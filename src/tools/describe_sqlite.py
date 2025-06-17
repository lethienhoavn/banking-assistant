import sqlite3
import pandas as pd

conn = sqlite3.connect('db.sqlite')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(t[0])

# users
# addresses
# products
# carts
# orders
# order_products


df = pd.read_sql_query("SELECT * FROM users LIMIT 5;", conn)
print(df)
print(pd.read_sql_query("SELECT count(*) FROM users;", conn))

#    id              name                     email    password
# 0   1      Marvin Mejia       david11@example.net  Z2QcvXwY%O
# 1   2  Michael Randolph  selenamadden@example.com  Exnd*2NmPs
# 2   3      David Parker  nielsenwendy@example.com  4F+A0gHg!b
# 3   4     Vanessa Young      austin30@example.org  )@T1F+0x%w
# 4   5  Elizabeth Holmes    jennifer91@example.org  *GZzpMntb6

df = pd.read_sql_query("SELECT * FROM addresses LIMIT 5;", conn)
print(df)
print(pd.read_sql_query("SELECT count(*) FROM addresses;", conn))

#    id  user_id                                            address
# 0   1        2                   Unit 6404 Box 5297, DPO AE 13110
# 1   2        2  60141 Harrison Gardens Suite 626, East Jamesst...
# 2   3        3       41126 Angela Port, North Emilyport, OR 34162
# 3   4        4                   Unit 7418 Box 9166, DPO AP 90017
# 4   5        5     782 Brent Junctions, North Brentbury, FM 84956

df = pd.read_sql_query("SELECT * FROM products LIMIT 5;", conn)
print(df)

#    id                  name   price
# 0   1         Frozen Towels  518.42
# 1   2                  Soap  183.65
# 2   3  Intelligent Soft Car  533.60
# 3   4   Handmade Soft Chips  752.84
# 4   5         Refined Shirt  195.27

df = pd.read_sql_query("SELECT * FROM carts LIMIT 5;", conn)
print(df)

#    id  user_id  product_id  quantity
# 0   1       86           1         3
# 1   2     1247           1         2
# 2   3      381           1         1
# 3   4     1535           2         6
# 4   5       23           3         2

df = pd.read_sql_query("SELECT * FROM orders LIMIT 5;", conn)
print(df)

#    id  user_id              created
# 0   1      323  2025-05-12 00:00:00
# 1   2      853  2026-11-17 00:00:00
# 2   3     1251  2025-01-10 00:00:00
# 3   4       96  2023-02-27 00:00:00
# 4   5     1197  2026-09-13 00:00:00

df = pd.read_sql_query("SELECT * FROM order_products LIMIT 5;", conn)
print(df)

#    id  order_id  product_id  amount
# 0   1         1         737      10
# 1   2         1        3396       7
# 2   3         1        3245       8
# 3   4         1        2683       3
# 4   5         2        3497       3

conn.close()