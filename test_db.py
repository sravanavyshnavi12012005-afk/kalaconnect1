import psycopg2

try:
    conn = psycopg2.connect(
        dbname="kalaconnectdb",
        user="postgres",
        password="1234",
        host="localhost",
        port="5432"
    )
    print("Connected to PostgreSQL!")
except Exception as e:
    print("Error:", e)
