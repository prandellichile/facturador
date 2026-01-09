import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import pandas as pd

DB_FILE = "inventario.db"
IVA = 0.19


# =========================
# ESTILO MODERNO (AZUL / CELESTE / ROJO PASTEL)
# =========================

def aplicar_estilos_modernos(root):
    style = ttk.Style(root)

    # Tema base
    style.theme_use("clam")

    # Paleta de colores
    azul = "#1E88E5"
    celeste = "#BBDEFB"
    rojo_pastel = "#EF9A9A"
    gris_claro = "#F5F5F5"
    gris_borde = "#D0D0D0"

    # ===== Botones redondeados =====
    style.configure(
        "Rounded.TButton",
        font=("Segoe UI", 11),
        padding=10,
        background=azul,
        foreground="white",
        borderwidth=0,
        focusthickness=3,
        focuscolor="none"
    )

    style.map(
        "Rounded.TButton",
        background=[("active", "#1565C0")],
        foreground=[("active", "white")]
    )

    # ===== Entradas redondeadas =====
    style.configure(
        "Rounded.TEntry",
        padding=6,
        relief="flat",
        bordercolor=gris_borde,
        lightcolor=celeste,
        darkcolor=gris_borde,
        borderwidth=1
    )

    # ===== Combobox moderno =====
    style.configure(
        "Rounded.TCombobox",
        padding=6,
        relief="flat",
        bordercolor=gris_borde,
        lightcolor=celeste,
        darkcolor=gris_borde,
        borderwidth=1
    )

    # ===== Treeview moderno =====
    style.configure(
        "Custom.Treeview",
        background="white",
        foreground="black",
        rowheight=28,
        fieldbackground="white",
        bordercolor=gris_borde,
        borderwidth=1,
        font=("Segoe UI", 10)
    )

    style.configure(
        "Custom.Treeview.Heading",
        background=azul,
        foreground="white",
        font=("Segoe UI", 11, "bold"),
        borderwidth=0
    )

    style.map(
        "Custom.Treeview",
        background=[("selected", celeste)],
        foreground=[("selected", "black")]
    )

    root.configure(bg=gris_claro)


# =========================
# CONEXIÓN A SQLITE
# =========================

def get_conn():
    return sqlite3.connect(DB_FILE)


# =========================
# OBTENER PRODUCTO
# =========================

def get_producto(codigo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, codigo, descripcion, stock_fisico,
               precio_detalle, precio_may1, precio_may2
        FROM productos
        WHERE codigo = ?
    """, (codigo,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "codigo": row[1],
        "descripcion": row[2],
        "stock": row[3],
        "detalle": row[4],
        "may1": row[5],
        "may2": row[6]
    }


# =========================
# ACTUALIZAR STOCK
# =========================

def actualizar_stock(producto_id, cantidad):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE productos
        SET stock_fisico = stock_fisico - ?,
            unidades_salientes = unidades_salientes + ?
        WHERE id = ?
    """, (cantidad, cantidad, producto_id))
    conn.commit()
    conn.close()
    # =========================
# REGISTRAR VENTA
# =========================

def registrar_venta(carrito, neto, iva, total, tipo_doc):
    conn = get_conn()
    cur = conn.cursor()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Crear tablas si no existen
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            total_neto REAL,
            total_iva REAL,
            total_total REAL,
            tipo_documento TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            codigo TEXT,
            descripcion TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            total_linea REAL
        )
    """)

    # Insertar encabezado
    cur.execute("""
        INSERT INTO ventas (fecha, total_neto, total_iva, total_total, tipo_documento)
        VALUES (?, ?, ?, ?, ?)
    """, (fecha, neto, iva, total, tipo_doc))

    venta_id = cur.lastrowid

    # Insertar detalle
    for item in carrito:
        cur.execute("""
            INSERT INTO ventas_detalle (
                venta_id, codigo, descripcion,
                cantidad, precio_unitario, total_linea
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            venta_id,
            item["codigo"],
            item["descripcion"],
            item["cantidad"],
            item["precio"],
            item["total"]
        ))

    conn.commit()
    conn.close()

    return venta_id


# =========================
# CAJA DIARIA
# =========================

