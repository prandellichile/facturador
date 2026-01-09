import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import datetime

DB_FILE = "inventario.db"
IVA = 0.19


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

def registrar_venta(carrito, neto, iva, total):
    conn = get_conn()
    cur = conn.cursor()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            total_neto REAL,
            total_iva REAL,
            total_total REAL
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

    cur.execute("""
        INSERT INTO ventas (fecha, total_neto, total_iva, total_total)
        VALUES (?, ?, ?, ?)
    """, (fecha, neto, iva, total))

    venta_id = cur.lastrowid

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
# INTERFAZ GRÁFICA
# =========================

class POS:
    def __init__(self, root):
        self.root = root
        self.root.title("POS Profesional - Cuesta Blanca")
        self.carrito = []
        self.lista_precio = tk.StringVar(value="detalle")

        # Entrada de código
        tk.Label(root, text="Escanear código:").grid(row=0, column=0)
        self.entry_codigo = tk.Entry(root, width=30)
        self.entry_codigo.grid(row=0, column=1)
        self.entry_codigo.bind("<Return>", self.agregar_producto)

        # Botón agregar
        tk.Button(root, text="Agregar", command=self.agregar_producto).grid(row=0, column=2)

        # Selector de lista de precios
        tk.Label(root, text="Lista de precios:").grid(row=1, column=0)
        ttk.Combobox(root, textvariable=self.lista_precio,
                     values=["detalle", "may1", "may2"]).grid(row=1, column=1)

        # Tabla
        self.tree = ttk.Treeview(root, columns=("codigo", "desc", "cant", "precio", "total"), show="headings")
        for col in ("codigo", "desc", "cant", "precio", "total"):
            self.tree.heading(col, text=col.capitalize())
        self.tree.grid(row=2, column=0, columnspan=3)

        # Totales
        self.label_total = tk.Label(root, text="TOTAL: 0")
        self.label_total.grid(row=3, column=0, columnspan=3)

        # Botones
        tk.Button(root, text="Eliminar ítem", command=self.eliminar_item).grid(row=4, column=0)
        tk.Button(root, text="Vaciar carrito", command=self.vaciar_carrito).grid(row=4, column=1)
        tk.Button(root, text="Finalizar venta", command=self.finalizar_venta).grid(row=4, column=2)

    # =========================
    # AGREGAR PRODUCTO
    # =========================

    def agregar_producto(self, event=None):
        codigo = self.entry_codigo.get().strip()
        self.entry_codigo.delete(0, tk.END)

        producto = get_producto(codigo)
        if not producto:
            messagebox.showerror("Error", "Producto no encontrado")
            return

        precio = producto[self.lista_precio.get()]
        cantidad = 1
        total = precio * cantidad

        self.carrito.append({
            "id": producto["id"],
            "codigo": producto["codigo"],
            "descripcion": producto["descripcion"],
            "cantidad": cantidad,
            "precio": precio,
            "total": total
        })

        self.tree.insert("", tk.END, values=(producto["codigo"], producto["descripcion"], cantidad, precio, total))
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
        self.label_total.config(text=f"TOTAL: {total:,}")

    # =========================
    # FINALIZAR VENTA
    # =========================

    def finalizar_venta(self):
        if not self.carrito:
            return

        neto = sum(item["total"] for item in self.carrito)
        iva = round(neto * IVA)
        total = neto + iva

        venta_id = registrar_venta(self.carrito, neto, iva, total)

        for item in self.carrito:
            actualizar_stock(item["id"], item["cantidad"])

        messagebox.showinfo("Venta registrada", f"Venta ID: {venta_id}")

        self.vaciar_carrito()


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    root = tk.Tk()
    app = POS(root)
    root.mainloop()