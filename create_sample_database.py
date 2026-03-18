import sqlite3

conn = sqlite3.connect("inventory_system.db")
cursor = conn.cursor()

# PRODUCTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
product_id INTEGER PRIMARY KEY AUTOINCREMENT,
product_name TEXT,
stock INTEGER,
min_stock INTEGER,
last_price INTEGER
)
""")

# INVOICES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_number TEXT,
supplier_name TEXT,
invoice_date TEXT,
grand_total INTEGER
)
""")

# INVOICE ITEMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS invoice_items(
item_id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_number TEXT,
product_name TEXT,
qty INTEGER,
rate INTEGER,
amount INTEGER
)
""")

# SAMPLE PRODUCTS
products = [

("Cotton Fabric Roll",120,30,120),
("Polyester Fabric",80,20,150),
("Silk Fabric",40,10,350),
("Denim Fabric",65,15,200),
("Linen Fabric",30,10,180),
("Rayon Fabric",90,25,140),
("Wool Fabric",25,10,420),
("Cotton Fabric",120,30,120)

]

cursor.executemany("""
INSERT INTO products(product_name,stock,min_stock,last_price)
VALUES(?,?,?,?)
""",products)

conn.commit()

print("Sample database created successfully")
conn.close()