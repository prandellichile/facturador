import sqlite3
DB = r'D:\Proyectos\Cuesta Blaca Proyect Vers. 2.0\bd\pos_full.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM products")
print("COUNT:", cur.fetchone()[0])
cur.execute("SELECT codigo, descripcion, categoria, stock_fisico FROM products LIMIT 10")
for r in cur.fetchall():
    print(r)
conn.close()