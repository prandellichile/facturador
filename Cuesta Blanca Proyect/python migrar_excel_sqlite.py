import pandas as pd
import sqlite3

# =========================
# CONFIG
# =========================

EXCEL_FILE = r"D:\Proyectos\Cuesta Blanca Proyect\INFORME CUESTA BLANCA.xlsx"
SHEET = "CUESTA BLANCA"
DB_FILE = "inventario.db"

USD_CLP = 950
MARGIN_RETAIL = 1.80
MARGIN_MAY1 = 1.50
MARGIN_MAY2 = 1.35


# =========================
# CARGAR EXCEL
# =========================

df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET)

# Calcular costos y precios
df["Costo_CLP"] = df["Costo"] * USD_CLP
df["Precio_Detalle"] = (df["Costo_CLP"] * MARGIN_RETAIL).round(0)
df["Precio_May1"] = (df["Costo_CLP"] * MARGIN_MAY1).round(0)
df["Precio_May2"] = (df["Costo_CLP"] * MARGIN_MAY2).round(0)

# Nueva columna
df["Unidades_Salientes"] = 0


# =========================
# CREAR BASE DE DATOS
# =========================

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE,
    descripcion TEXT,
    familia TEXT,
    unidad_medida TEXT,
    stock_fisico INTEGER,
    costo_usd REAL,
    costo_clp REAL,
    precio_detalle REAL,
    precio_may1 REAL,
    precio_may2 REAL,
    unidades_salientes INTEGER,
    ean TEXT,
    bodega TEXT,
    ubicacion TEXT
)
""")

# Insertar productos
for _, row in df.iterrows():
    cur.execute("""
        INSERT OR REPLACE INTO productos (
            codigo, descripcion, familia, unidad_medida,
            stock_fisico, costo_usd, costo_clp,
            precio_detalle, precio_may1, precio_may2,
            unidades_salientes, ean, bodega, ubicacion
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["Código"],
        row["Descripción"],
        row["Familia"],
        row["Unidad de Medida"],
        row["Stock Físico"],
        row["Costo"],
        row["Costo_CLP"],
        row["Precio_Detalle"],
        row["Precio_May1"],
        row["Precio_May2"],
        row["Unidades_Salientes"],
        row["EAN UA"],
        row["Bodega"],
        row["Ubicación"]
    ))

conn.commit()
conn.close()

print("\nMigración completada. Base de datos creada: inventario.db")