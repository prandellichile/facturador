import os
import csv
import sqlite3
import logging
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# -------------------------
# RUTAS Y DIRECTORIOS
# -------------------------
BASE_DIR = r'D:\Proyectos\Cuesta Blaca Proyect Vers. 2.0'
DB_DIR = os.path.join(BASE_DIR, 'bd')
REPORTS_DIR = os.path.join(BASE_DIR, 'informes')
EXPORTS_DIR = os.path.join(BASE_DIR, 'export')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

DB_PATH = os.path.join(DB_DIR, 'pos_full.db')
LOG_PATH = os.path.join(LOGS_DIR, 'pos_full.log')
LATENCY_CSV = os.path.join(LOGS_DIR, 'latency_metrics.csv')

for d in (BASE_DIR, DB_DIR, REPORTS_DIR, EXPORTS_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logging.info("POS_FULL iniciado (sin importación automática)")

# Ensure latency CSV header
if not os.path.exists(LATENCY_CSV):
    with open(LATENCY_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp','operation','duration_ms'])

def log_latency(operation, duration_s):
    ms = round(duration_s * 1000, 2)
    with open(LATENCY_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), operation, ms])

# -------------------------
# DB: esquema (crea tablas mínimas si no existen)
# -------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    familia TEXT,
    codigo TEXT UNIQUE,
    descripcion TEXT,
    categoria TEXT,
    modelo TEXT,
    color TEXT,
    talla TEXT,
    unidad_medida TEXT,
    bodega TEXT,
    ubicacion TEXT,
    unidad_almacenamiento TEXT,
    ean_ua TEXT,
    stock_fisico INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT UNIQUE,
    precio REAL,
    moneda TEXT DEFAULT 'CLP',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    total REAL,
    forma_pago TEXT,
    estado TEXT DEFAULT 'cerrada'
);

CREATE TABLE IF NOT EXISTS sale_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    producto_codigo TEXT,
    descripcion TEXT,
    cantidad INTEGER,
    precio_unitario REAL,
    subtotal REAL,
    FOREIGN KEY(sale_id) REFERENCES sales(id)
);

CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER,
    producto_codigo TEXT,
    cantidad INTEGER,
    monto REAL,
    motivo TEXT,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

