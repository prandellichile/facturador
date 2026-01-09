import sqlite3
import datetime
import pandas as pd

# =========================
# CONFIGURACIÓN
# =========================

DB_FILE = "inventario.db"
IVA = 0.19


# =========================
# CONEXIÓN A SQLITE
# =========================

def get_conn():
    return sqlite3.connect(DB_FILE)


# =========================
# OBTENER PRODUCTO POR CÓDIGO
# =========================

def get_producto_por_codigo(codigo):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, codigo, descripcion, stock_fisico,
               precio_detalle, precio_may1, precio_may2,
               unidades_salientes
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
        "stock_fisico": row[3],
        "precio_detalle": row[4],
        "precio_may1": row[5],
        "precio_may2": row[6],
        "unidades_salientes": row[7]
    }


# =========================
# ACTUALIZAR STOCK Y SALIENTES
# =========================

def actualizar_stock_y_salientes(producto_id, cantidad):
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

def registrar_venta(carrito, total_neto, total_iva, total_total):
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
            total_linea REAL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id)
        )
    """)

    cur.execute("""
        INSERT INTO ventas (fecha, total_neto, total_iva, total_total)
        VALUES (?, ?, ?, ?)
    """, (fecha, total_neto, total_iva, total_total))

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
            item["precio_unitario"],
            item["total_linea"]
        ))

    conn.commit()
    conn.close()

    return venta_id


# =========================
# POS PROFESIONAL EN CONSOLA
# =========================

def pos_consola(lista_precio="DETALLE"):
    carrito = []

    print("\n====================================")
    print("   POS PROFESIONAL - CONSOLA")
    print("   Escanea productos con la pistola")
    print("   Escribe FIN para cerrar venta")
    print("   Escribe BORRAR para vaciar carrito")
    print("====================================\n")

    while True:
        codigo = input("Escanea código: ").strip()

        if codigo.upper() == "FIN":
            break

        if codigo.upper() == "BORRAR":
            carrito = []
            print("\nCarrito vaciado.\n")
            continue

        producto = get_producto_por_codigo(codigo)

        if not producto:
            print(f"⚠️ Código no encontrado: {codigo}\n")
            continue

        print(f"Producto: {producto['descripcion']}")
        print(f"Stock actual: {producto['stock_fisico']}")

        try:
            cantidad = int(input("Cantidad (ENTER = 1): ") or "1")
        except ValueError:
            print("Cantidad inválida.\n")
            continue

        if cantidad <= 0:
            print("Cantidad debe ser mayor a 0.\n")
            continue

        if cantidad > producto["stock_fisico"]:
            print("❌ No hay stock suficiente.\n")
            continue

        # Selección de precio
        if lista_precio == "DETALLE":
            precio = producto["precio_detalle"]
        elif lista_precio == "MAY1":
            precio = producto["precio_may1"]
        elif lista_precio == "MAY2":
            precio = producto["precio_may2"]
        else:
            precio = producto["precio_detalle"]

        total_linea = precio * cantidad

        carrito.append({
            "id": producto["id"],
            "codigo": producto["codigo"],
            "descripcion": producto["descripcion"],
            "cantidad": cantidad,
            "precio_unitario": precio,
            "total_linea": total_linea
        })

        df_carrito = pd.DataFrame(carrito)
        print("\nCarrito actual:")
        print(df_carrito[["codigo", "descripcion", "cantidad", "precio_unitario", "total_linea"]].to_string(index=False))
        print(f"\nTOTAL PARCIAL: {df_carrito['total_linea'].sum():,}\n")

    if not carrito:
        print("\nNo se registraron productos.\n")
        return

    df_carrito = pd.DataFrame(carrito)
    neto = df_carrito["total_linea"].sum()
    iva = round(neto * IVA)
    total = neto + iva

    print("\n==============================")
    print("          BOLETA")
    print("==============================")
    print(df_carrito[["codigo", "descripcion", "cantidad", "precio_unitario", "total_linea"]].to_string(index=False))
    print("------------------------------")
    print(f"NETO : {neto:,}")
    print(f"IVA  : {iva:,}")
    print(f"TOTAL: {total:,}")
    print("==============================\n")

    confirmar = input("Confirmar venta y rebajar stock? (S/N): ").strip().upper()
    if confirmar != "S":
        print("\nVenta cancelada. No se modificó el inventario.\n")
        return

    for item in carrito:
        actualizar_stock_y_salientes(item["id"], item["cantidad"])

    venta_id = registrar_venta(carrito, neto, iva, total)

    print(f"\n✅ Venta registrada con ID: {venta_id}")
    print("✅ Stock actualizado y unidades salientes incrementadas.\n")


# =========================
# MAIN
# =========================

def main():
    print("\nSelecciona lista de precios:")
    print("1) Detalle")
    print("2) Mayorista 1")
    print("3) Mayorista 2")

    opcion = input("Opción (1/2/3): ").strip()

    if opcion == "1":
        lista = "DETALLE"
    elif opcion == "2":
        lista = "MAY1"
    elif opcion == "3":
        lista = "MAY2"
    else:
        lista = "DETALLE"

    pos_consola(lista_precio=lista)


if __name__ == "__main__":
    main()