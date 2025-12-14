from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "kalaconnect_secret"

DB = "kalaconnect.db"

# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    c = db.cursor()

    # Users
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT
    )""")

    # Sellers
    c.execute("""CREATE TABLE IF NOT EXISTS sellers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT
    )""")

    # Products
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price REAL, description TEXT,
        image TEXT, seller_id INTEGER, status TEXT
    )""")

    # Cart
    c.execute("""CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, product_id INTEGER
    )""")

    # Orders
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        payment_mode TEXT,
        address TEXT,
        status TEXT
    )""")

    # Reviews
    c.execute("""CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        comment TEXT, rating INTEGER
    )""")

    conn = db
    conn.commit()
    db.close()

init_db()

# ---------------- USER ----------------

@app.route('/')
def home():
    db = get_db()
    products = db.execute("SELECT * FROM products WHERE status='approved'").fetchall()
    return render_template("index.html", products=products)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        db=get_db()
        try:
            db.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                       (name,email,password))
            db.commit()
            return redirect('/login')
        except:
            flash("Email already exists")
    return render_template("signup.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        db=get_db()
        user=db.execute("SELECT * FROM users WHERE email=? AND password=?",
                        (email,password)).fetchone()
        if user:
            session['user_id']=user['id']
            return redirect('/')
        else:
            flash("Invalid login")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/product/<int:id>')
def product_detail(id):
    db=get_db()
    product=db.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    reviews=db.execute("""
        SELECT r.*,u.name FROM reviews r
        JOIN users u ON r.user_id=u.id
        WHERE product_id=?""",(id,)).fetchall()
    return render_template("product_detail.html", product=product, reviews=reviews)

@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    db=get_db()
    db.execute("INSERT INTO cart(user_id,product_id) VALUES(?,?)",
               (session['user_id'],id))
    db.commit()
    return redirect('/cart')

@app.route('/cart')
def cart():
    db=get_db()
    items=db.execute("""
        SELECT p.* FROM cart c
        JOIN products p ON c.product_id=p.id
        WHERE c.user_id=?""",(session['user_id'],)).fetchall()
    total=sum([i['price'] for i in items])
    return render_template("cart.html", items=items, total=total)

# ---------------- PAYMENT + DELIVERY ----------------

@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if request.method=='POST':
        address=request.form['address']
        payment=request.form['payment']
        db=get_db()
        items=db.execute("""
            SELECT p.* FROM cart c 
            JOIN products p ON c.product_id=p.id 
            WHERE c.user_id=?""",(session['user_id'],)).fetchall()
        total=sum([i['price'] for i in items])

        db.execute("""INSERT INTO orders(user_id,total,payment_mode,address,status)
                      VALUES(?,?,?,?,?)""",
                   (session['user_id'],total,payment,address,"Placed"))
        db.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
        db.commit()
        return redirect('/orders')
    return render_template("checkout.html")

@app.route('/orders')
def orders():
    db=get_db()
    orders=db.execute("SELECT * FROM orders WHERE user_id=?",
                      (session['user_id'],)).fetchall()
    return render_template("orders.html", orders=orders)

# ---------------- SELLER / ARTIST ----------------

@app.route('/seller_signup', methods=['GET','POST'])
def seller_signup():
    if request.method=='POST':
        db=get_db()
        db.execute("INSERT INTO sellers(name,email,password) VALUES(?,?,?)",
                   (request.form['name'],request.form['email'],request.form['password']))
        db.commit()
        return redirect('/seller_login')
    return render_template("seller_signup.html")

@app.route('/seller_login', methods=['GET','POST'])
def seller_login():
    if request.method=='POST':
        db=get_db()
        seller=db.execute("SELECT * FROM sellers WHERE email=? AND password=?",
                          (request.form['email'],request.form['password'])).fetchone()
        if seller:
            session['seller_id']=seller['id']
            return redirect('/seller_dashboard')
    return render_template("seller_login.html")

@app.route('/seller_dashboard')
def seller_dashboard():
    db=get_db()
    products=db.execute("SELECT * FROM products WHERE seller_id=?",
                        (session['seller_id'],)).fetchall()
    return render_template("seller_dashboard.html", products=products)

@app.route('/add_product', methods=['GET','POST'])
def add_product():
    if request.method=='POST':
        db=get_db()
        db.execute("""INSERT INTO products
            (name,price,description,image,seller_id,status)
            VALUES(?,?,?,?,?,?)""",
            (request.form['name'],request.form['price'],
             request.form['description'],request.form['image'],
             session['seller_id'],"pending"))
        db.commit()
        return redirect('/seller_dashboard')
    return render_template("add_product.html")

# ---------------- ADMIN ----------------

@app.route('/admin')
def admin_login():
    return render_template("admin_login.html")

@app.route('/admin_dashboard')
def admin_dashboard():
    db=get_db()
    products=db.execute("SELECT * FROM products").fetchall()
    orders=db.execute("SELECT * FROM orders").fetchall()
    sellers=db.execute("SELECT * FROM sellers").fetchall()
    return render_template("admin_dashboard.html",
                           products=products,orders=orders,sellers=sellers)

@app.route('/approve_product/<int:id>')
def approve_product(id):
    db=get_db()
    db.execute("UPDATE products SET status='approved' WHERE id=?", (id,))
    db.commit()
    return redirect('/admin_dashboard')

@app.route('/update_order/<int:id>')
def update_order(id):
    db=get_db()
    db.execute("UPDATE orders SET status='Delivered' WHERE id=?", (id,))
    db.commit()
    return redirect('/admin_dashboard')

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)