def caja_diaria():
    conn = get_conn()
    cur = conn.cursor()

    hoy = datetime.datetime.now().strftime("%Y-%m-%d")

    cur.execute("""
        SELECT SUM(total_neto), SUM(total_iva), SUM(total_total)
        FROM ventas
        WHERE fecha LIKE ?
    """, (hoy + "%",))

    row = cur.fetchone()
    conn.close()

    neto = row[0] or 0
    iva = row[1] or 0
    total = row[2] or 0

    messagebox.showinfo(
        "Caja diaria",
        f"Fecha: {hoy}\n\n"
        f"Neto: {neto:,}\n"
        f"IVA: {iva:,}\n"
        f"Total: {total:,}"
    )


# =========================
# INFORME DE SALIDAS
# =========================

def informe_salidas():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT codigo, descripcion, unidades_salientes
        FROM productos
        WHERE unidades_salientes > 0
        ORDER BY unidades_salientes DESC
    """)

    datos = cur.fetchall()
    conn.close()

    ventana = tk.Toplevel()
    ventana.title("Informe de salidas")

    tree = ttk.Treeview(ventana, columns=("codigo", "desc", "salidas"), show="headings")
    tree.heading("codigo", text="Código")
    tree.heading("desc", text="Descripción")
    tree.heading("salidas", text="Unidades salientes")
    tree.pack(fill=tk.BOTH, expand=True)

    for d in datos:
        tree.insert("", tk.END, values=d)


# =========================
# EXPORTACIÓN DIARIA A SAP B1
# =========================

def exportar_sap_diario():
    conn = get_conn()
    cur = conn.cursor()

    hoy = datetime.datetime.now().strftime("%Y-%m-%d")

    # Obtener ventas del día
    cur.execute("""
        SELECT id, fecha, total_total, tipo_documento
        FROM ventas
        WHERE fecha LIKE ?
    """, (hoy + "%",))
    ventas = cur.fetchall()

    # Obtener detalle del día
    cur.execute("""
        SELECT venta_id, codigo, descripcion, cantidad, precio_unitario, total_linea
        FROM ventas_detalle
        WHERE venta_id IN (
            SELECT id FROM ventas WHERE fecha LIKE ?
        )
    """, (hoy + "%",))
    detalle = cur.fetchall()

    conn.close()

    if not ventas:
        messagebox.showinfo("Exportación SAP", "No hay ventas para exportar hoy.")
        return

    # Crear DataFrames
    df_oinv = pd.DataFrame(columns=[
        "DocDate", "DocDueDate", "CardCode", "DocTotal",
        "Comments", "Series", "DocType"
    ])

    df_inv1 = pd.DataFrame(columns=[
        "DocEntry", "ItemCode", "Quantity", "Price",
        "LineTotal", "WhsCode"
    ])

    # Llenar encabezado
    for v in ventas:
        venta_id, fecha, total, tipo_doc = v

        # Serie SAP según tipo de documento
        if tipo_doc == "BOLETA":
            serie = 33
        else:
            serie = 30

        df_oinv.loc[len(df_oinv)] = [
            fecha.split(" ")[0],   # DocDate
            fecha.split(" ")[0],   # DocDueDate
            "C99999",              # Cliente genérico
            total,
            f"Venta POS ID {venta_id}",
            serie,
            "I"                    # Documento de ítems
        ]

    # Llenar detalle
    for d in detalle:
        venta_id, codigo, desc, qty, price, total_linea = d
        df_inv1.loc[len(df_inv1)] = [
            venta_id,
            codigo,
            qty,
            price,
            total_linea,
            "01"  # Bodega SAP
        ]

    # Guardar Excel
    fecha_archivo = datetime.datetime.now().strftime("%Y%m%d")
    archivo = f"export_sap_{fecha_archivo}.xlsx"

    with pd.ExcelWriter(archivo) as writer:
        df_oinv.to_excel(writer, sheet_name="OINV", index=False)
        df_inv1.to_excel(writer, sheet_name="INV1", index=False)

    messagebox.showinfo("Exportación completada", f"Archivo generado:\n{archivo}")
    # =========================
# INTERFAZ GRÁFICA
# =========================

class POS:
    def __init__(self, root):
        self.root = root
        aplicar_estilos_modernos(root)
        self.root.title("POS Profesional - Cuesta Blanca")

        self.carrito = []
        self.lista_precio = tk.StringVar(value="detalle")
        self.tipo_doc = tk.StringVar(value="BOLETA")
        self.modo_prueba = tk.BooleanVar(value=False)

        # ===== FILA 0: ESCANEO =====
        tk.Label(root, text="Escanear código:", bg="#F5F5F5", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w")
        self.entry_codigo = ttk.Entry(root, style="Rounded.TEntry", width=30)
        self.entry_codigo.grid(row=0, column=1, sticky="we")
        self.entry_codigo.bind("<Return>", self.agregar_producto)

        ttk.Button(root, text="Agregar", style="Rounded.TButton",
                   command=self.agregar_producto).grid(row=0, column=2, padx=5)

        # ===== FILA 1: LISTA DE PRECIOS =====
        tk.Label(root, text="Lista de precios:", bg="#F5F5F5", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w")
        self.combo_lista = ttk.Combobox(root, textvariable=self.lista_precio,
                                        values=["detalle", "may1", "may2"],
                                        width=10, style="Rounded.TCombobox")
        self.combo_lista.grid(row=1, column=1, sticky="w")
        self.combo_lista.current(0)

        # ===== FILA 2: TABLA CARRITO =====
        self.tree = ttk.Treeview(
            root,
            style="Custom.Treeview",
            columns=("codigo", "desc", "cant", "precio", "total"),
            show="headings",
            height=10
        )

        self.tree.heading("codigo", text="Código")
        self.tree.heading("desc", text="Descripción")
        self.tree.heading("cant", text="Cant.")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("total", text="Total")

        self.tree.column("codigo", width=120)
        self.tree.column("desc", width=250)
        self.tree.column("cant", width=60, anchor="e")
        self.tree.column("precio", width=80, anchor="e")
        self.tree.column("total", width=100, anchor="e")

        self.tree.grid(row=2, column=0, columnspan=3, pady=5, sticky="nsew")

        # ===== FILA 3: TOTALES =====
        self.label_total = tk.Label(
            root,
            text="NETO: 0 | IVA: 0 | TOTAL: 0",
            font=("Segoe UI", 12, "bold"),
            bg="#F5F5F5"
        )
        self.label_total.grid(row=3, column=0, columnspan=3, sticky="e", pady=5)

        # ===== FILA 4: BOTONES CARRITO =====
        ttk.Button(root, text="Eliminar ítem", style="Rounded.TButton",
                   command=self.eliminar_item).grid(row=4, column=0, pady=5)

        ttk.Button(root, text="Vaciar carrito", style="Rounded.TButton",
                   command=self.vaciar_carrito).grid(row=4, column=1, pady=5)

        ttk.Button(root, text="Finalizar venta", style="Rounded.TButton",
                   command=self.finalizar_venta).grid(row=4, column=2, pady=5)

        # ===== FILA 5: CAJA / INFORMES / EXPORT =====
        ttk.Button(root, text="Caja diaria", style="Rounded.TButton",
                   command=caja_diaria).grid(row=5, column=0, pady=5)

        ttk.Button(root, text="Informe salidas", style="Rounded.TButton",
                   command=informe_salidas).grid(row=5, column=1, pady=5)

        ttk.Button(root, text="Exportar SAP Diario", style="Rounded.TButton",
                   command=exportar_sap_diario).grid(row=5, column=2, pady=5)

        # ===== FILA 6: BUSCADOR =====
        tk.Label(root, text="Buscar producto:", bg="#F5F5F5", font=("Segoe UI", 11)).grid(row=6, column=0, sticky="w")
        self.entry_buscar = ttk.Entry(root, style="Rounded.TEntry", width=30)
        self.entry_buscar.grid(row=6, column=1, sticky="we")

        ttk.Button(root, text="Buscar", style="Rounded.TButton",
                   command=self.buscar_producto).grid(row=6, column=2, padx=5, pady=5)

        # ===== FILA 7: DESCUENTO =====
        tk.Label(root, text="Descuento %:", bg="#F5F5F5", font=("Segoe UI", 11)).grid(row=7, column=0, sticky="w")
        self.entry_descuento = ttk.Entry(root, style="Rounded.TEntry", width=10)
        self.entry_descuento.grid(row=7, column=1, sticky="w")

        ttk.Button(root, text="Aplicar descuento", style="Rounded.TButton",
                   command=self.aplicar_descuento).grid(row=7, column=2, padx=5, pady=5)

        # ===== FILA 8: TIPO DOCUMENTO =====
        tk.Label(root, text="Tipo documento:", bg="#F5F5F5", font=("Segoe UI", 11)).grid(row=8, column=0, sticky="w")
        self.combo_tipo = ttk.Combobox(root, textvariable=self.tipo_doc,
                                       values=["BOLETA", "FACTURA"],
                                       width=10, style="Rounded.TCombobox")
        self.combo_tipo.grid(row=8, column=1, sticky="w")
        self.combo_tipo.current(0)

        # ===== FILA 9: MODO PRUEBA =====
        tk.Checkbutton(
            root,
            text="Modo prueba (no afecta inventario)",
            variable=self.modo_prueba,
            bg="#F5F5F5",
            font=("Segoe UI", 11)
        ).grid(row=9, column=0, columnspan=2, sticky="w")

        # ===== FILA 10: AJUSTE CANTIDAD =====
        ttk.Button(root, text="+1 cantidad", style="Rounded.TButton",
                   command=self.incrementar_cantidad).grid(row=10, column=0, pady=5)

        ttk.Button(root, text="-1 cantidad", style="Rounded.TButton",
                   command=self.decrementar_cantidad).grid(row=10, column=1, pady=5)

        # Configuración de expansión
        root.columnconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        # Cierre del día
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

            # =========================
    # AGREGAR PRODUCTO (CON CANTIDAD)
    # =========================

    def agregar_producto(self, event=None):
        codigo = self.entry_codigo.get().strip()
        self.entry_codigo.delete(0, tk.END)

        if not codigo:
            return

        producto = get_producto(codigo)
        if not producto:
            messagebox.showerror("Error", f"Producto no encontrado: {codigo}")
            return

        # Validación de stock en modo real
        if producto["stock"] <= 0 and not self.modo_prueba.get():
            messagebox.showerror("Sin stock", f"Sin stock para: {producto['descripcion']}")
            return

        # === Pedir cantidad ===
        cantidad_str = simpledialog.askstring(
            "Cantidad",
            f"Ingrese cantidad para:\n{producto['descripcion']}\n\n(ENTER = 1)"
        )

        if cantidad_str is None or cantidad_str.strip() == "":
            cantidad = 1
        else:
            try:
                cantidad = int(cantidad_str)
            except:
                messagebox.showerror("Error", "Cantidad inválida")
                return

        if cantidad <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
            return

        # Validación de stock en modo real
        if cantidad > producto["stock"] and not self.modo_prueba.get():
            messagebox.showerror("Error", "No hay stock suficiente")
            return

        # Selección de precio
        lista = self.lista_precio.get()
        if lista == "detalle":
            precio = producto["detalle"]
        elif lista == "may1":
            precio = producto["may1"]
        elif lista == "may2":
            precio = producto["may2"]
        else:
            precio = producto["detalle"]

        total = precio * cantidad

        # Agregar al carrito
        self.carrito.append({
            "id": producto["id"],
            "codigo": producto["codigo"],
            "descripcion": producto["descripcion"],
            "cantidad": cantidad,
            "precio": precio,
            "total": total
        })

        # Mostrar en tabla
        self.tree.insert("", tk.END, values=(
            producto["codigo"],
            producto["descripcion"],
            cantidad,
            precio,
            total
        ))

        self.actualizar_totales()


    # =========================
    # AJUSTAR CANTIDAD (+1)
    # =========================

    def incrementar_cantidad(self):
        selected = self.tree.selection()
        if not selected:
            return

        index = self.tree.index(selected[0])
        item = self.carrito[index]

        # Validación de stock en modo real
        if not self.modo_prueba.get():
            prod = get_producto(item["codigo"])
            if item["cantidad"] + 1 > prod["stock"]:
                messagebox.showerror("Error", "No hay stock suficiente")
                return

        item["cantidad"] += 1
        item["total"] = item["cantidad"] * item["precio"]

        self.tree.item(selected[0], values=(
            item["codigo"],
            item["descripcion"],
            item["cantidad"],
            item["precio"],
            item["total"]
        ))

        self.actualizar_totales()


    # =========================
    # AJUSTAR CANTIDAD (-1)
    # =========================

    def decrementar_cantidad(self):
        selected = self.tree.selection()
        if not selected:
            return

        index = self.tree.index(selected[0])
        item = self.carrito[index]

        if item["cantidad"] <= 1:
            return

        item["cantidad"] -= 1
        item["total"] = item["cantidad"] * item["precio"]

        self.tree.item(selected[0], values=(
            item["codigo"],
            item["descripcion"],
            item["cantidad"],
            item["precio"],
            item["total"]
        ))

        self.actualizar_totales()


    # =========================
    # ELIMINAR ITEM
    # =========================

    def eliminar_item(self):
        selected = self.tree.selection()
        if not selected:
            return

        index = self.tree.index(selected[0])
        self.tree.delete(selected[0])
        del self.carrito[index]

        self.actualizar_totales()


    # =========================
    # VACIAR CARRITO
    # =========================

    def vaciar_carrito(self):
        self.tree.delete(*self.tree.get_children())
        self.carrito = []
        self.actualizar_totales()


    # =========================
    # ACTUALIZAR TOTALES
    # =========================

    def actualizar_totales(self):
        neto = sum(item["total"] for item in self.carrito)
        iva = round(neto * IVA)
        total = neto + iva

        self.label_total.config(
            text=f"NETO: {neto:,} | IVA: {iva:,} | TOTAL: {total:,}"
        )


    # =========================
    # FINALIZAR VENTA (CON MODO PRUEBA)
    # =========================

    def finalizar_venta(self):
        if not self.carrito:
            return

        neto = sum(item["total"] for item in self.carrito)
        iva = round(neto * IVA)
        total = neto + iva

        # === MODO PRUEBA ===
        if self.modo_prueba.get():
            messagebox.showinfo(
                "Modo prueba",
                f"Venta simulada por TOTAL: {total:,}\n\n"
                f"No se rebajó inventario.\n"
                f"No se registró venta real.\n"
                f"No se exportará a SAP."
            )
            self.vaciar_carrito()
            return

        # === MODO REAL ===
        if messagebox.askyesno("Confirmar", f"Confirmar venta por TOTAL: {total:,}?"):
            venta_id = registrar_venta(
                self.carrito, neto, iva, total, self.tipo_doc.get()
            )

            for item in self.carrito:
                actualizar_stock(item["id"], item["cantidad"])

            messagebox.showinfo("Venta registrada", f"Venta ID: {venta_id}")
            self.vaciar_carrito()

                # =========================
    # BUSCAR PRODUCTO
    # =========================

    def buscar_producto(self):
        palabra = self.entry_buscar.get().strip()
        if not palabra:
            return

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT codigo, descripcion, stock_fisico
            FROM productos
            WHERE descripcion LIKE ?
        """, ("%" + palabra + "%",))
        resultados = cur.fetchall()
        conn.close()

        ventana = tk.Toplevel(self.root)
        ventana.title("Resultados de búsqueda")

        tree = ttk.Treeview(
            ventana,
            style="Custom.Treeview",
            columns=("codigo", "desc", "stock"),
            show="headings"
        )

        tree.heading("codigo", text="Código")
        tree.heading("desc", text="Descripción")
        tree.heading("stock", text="Stock")

        tree.pack(fill=tk.BOTH, expand=True)

        for r in resultados:
            tree.insert("", tk.END, values=r)

        def seleccionar(event):
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])["values"]
            self.entry_codigo.delete(0, tk.END)
            self.entry_codigo.insert(0, item[0])
            ventana.destroy()
            self.entry_codigo.focus()

        tree.bind("<Double-1>", seleccionar)


    # =========================
    # APLICAR DESCUENTO
    # =========================

    def aplicar_descuento(self):
        if not self.carrito:
            return

        try:
            porc = float(self.entry_descuento.get())
        except ValueError:
            messagebox.showerror("Error", "Descuento inválido")
            return

        if porc <= 0:
            return

        factor = (100 - porc) / 100.0

        for item in self.carrito:
            item["precio"] = round(item["precio"] * factor)
            item["total"] = item["precio"] * item["cantidad"]

        # Refrescar tabla
        self.tree.delete(*self.tree.get_children())
        for item in self.carrito:
            self.tree.insert("", tk.END, values=(
                item["codigo"],
                item["descripcion"],
                item["cantidad"],
                item["precio"],
                item["total"]
            ))

        self.actualizar_totales()
        messagebox.showinfo("Descuento", f"Descuento del {porc}% aplicado a toda la venta.")


    # =========================
    # CIERRE DEL DÍA
    # =========================

    def on_close(self):
        if self.modo_prueba.get():
            messagebox.showinfo(
                "Modo prueba",
                "Cierre del día simulado.\nNo se exportó nada a SAP.\nNo se modificó inventario."
            )
            self.root.destroy()
            return

        if messagebox.askyesno("Cerrar día", "¿Deseas exportar las ventas del día a SAP antes de cerrar?"):
            exportar_sap_diario()

        self.root.destroy()


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    root = tk.Tk()
    app = POS(root)
    root.mainloop()
    