# -------------------------
# POS: lógica principal
# -------------------------
class POS:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
        self.cart = []
        self.monto_inicial = 0

    # Productos / precios / stock
    def get_product(self, codigo):
        t0 = time.perf_counter()
        self.cur.execute("SELECT familia,codigo,descripcion,categoria,modelo,color,talla,unidad_medida,bodega,ubicacion,unidad_almacenamiento,ean_ua,stock_fisico FROM products WHERE codigo = ?", (codigo,))
        row = self.cur.fetchone()
        duration = time.perf_counter() - t0
        log_latency('get_product', duration)
        if not row:
            return None
        keys = ['familia','codigo','descripcion','categoria','modelo','color','talla','unidad_medida','bodega','ubicacion','unidad_almacenamiento','ean_ua','stock_fisico']
        return dict(zip(keys, row))

    def get_stock(self, codigo):
        self.cur.execute("SELECT stock_fisico FROM products WHERE codigo = ?", (codigo,))
        r = self.cur.fetchone()
        return int(r[0]) if r and r[0] is not None else 0

    def get_price_by_category(self, categoria):
        t0 = time.perf_counter()
        self.cur.execute("SELECT precio FROM price_list WHERE categoria = ?", (categoria,))
        r = self.cur.fetchone()
        duration = time.perf_counter() - t0
        log_latency('get_price_by_category', duration)
        return float(r[0]) if r else None

    def set_price_for_category(self, categoria, precio):
        self.cur.execute("""
            INSERT INTO price_list (categoria, precio) VALUES (?, ?)
            ON CONFLICT(categoria) DO UPDATE SET precio=excluded.precio, updated_at=CURRENT_TIMESTAMP
        """, (categoria, float(precio)))
        self.conn.commit()
        logging.info(f"Precio actualizado: {categoria} -> {precio}")

    # Carrito
    def add_to_cart(self, codigo, cantidad=1, precio_manual=None):
        """
        Retornos:
         - (True, line) -> agregado correctamente
         - ("price_from_category", {"producto": prod, "precio_categoria": precio}) -> existe precio por categoría (informativo)
         - (None, {"need_price": True, "producto": prod}) -> falta precio por categoría
         - (False, "mensaje") -> error (producto no existe o stock insuficiente)
        """
        prod = self.get_product(codigo)
        if not prod:
            return False, "Producto no encontrado"

        stock_actual = self.get_stock(codigo)
        if cantidad > stock_actual:
            return False, f"Stock insuficiente. Disponible: {stock_actual}"

        precio_categoria = self.get_price_by_category(prod['categoria'])

        # Si se pasó precio manual explícito, lo usamos
        if precio_manual is not None:
            precio = precio_manual
            subtotal = cantidad * float(precio)
            line = {
                "producto_codigo": codigo,
                "descripcion": prod['descripcion'],
                "cantidad": cantidad,
                "precio_unitario": float(precio),
                "subtotal": subtotal
            }
            self.cart.append(line)
            logging.info(f"Añadido al carrito: {codigo} x{cantidad} @ {precio} (manual)")
            return True, line

        # Si existe precio por categoría, devolvemos aviso para la UI (para preguntar)
        if precio_categoria is not None:
            return "price_from_category", {"producto": prod, "precio_categoria": float(precio_categoria)}

        # Si no hay precio por categoría y no se pasó precio manual
        return None, {"need_price": True, "producto": prod}

    def edit_line_price(self, index, nuevo_precio):
        if index < 0 or index >= len(self.cart):
            return False
        self.cart[index]['precio_unitario'] = float(nuevo_precio)
        self.cart[index]['subtotal'] = round(self.cart[index]['cantidad'] * float(nuevo_precio), 2)
        logging.info(f"Precio línea {index} editado a {nuevo_precio}")
        return True

    def finalize_sale(self, forma_pago='efectivo'):
        """
        Ejecuta la venta en una transacción: verifica stock línea por línea antes de confirmar.
        Si algún item no tiene stock suficiente, hace rollback y devuelve error.
        """
        if not self.cart:
            return False, "Carrito vacío"

        try:
            # iniciar transacción
            self.conn.execute('BEGIN')
            total = 0
            for l in self.cart:
                codigo = l['producto_codigo']
                cantidad = int(l['cantidad'])
                # verificar stock actual
                self.cur.execute("SELECT stock_fisico FROM products WHERE codigo = ?", (codigo,))
                row = self.cur.fetchone()
                stock_actual = int(row[0]) if row and row[0] is not None else 0
                if cantidad > stock_actual:
                    self.conn.execute('ROLLBACK')
                    return False, f"Stock insuficiente para {codigo}. Disponible: {stock_actual}"
                total += l['subtotal']

            # insertar venta y líneas
            fecha = datetime.now().isoformat()
            self.cur.execute("INSERT INTO sales (fecha, total, forma_pago) VALUES (?, ?, ?)", (fecha, total, forma_pago))
            sale_id = self.cur.lastrowid
            for l in self.cart:
                self.cur.execute("""
                    INSERT INTO sale_lines (sale_id, producto_codigo, descripcion, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sale_id, l['producto_codigo'], l['descripcion'], l['cantidad'], l['precio_unitario'], l['subtotal']))
                # actualizar stock
                self.cur.execute("UPDATE products SET stock_fisico = stock_fisico - ? WHERE codigo = ?", (l['cantidad'], l['producto_codigo']))

            self.conn.commit()
            logging.info(f"Venta finalizada ID {sale_id} total {total}")
            self.cart = []
            return True, sale_id

        except Exception as e:
            logging.exception("Error finalize_sale")
            try:
                self.conn.rollback()
            except:
                pass
            return False, str(e)

    # Devoluciones
    def devolver_articulo(self, id_venta, sku, cantidad, motivo="SIN MOTIVO"):
        self.cur.execute("SELECT cantidad, precio_unitario FROM sale_lines WHERE sale_id = ? AND producto_codigo = ?", (id_venta, sku))
        row = self.cur.fetchone()
        if not row:
            return False, "Artículo no encontrado en la venta"
        cantidad_vendida, precio_unitario = row
        if cantidad > cantidad_vendida:
            return False, f"Solo se vendieron {cantidad_vendida} unidades"
        monto_devuelto = cantidad * precio_unitario
        self.cur.execute("""
            INSERT INTO returns (sale_id, producto_codigo, cantidad, monto, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (id_venta, sku, cantidad, monto_devuelto, motivo, datetime.now().isoformat()))
        # ajustar stock
        self.cur.execute("UPDATE products SET stock_fisico = stock_fisico + ? WHERE codigo = ?", (cantidad, sku))
        self.conn.commit()
        logging.info(f"Devolución registrada: venta {id_venta} sku {sku} cant {cantidad} monto {monto_devuelto} motivo {motivo}")
        return True, f"Devolución registrada por ${monto_devuelto}"

    # Reportes simples
    def reporte_cierre(self):
        self.cur.execute("SELECT id, fecha, total, forma_pago FROM sales WHERE date(fecha) = date('now')")
        ventas = self.cur.fetchall()
        self.cur.execute("SELECT SUM(monto) FROM returns WHERE date(fecha) = date('now')")
        devoluciones = self.cur.fetchone()[0] or 0
        self.cur.execute("SELECT SUM(total) FROM sales WHERE date(fecha) = date('now')")
        total_ventas = self.cur.fetchone()[0] or 0
        self.cur.execute("SELECT COUNT(*) FROM products WHERE stock_fisico <= 0")
        agotados = self.cur.fetchone()[0]
        return {
            "ventas": ventas,
            "total_ventas": total_ventas,
            "devoluciones": devoluciones,
            "agotados": agotados
        }

# -------------------------
# UI: Interfaz moderna integrada
# -------------------------
COLOR_BG = "#EAF7FF"        # fondo muy claro azul celeste
COLOR_PRIMARY = "#87CEEB"   # azul celeste
COLOR_ACCENT = "#F4C7C3"    # rojo pálido
COLOR_TEXT = "#222222"

class ModernPOSApp(tk.Tk):
    def __init__(self, pos):
        super().__init__()
        self.pos = pos
        self.title("POS Profesional - Cuesta Blanca")
        self.geometry("1200x720")
        self.configure(bg=COLOR_BG)
        self.style = ttk.Style(self)
        self._setup_style()
        self._build_layout()
        self._bind_shortcuts()

    def _setup_style(self):
        try:
            self.style.theme_use('default')
        except:
            pass
        self.style.configure("TFrame", background=COLOR_BG)
        self.style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Accent.TButton", background=COLOR_PRIMARY, foreground=COLOR_TEXT)
        self.style.map("Accent.TButton",
                       background=[('active', COLOR_ACCENT), ('!active', COLOR_PRIMARY)])
        self.style.configure("Danger.TButton", background=COLOR_ACCENT, foreground=COLOR_TEXT)
        self.style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        self.style.configure("TCombobox", padding=4)

    def _build_layout(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=8)
        ttk.Label(header, text="POS Profesional", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="  •  Cuesta Blanca", foreground=COLOR_PRIMARY).pack(side=tk.LEFT)

        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        left = ttk.Frame(main, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))

        ttk.Label(left, text="Código / Palabra clave").pack(anchor="w", pady=(6,2))
        self.entry_search = ttk.Entry(left, width=28)
        self.entry_search.pack(anchor="w")
        self.entry_search.focus()

        qty_frame = ttk.Frame(left)
        qty_frame.pack(anchor="w", pady=6)
        ttk.Label(qty_frame, text="Cantidad").pack(side=tk.LEFT)
        self.spin_qty = tk.Spinbox(qty_frame, from_=1, to=999, width=6)
        self.spin_qty.pack(side=tk.LEFT, padx=6)

        ttk.Label(left, text="Tipo de documento").pack(anchor="w", pady=(8,2))
        self.doc_type = ttk.Combobox(left, values=["Boleta", "Factura", "Nota de Crédito"], state="readonly")
        self.doc_type.current(0)
        self.doc_type.pack(anchor="w")

        ttk.Button(left, text="Agregar al carrito", style="Accent.TButton", command=self.action_add).pack(fill=tk.X, pady=8)
        ttk.Button(left, text="Aplicar descuento", command=self.action_apply_discount).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="Buscar por palabra clave", command=self.action_search_keyword).pack(fill=tk.X, pady=4)
        ttk.Button(left, text="Abrir Devoluciones", command=self.open_devoluciones).pack(fill=tk.X, pady=8)
        ttk.Button(left, text="Admin Precios por Categoría", command=self.open_admin_precios).pack(fill=tk.X, pady=4)

        center = ttk.Frame(main)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cols = ("codigo","descripcion","cantidad","precio","subtotal")
        self.tree = ttk.Treeview(center, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
        self.tree.column("descripcion", width=380)
        self.tree.column("precio", width=100, anchor="e")
        self.tree.column("subtotal", width=120, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        line_ctrl = ttk.Frame(center)
        line_ctrl.pack(fill=tk.X, padx=6, pady=(0,8))
        ttk.Button(line_ctrl, text="Editar precio", command=self.edit_line_price).pack(side=tk.LEFT, padx=4)
        ttk.Button(line_ctrl, text="Editar cantidad", command=self.edit_line_qty).pack(side=tk.LEFT, padx=4)
        ttk.Button(line_ctrl, text="Eliminar línea", command=self.remove_line).pack(side=tk.LEFT, padx=4)

        right = ttk.Frame(main, width=320)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10,0))

        totals = ttk.Frame(right)
        totals.pack(fill=tk.X, pady=6)
        ttk.Label(totals, text="Totales", style="Header.TLabel").pack(anchor="w")
        self.lbl_total = ttk.Label(totals, text="Total: $0.00", font=("Segoe UI", 14, "bold"))
        self.lbl_total.pack(anchor="w", pady=(6,0))

        ttk.Button(right, text="Finalizar Venta Efectivo", style="Accent.TButton", command=lambda: self.finalize("efectivo")).pack(fill=tk.X, pady=6)
        ttk.Button(right, text="Finalizar Venta Tarjeta", style="Accent.TButton", command=lambda: self.finalize("tarjeta")).pack(fill=tk.X, pady=6)

        rpt_frame = ttk.LabelFrame(right, text="Reportes y Export")
        rpt_frame.pack(fill=tk.X, pady=10)
        ttk.Button(rpt_frame, text="Informe Caja Diaria", command=self.report_caja).pack(fill=tk.X, pady=4)
        ttk.Button(rpt_frame, text="Informe de Salidas", command=self.report_salidas).pack(fill=tk.X, pady=4)
        ttk.Button(rpt_frame, text="Exportar SAP Diario", command=self.export_sap).pack(fill=tk.X, pady=4)

        self.status = ttk.Label(self, text="Listo", anchor="w")
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------
    # Acciones UI (con validaciones)
    # -------------------------
    def action_add(self):
        codigo = self.entry_search.get().strip()
        if not codigo:
            messagebox.showerror("Error", "Ingresa código o palabra clave")
            return
        try:
            cantidad = int(self.spin_qty.get())
        except:
            messagebox.showerror("Error", "Cantidad inválida")
            return

        res, info = self.pos.add_to_cart(codigo, cantidad)
        # Caso: stock insuficiente o producto no existe
        if res is False:
            messagebox.showerror("Error", info)
            return

        # Caso: existe precio por categoría (informativo) -> preguntar si usar o cambiar
        if res == "price_from_category":
            producto = info["producto"]
            precio_cat = info["precio_categoria"]
            msg = (f"Producto: {producto['descripcion']}\n"
                   f"Categoría: {producto['categoria']}\n"
                   f"Precio por categoría: {precio_cat:.2f}\n\n"
                   "¿Deseas usar este precio?")
            usar = messagebox.askyesno("Precio por categoría", msg, icon='question')
            if usar:
                ok, line = self.pos.add_to_cart(codigo, cantidad, precio_manual=precio_cat)
                if ok:
                    self.refresh_cart()
                else:
                    messagebox.showerror("Error", line)
                return
            else:
                precio = simpledialog.askfloat("Precio manual", f"Ingrese precio para {producto['descripcion']}", parent=self, minvalue=0.0)
                if precio is None:
                    return
                ok, line = self.pos.add_to_cart(codigo, cantidad, precio_manual=precio)
                if ok:
                    self.refresh_cart()
                else:
                    messagebox.showerror("Error", line)
                return

        # Caso: falta precio por categoría -> pedir precio manual
        if res is None and isinstance(info, dict) and info.get("need_price"):
            producto = info["producto"]
            precio = simpledialog.askfloat("Precio manual", f"Ingrese precio para {producto['descripcion']}", parent=self, minvalue=0.0)
            if precio is None:
                return
            ok, line = self.pos.add_to_cart(codigo, cantidad, precio_manual=precio)
            if ok:
                self.refresh_cart()
            else:
                messagebox.showerror("Error", line)
            return

        # Caso: agregado correctamente
        if res is True:
            self.refresh_cart()
            return

        # Fallback
        messagebox.showerror("Error", "No se pudo agregar el producto")

    def action_search_keyword(self):
        term = self.entry_search.get().strip()
        if not term:
            term = simpledialog.askstring("Buscar", "Ingrese palabra clave", parent=self)
            if not term:
                return
        term_like = f"%{term}%"
        try:
            self.pos.cur.execute("SELECT codigo, descripcion, stock_fisico FROM products WHERE lower(descripcion) LIKE lower(?) OR lower(codigo) LIKE lower(?) LIMIT 200", (term_like, term_like))
            rows = self.pos.cur.fetchall()
        except Exception as e:
            logging.error(f"Error en consulta búsqueda SQL: {e}")
            rows = []

        if not rows:
            # fallback: cargar y comparar en Python (normalizando acentos)
            try:
                import unicodedata
                def _normalize(s):
                    if s is None:
                        return ''
                    s = str(s).strip().lower()
                    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
                self.pos.cur.execute("SELECT codigo, descripcion, stock_fisico FROM products")
                all_rows = self.pos.cur.fetchall()
                norm_term = _normalize(term)
                rows = []
                for r in all_rows:
                    if norm_term in _normalize(r[1]) or norm_term in _normalize(r[0]):
                        rows.append(r)
                rows = rows[:200]
            except Exception as e:
                logging.error(f"Error fallback búsqueda: {e}")
                rows = []

        if not rows:
            messagebox.showinfo("Buscar", "No se encontraron productos")
            return

        win = tk.Toplevel(self)
        win.title("Resultados de búsqueda")
        tree = ttk.Treeview(win, columns=("codigo","descripcion","stock"), show="headings")
        for h in ("codigo","descripcion","stock"):
            tree.heading(h, text=h.capitalize())
        tree.pack(fill=tk.BOTH, expand=True)
        for r in rows:
            tree.insert("", tk.END, values=r)

        def select_and_close():
            sel = tree.selection()
            if not sel:
                messagebox.showerror("Error", "Selecciona un producto")
                return
            codigo = tree.item(sel[0])['values'][0]
            self.entry_search.delete(0, tk.END)
            self.entry_search.insert(0, codigo)
            win.destroy()

        ttk.Button(win, text="Seleccionar", command=select_and_close).pack(pady=6)

    def refresh_cart(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for i, l in enumerate(self.pos.cart):
            self.tree.insert("", tk.END, iid=str(i), values=(l['producto_codigo'], l['descripcion'], l['cantidad'], f"{l['precio_unitario']:.2f}", f"{l['subtotal']:.2f}"))
        total = sum(l['subtotal'] for l in self.pos.cart)
        self.lbl_total.config(text=f"Total: ${total:,.2f}")

    def edit_line_price(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona una línea")
            return
        idx = int(sel[0])
        nuevo = simpledialog.askfloat("Editar precio", "Nuevo precio unitario:", parent=self)
        if nuevo is None:
            return
        ok = self.pos.edit_line_price(idx, nuevo)
        if ok:
            self.refresh_cart()

    def edit_line_qty(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona una línea")
            return
        idx = int(sel[0])
        nuevo = simpledialog.askinteger("Editar cantidad", "Nueva cantidad:", parent=self, minvalue=1)
        if nuevo is None:
            return
        # validar stock al editar cantidad
        codigo = self.pos.cart[idx]['producto_codigo']
        stock_actual = self.pos.get_stock(codigo)
        if nuevo > stock_actual:
            messagebox.showerror("Error", f"Stock insuficiente. Disponible: {stock_actual}")
            return
        self.pos.cart[idx]['cantidad'] = int(nuevo)
        self.pos.cart[idx]['subtotal'] = round(self.pos.cart[idx]['cantidad'] * self.pos.cart[idx]['precio_unitario'], 2)
        self.refresh_cart()

    def remove_line(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona una línea")
            return
        idx = int(sel[0])
        del self.pos.cart[idx]
        self.refresh_cart()

    def action_apply_discount(self):
        if not self.pos.cart:
            messagebox.showerror("Error", "Carrito vacío")
            return
        pct = simpledialog.askfloat("Descuento", "Porcentaje de descuento a aplicar (ej 10 para 10%)", parent=self, minvalue=0, maxvalue=100)
        if pct is None:
            return
        factor = (100 - pct) / 100.0
        for l in self.pos.cart:
            l['precio_unitario'] = round(l['precio_unitario'] * factor, 2)
            l['subtotal'] = round(l['precio_unitario'] * l['cantidad'], 2)
        self.refresh_cart()
        messagebox.showinfo("Descuento", f"Descuento del {pct}% aplicado")

    def finalize(self, forma_pago):
        ok, info = self.pos.finalize_sale(forma_pago)
        if not ok:
            messagebox.showerror("Error", info)
            return
        messagebox.showinfo("Venta", f"Venta registrada. ID: {info}")
        self.refresh_cart()

    # -------------------------
    # Reportes y export
    # -------------------------
    def report_caja(self):
        r = self.pos.reporte_cierre()
        txt = f"Ventas hoy: {len(r['ventas'])}\nTotal ventas: {r['total_ventas']}\nDevoluciones hoy: {r['devoluciones']}\nProductos agotados: {r['agotados']}"
        messagebox.showinfo("Informe Caja Diaria", txt)

    def report_salidas(self):
        self.pos.cur.execute("SELECT sale_id, producto_codigo, cantidad, subtotal FROM sale_lines ORDER BY id DESC LIMIT 200")
        rows = self.pos.cur.fetchall()
        win = tk.Toplevel(self)
        win.title("Informe de Salidas")
        tree = ttk.Treeview(win, columns=("venta","sku","cant","subtotal"), show="headings")
        for h in ("venta","sku","cant","subtotal"):
            tree.heading(h, text=h.capitalize())
        tree.pack(expand=True, fill=tk.BOTH)
        for r in rows:
            tree.insert("", tk.END, values=r)

    def export_sap(self):
        fecha_str = datetime.now().strftime("%Y%m%d")
        filename = os.path.join(EXPORTS_DIR, f"sap_export_{fecha_str}.csv")
        self.pos.cur.execute("SELECT s.id, s.fecha, sl.producto_codigo, sl.cantidad, sl.precio_unitario, sl.subtotal FROM sales s JOIN sale_lines sl ON s.id = sl.sale_id WHERE date(s.fecha) = date('now')")
        rows = self.pos.cur.fetchall()
        if not rows:
            messagebox.showinfo("Exportar SAP", "No hay ventas para exportar hoy")
            return
        with open(filename, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["SaleID","Fecha","SKU","Cantidad","PrecioUnitario","Subtotal"])
            for r in rows:
                writer.writerow(r)
        logging.info(f"Export SAP generado: {filename}")
        messagebox.showinfo("Exportar SAP", f"Exportado a {filename}")

    # -------------------------
    # Ventanas auxiliares
    # -------------------------
    def open_devoluciones(self):
        DevolucionWindow(self, self.pos)

    def open_admin_precios(self):
        AdminPreciosWindow(self, self.pos)

    def _bind_shortcuts(self):
        self.bind("<Return>", lambda e: self.action_add())
        self.bind("<F5>", lambda e: self.refresh_cart())

# -------------------------
# Ventana Devoluciones
# -------------------------
class DevolucionWindow(tk.Toplevel):
    def __init__(self, master, pos):
        super().__init__(master)
        self.pos = pos
        self.title("Devoluciones")
        self.geometry("700x420")
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self)
        frame.pack(pady=8)
        tk.Label(frame, text="ID Venta:").pack(side=tk.LEFT)
        self.entry_id = tk.Entry(frame, width=8)
        self.entry_id.pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Buscar", command=self.buscar).pack(side=tk.LEFT, padx=5)

        cols = ("sku","descripcion","cantidad","precio")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
        self.tree.pack(fill=tk.BOTH, expand=True, pady=8)

        bottom = tk.Frame(self)
        bottom.pack(pady=5)
        tk.Label(bottom, text="Cantidad a devolver:").pack(side=tk.LEFT)
        self.entry_cant = tk.Entry(bottom, width=6)
        self.entry_cant.pack(side=tk.LEFT, padx=5)
        tk.Label(bottom, text="Motivo:").pack(side=tk.LEFT, padx=5)
        self.entry_motivo = tk.Entry(bottom, width=30)
        self.entry_motivo.pack(side=tk.LEFT, padx=5)
        tk.Button(bottom, text="Registrar devolución", command=self.registrar).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom, text="Ver historial", command=self.ver_historial).pack(side=tk.LEFT, padx=5)

    def buscar(self):
        vid = self.entry_id.get().strip()
        if not vid.isdigit():
            messagebox.showerror("Error", "ID inválido")
            return
        vid = int(vid)
        self.pos.cur.execute("SELECT producto_codigo, descripcion, cantidad, precio_unitario FROM sale_lines WHERE sale_id = ?", (vid,))
        rows = self.pos.cur.fetchall()
        for r in self.tree.get_children():
            self.tree.delete(r)
        for row in rows:
            self.tree.insert("", tk.END, values=(row[0], row[1], row[2], f"{row[3]:.2f}"))

    def registrar(self):
        vid = self.entry_id.get().strip()
        cant = self.entry_cant.get().strip()
        motivo = self.entry_motivo.get().strip() or "SIN MOTIVO"
        if not vid.isdigit() or not cant.isdigit():
            messagebox.showerror("Error", "ID y cantidad deben ser numéricos")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona un artículo")
            return
        sku = self.tree.item(sel[0])['values'][0]
        ok, msg = self.pos.devolver_articulo(int(vid), sku, int(cant), motivo)
        if ok:
            messagebox.showinfo("Éxito", msg)
        else:
            messagebox.showerror("Error", msg)

    def ver_historial(self):
        self.pos.cur.execute("SELECT sale_id, producto_codigo, cantidad, monto, motivo, fecha FROM returns ORDER BY fecha DESC LIMIT 200")
        rows = self.pos.cur.fetchall()
        win = tk.Toplevel(self)
        win.title("Historial Devoluciones")
        tree = ttk.Treeview(win, columns=("venta","sku","cant","monto","motivo","fecha"), show="headings")
        for h in ("venta","sku","cant","monto","motivo","fecha"):
            tree.heading(h, text=h.capitalize())
        tree.pack(expand=True, fill=tk.BOTH)
        for r in rows:
            tree.insert("", tk.END, values=r)

# -------------------------
# Admin Precios por Categoría
# -------------------------
class AdminPreciosWindow(tk.Toplevel):
    def __init__(self, master, pos):
        super().__init__(master)
        self.pos = pos
        self.title("Admin Precios por Categoría")
        self.geometry("620x360")
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self)
        frame.pack(pady=8)
        tk.Label(frame, text="Categoría:").grid(row=0, column=0, padx=5)
        self.entry_cat = tk.Entry(frame, width=20)
        self.entry_cat.grid(row=0, column=1, padx=5)
        tk.Label(frame, text="Precio:").grid(row=0, column=2, padx=5)
        self.entry_prec = tk.Entry(frame, width=12)
        self.entry_prec.grid(row=0, column=3, padx=5)
        tk.Button(frame, text="Guardar", command=self.guardar).grid(row=0, column=4, padx=5)
        tk.Button(frame, text="Cargar selección", command=self.cargar_seleccion).grid(row=0, column=5, padx=5)

        self.tree = ttk.Treeview(self, columns=("categoria","precio","updated"), show="headings", height=12)
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("updated", text="Updated")
        self.tree.pack(expand=True, fill=tk.BOTH, pady=8)
        tk.Button(self, text="Refrescar", command=self.refrescar).pack()
        self.refrescar()

    def guardar(self):
        cat = self.entry_cat.get().strip()
        try:
            prec = float(self.entry_prec.get().strip())
        except:
            messagebox.showerror("Error", "Precio inválido")
            return
        self.pos.set_price_for_category(cat, prec)
        messagebox.showinfo("OK", "Precio guardado/actualizado")
        self.refrescar()

    def cargar_seleccion(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Selecciona una categoría en la lista")
            return
        row = self.tree.item(sel[0])['values']
        categoria, precio, updated = row
        self.entry_cat.delete(0, tk.END)
        self.entry_cat.insert(0, categoria)
        self.entry_prec.delete(0, tk.END)
        self.entry_prec.insert(0, str(precio))

    def refrescar(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.pos.cur.execute("SELECT categoria, precio, updated_at FROM price_list ORDER BY categoria")
        for row in self.pos.cur.fetchall():
            self.tree.insert("", tk.END, values=row)

# -------------------------
# MAIN
# -------------------------
def main():
    # Inicializar esquema mínimo (no importa productos)
    conn = init_db(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    total = cur.fetchone()[0]
    conn.close()

    if total == 0:
        msg = ("La tabla 'products' está vacía.\n\n"
               "Ejecuta el script 'importer.py' para cargar los productos desde el Excel:\n"
               f"{os.path.join(BASE_DIR, 'fuentes')}\n\n"
               "Después de importar, vuelve a ejecutar este programa.")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("Productos no cargados", msg)
            root.destroy()
        except:
            print(msg)
        return

    pos = POS(DB_PATH)
    app = ModernPOSApp(pos)
    app.mainloop()

if __name__ == "__main__":
    main()