import os
import pandas as pd

# =========================
# CONFIGURACIÓN
# =========================

INVENTORY_FILE = r"D:\Proyectos\Cuesta Blanca Proyect\INFORME CUESTA BLANCA.xlsx"
INVENTORY_SHEET = "CUESTA BLANCA"
OUTPUT_FOLDER = r"D:\Proyectos\Cuesta Blanca Proyect\salidas"

USD_CLP_RATE = 950.0

MARGIN_RETAIL = 1.80
MARGIN_WHOLESALE_1 = 1.50
MARGIN_WHOLESALE_2 = 1.35

IVA_RATE = 0.19


# =========================
# INVENTARIO
# =========================

def load_inventory():
    df = pd.read_excel(INVENTORY_FILE, sheet_name=INVENTORY_SHEET)
    df["Costo_CLP"] = df["Costo"] * USD_CLP_RATE
    df["Precio_Detalle"] = (df["Costo_CLP"] * MARGIN_RETAIL).round(0)
    df["Precio_Mayorista_1"] = (df["Costo_CLP"] * MARGIN_WHOLESALE_1).round(0)
    df["Precio_Mayorista_2"] = (df["Costo_CLP"] * MARGIN_WHOLESALE_2).round(0)
    return df


def save_inventory(df):
    df.to_excel(INVENTORY_FILE, sheet_name=INVENTORY_SHEET, index=False)
    print("\nInventario actualizado guardado correctamente.")


# =========================
# POS / PISTOLA LÁSER
# =========================

def pos_loop(inventory_df, lista_precio="DETALLE"):
    carrito = []

    print("\n==============================")
    print("   SISTEMA POS - ESCANEA")
    print("   Escribe FIN para cerrar venta")
    print("==============================\n")

    while True:
        codigo = input("Escanea código: ").strip()

        if codigo.upper() == "FIN":
            break

        # Buscar producto
        row = inventory_df[inventory_df["Código"] == codigo]

        if row.empty:
            print(f"⚠️ Código no encontrado: {codigo}")
            continue

        row = row.iloc[0]

        # Selección de precio
        if lista_precio == "DETALLE":
            precio = row["Precio_Detalle"]
        elif lista_precio == "MAY1":
            precio = row["Precio_Mayorista_1"]
        elif lista_precio == "MAY2":
            precio = row["Precio_Mayorista_2"]
        else:
            precio = row["Precio_Detalle"]

        carrito.append({
            "Código": codigo,
            "Descripción": row["Descripción"],
            "Cantidad": 1,
            "Precio Unitario": precio,
            "Total Línea": precio
        })

        # Mostrar carrito
        df_carrito = pd.DataFrame(carrito)
        print("\nCarrito actual:")
        print(df_carrito.to_string(index=False))
        print(f"TOTAL: {df_carrito['Total Línea'].sum():,}\n")

    return pd.DataFrame(carrito)


# =========================
# REBAJA DE INVENTARIO
# =========================

def rebajar_inventario(inventory_df, carrito_df):
    for _, row in carrito_df.iterrows():
        codigo = row["Código"]
        qty = row["Cantidad"]

        idx = inventory_df[inventory_df["Código"] == codigo].index[0]
        inventory_df.at[idx, "Stock Físico"] -= qty

    return inventory_df


# =========================
# MAIN
# =========================

def main():
    inv = load_inventory()

    # Iniciar POS
    carrito = pos_loop(inv, lista_precio="DETALLE")

    if carrito.empty:
        print("No se registraron productos.")
        return

    # Calcular totales
    neto = carrito["Total Línea"].sum()
    iva = round(neto * IVA_RATE)
    total = neto + iva

    print("\n==============================")
    print("        BOLETA FINAL")
    print("==============================")
    print(carrito.to_string(index=False))
    print("------------------------------")
    print(f"NETO : {neto:,}")
    print(f"IVA  : {iva:,}")
    print(f"TOTAL: {total:,}")
    print("==============================\n")

    # Rebajar inventario
    inv = rebajar_inventario(inv, carrito)
    save_inventory(inv)


if __name__ == "__main__":
    main()