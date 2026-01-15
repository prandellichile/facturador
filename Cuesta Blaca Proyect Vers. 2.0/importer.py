# importer.py
# Ejecutar: python importer.py
# Importa productos desde Excel a la BD pos_full.db (idempotente)

import os
import sqlite3
import pandas as pd
from datetime import datetime
import logging

BASE_DIR = r'D:\Proyectos\Cuesta Blaca Proyect Vers. 2.0'
EXCEL_DIR = os.path.join(BASE_DIR, 'fuentes')
EXCEL_FILENAME = 'INFORME CUESTA BLANCA().xlsx'
EXCEL_PATH = os.path.join(EXCEL_DIR, EXCEL_FILENAME)
DB_PATH = os.path.join(BASE_DIR, 'bd', 'pos_full.db')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
LOG_PATH = os.path.join(LOGS_DIR, 'importer.log')

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

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
"""

def init_db(conn):
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)
    conn.commit()

def import_products(conn, excel_path):
    if not os.path.exists(excel_path):
        logging.error(f"Excel no encontrado: {excel_path}")
        raise FileNotFoundError(excel_path)

    df = pd.read_excel(excel_path, sheet_name=0, dtype=str)
    df = df.rename(columns={
        'Familia':'familia',
        'Código':'codigo',
        'Descripción':'descripcion',
        'Categoria':'categoria',
        'Modelo':'modelo',
        'Color':'color',
        'Talla':'talla',
        'Unidad de Medida':'unidad_medida',
        'Bodega':'bodega',
        'Ubicación':'ubicacion',
        'Unidad de Almacenamiento':'unidad_almacenamiento',
        'EAN UA':'ean_ua',
        'Stock Físico':'stock_fisico'
    })
    df = df.fillna('')

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        codigo = str(row.get('codigo','')).strip()
        if not codigo:
            continue
        sf = row.get('stock_fisico','')
        try:
            stock_val = int(float(str(sf).replace(',',''))) if sf not in ('', None) else 0
        except:
            stock_val = 0

        cur.execute("""
            INSERT OR REPLACE INTO products
            (familia, codigo, descripcion, categoria, modelo, color, talla, unidad_medida, bodega, ubicacion, unidad_almacenamiento, ean_ua, stock_fisico, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get('familia',''),
            codigo,
            row.get('descripcion',''),
            row.get('categoria',''),
            row.get('modelo',''),
            row.get('color',''),
            row.get('talla',''),
            row.get('unidad_medida',''),
            row.get('bodega',''),
            row.get('ubicacion',''),
            row.get('unidad_almacenamiento',''),
            row.get('ean_ua',''),
            stock_val,
            datetime.now().isoformat()
        ))
        inserted += 1

    conn.commit()
    logging.info(f"Importación completada. Filas procesadas: {inserted}")
    return inserted

def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    try:
        n = import_products(conn, EXCEL_PATH)
        print(f"Importación finalizada. Filas: {n}")
    except Exception as e:
        logging.exception("Error en importación")
        print("Error en importación:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()