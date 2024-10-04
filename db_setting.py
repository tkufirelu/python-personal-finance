import mysql.connector
from mysql.connector import errorcode

# 連線到 MariaDB（不指定資料庫）
conn = mysql.connector.connect(
    host="localhost",
    user="firelu",
    password="atx121",
    charset="utf8mb4",
    collation="utf8mb4_general_ci"
)

cursor = conn.cursor()

# 檢查資料庫是否存在，如果不存在則建立
database_name = "finan"
try:
    cursor.execute(f"USE {database_name}")
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        cursor.execute(f"CREATE DATABASE {database_name} DEFAULT CHARACTER SET 'utf8mb4' COLLATE 'utf8mb4_general_ci'")
        cursor.execute(f"USE {database_name}")
    else:
        print(err)
        exit(1)

# 連線到指定的資料庫
conn.database = database_name

# 建立 cash 資料表
cursor.execute(
    """CREATE TABLE cash (
        transaction_id INT PRIMARY KEY AUTO_INCREMENT, 
        taiwanese_dollars INT, 
        us_dollars FLOAT,
        jp_dollars FLOAT,
        eu_dollars FLOAT,
        note VARCHAR(30), 
        date_info DATE,
        user_id VARCHAR(80)
    )"""
)

# 建立 stock 資料表
cursor.execute(
    """CREATE TABLE stock (
        transaction_id INT PRIMARY KEY AUTO_INCREMENT, 
        stock_id VARCHAR(10), 
        stock_num INT, 
        stock_price FLOAT, 
        processing_fee INT, 
        tax INT, 
        date_info DATE,
        user_id VARCHAR(80)
    )"""
)


# 建立 users 資料表
cursor.execute(
    """CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255)
    )"""
)


conn.commit()
conn.close()