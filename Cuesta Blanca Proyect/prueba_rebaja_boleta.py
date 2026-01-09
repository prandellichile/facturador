import pandas as pd

# =========================
# CONFIGURACIÓN
# =========================

INVENTARIO = r"D:\Proyectos\Cuesta Blanca Proyect\INFORME CUESTA BLANCA.xlsx"
HOJA = "CUESTA BLANCA"

USD_CLP = 950
MARGIN = 1.80
IVA = 0.19


# =========================
# CARGAR INVENTARIO
# =========================

def cargar_inventario():
    df = pd.read_excel(INVENTARIO, sheet_name=HOJA)
    df["Costo_CLP"] = df["Costo"] * USD_CLP
    df["Precio_Detalle"] = (df["Costo_CLP"] * MARGIN).round(0)
    return df


# =========================
# GUARDAR INVENTARIO
# =========================

def guardar_inventario(df):
    df.to_excel(INVENTARIO, sheet_name=HOJA, index=False)
    print("\nInventario actualizado guardado correctamente.")


# =========================
# BOLETA
# =========================

def generar_boleta(producto, cantidad):
    precio = producto["Precio_Detalle"]
    total_linea = precio * cantidad
    neto = total_linea
    iva = round(neto * IVA)
    total = neto + iva

    print("\n==============================")
    print("          BOLETA")
    print("==============================")
    print(f"Código      : {producto['Código']}")
    print(f"Descripción : {producto['Descripción']}")
    print(f"Cantidad    : {cantidad}")
    print(f"Precio      : {precio:,}")
    print("------------------------------")
    print(f"NETO        : {neto:,}")
    print(f"IVA         : {iva:,}")
    print(f"TOTAL       : {total:,}")
    print("==============================\n")


# =========================
# MAIN
# =========================

def main():
    inv = cargar_inventario()

    print("\n====================================")
    print("   PRUEBA: ESCANEO + REBAJA + BOLETA")
    print("====================================\n")

    codigo = input("Escanea el producto: ").strip()

    # Buscar producto
    fila = inv[inv["Código"] == codigo]

    if fila.empty:
        print(f"\n⚠️ Código no encontrado en inventario: {codigo}")
        return

    producto = fila.iloc[0]

    print(f"\nProducto encontrado: {producto['Descripción']}")
    print(f"Stock actual: {producto['Stock Físico']}")

    # Cantidad a rebajar
    cantidad = int(input("\nCantidad a rebajar: "))

    if cantidad > producto["Stock Físico"]:
        print("\n❌ No hay suficiente stock.")
        return

    # Rebajar stock
    idx = inv[inv["Código"] == codigo].index[0]
    inv.at[idx, "Stock Físico"] -= cantidad

    # Generar boleta
    generar_boleta(producto, cantidad)

    # Guardar inventario actualizado
    guardar_inventario(inv)


if __name__ == "__main__":
    main()