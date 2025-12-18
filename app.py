from flask import Flask, render_template, request, redirect, session, flash
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = "kalaconnect_secret"
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/yourdbname"

# ---------------- DATABASE ----------------

def get_db():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS sellers(
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id SERIAL PRIMARY KEY,
        name TEXT,
        price NUMERIC,
        description TEXT,
        image TEXT,
        seller_id INTEGER,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS cart(
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        product_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        total NUMERIC,
        payment_mode TEXT,
        address TEXT,
        status TEXT
    )
    """)

    db.commit()
    db.close()

@app.route('/')
def home():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products WHERE status='approved'")
    products = c.fetchall()
    return render_template("index.html", products=products)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        try:
            db = get_db()
            c = db.cursor()
            c.execute(
                "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
                (request.form['name'], request.form['email'], request.form['password'])
            )
            db.commit()
            return redirect('/login')
        except:
            flash("Email already exists")
    return render_template("signup.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (request.form['email'], request.form['password'])
        )
        user = c.fetchone()
        if user:
            session['user_id'] = user['id']
            return redirect('/')
        flash("Invalid login")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- CART ----------------

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    if 'user_id' not in session:
        return redirect('/login')

    db = get_db()
    c = db.cursor()
    c.execute(
        "INSERT INTO cart(user_id,product_id) VALUES(%s,%s)",
        (session['user_id'], id)
    )
    db.commit()
    return redirect('/cart')

@app.route('/cart')
def cart():
    db = get_db()
    c = db.cursor()
    c.execute("""
        SELECT p.* FROM cart c
        JOIN products p ON c.product_id=p.id
        WHERE c.user_id=%s
    """, (session['user_id'],))
    items = c.fetchall()
    total = sum(float(i['price']) for i in items)
    return render_template("cart.html", items=items, total=total)

# ---------------- CHECKOUT / DELIVERY ----------------

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()

        c.execute("""
            SELECT p.price FROM cart c
            JOIN products p ON c.product_id=p.id
            WHERE c.user_id=%s
        """, (session['user_id'],))
        items = c.fetchall()
        total = sum(float(i['price']) for i in items)

        c.execute("""
            INSERT INTO orders(user_id,total,payment_mode,address,status)
            VALUES(%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            total,
            request.form['payment'],
            request.form['address'],
            "Placed"
        ))

        c.execute("DELETE FROM cart WHERE user_id=%s", (session['user_id'],))
        db.commit()
        return redirect('/orders')

    return render_template("checkout.html")

@app.route('/orders')
def orders():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM orders WHERE user_id=%s", (session['user_id'],))
    orders = c.fetchall()
    return render_template("orders.html", orders=orders)

# ---------------- SELLER ----------------

@app.route('/seller_signup', methods=['GET','POST'])
def seller_signup():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute(
            "INSERT INTO sellers(name,email,password) VALUES(%s,%s,%s)",
            (request.form['name'], request.form['email'], request.form['password'])
        )
        db.commit()
        return redirect('/seller_login')
    return render_template("seller_signup.html")

@app.route('/seller_login', methods=['GET','POST'])
def seller_login():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute(
            "SELECT * FROM sellers WHERE email=%s AND password=%s",
            (request.form['email'], request.form['password'])
        )
        seller = c.fetchone()
        if seller:
            session['seller_id'] = seller['id']
            return redirect('/seller_dashboard')
    return render_template("seller_login.html")

@app.route('/seller_dashboard')
def seller_dashboard():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products WHERE seller_id=%s", (session['seller_id'],))
    products = c.fetchall()
    return render_template("seller_dashboard.html", products=products)

@app.route('/add_product', methods=['GET','POST'])
def add_product():
    if request.method == 'POST':
        db = get_db()
        c = db.cursor()
        c.execute("""
            INSERT INTO products(name,price,description,image,seller_id,status)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['price'],
            request.form['description'],
            request.form['image'],
            session['seller_id'],
            "pending"
        ))
        db.commit()
        return redirect('/seller_dashboard')
    return render_template("add_product.html")

# ---------------- ADMIN ----------------

@app.route('/admin_dashboard')
def admin_dashboard():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    c.execute("SELECT * FROM orders")
    orders = c.fetchall()
    return render_template("admin_dashboard.html", products=products, orders=orders)

@app.route('/approve_product/<int:id>')
def approve_product(id):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE products SET status='approved' WHERE id=%s", (id,))
    db.commit()
    return redirect('/admin_dashboard')

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)
