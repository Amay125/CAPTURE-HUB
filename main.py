from flask import Flask, render_template, url_for, request, redirect, session, jsonify
import random
import mysql.connector  # For database connection
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'my_secret_key_for_development')

# Database Connection Function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='amay',
            database='capturehub',
            port=3306
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# Initialize cart in session
@app.before_request
def initialize_cart():
    if 'cart' not in session:
        session['cart'] = []

# Home Route
@app.route('/')
def home():
    success_message = session.pop('success_message', None)
    return render_template('homepage.html', success_message=success_message)

# Cinematography Cameras Route
@app.route('/cinematography')
def cinematography():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE category='cinematography'")
        products = cursor.fetchall()
        connection.close()
    else:
        products = []
    return render_template('cinematography.html', products=products)

# Cameras Route
@app.route('/camera')
def camera():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE category='camera'")
        products = cursor.fetchall()
        connection.close()
    else:
        products = []
    return render_template('camera.html', products=products)

# Lenses Route
@app.route('/lens')
def lens():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE category='lens'")
        products = cursor.fetchall()
        connection.close()
    else:
        products = []
    return render_template('lens.html', products=products)

# Accessories Route
@app.route('/accessories')
def accessories():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE category='accessories'")
        products = cursor.fetchall()
        connection.close()
    else:
        products = []
    return render_template('accessories.html', products=products)

# Add to Cart Route
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product = {
        'id': request.form['product_id'],
        'name': request.form['name'],
        'price': float(request.form['price']),
        'image': request.form['image']
    }
    if 'user_id' not in session:
        session['pending_cart_item'] = product
        session.modified = True
        return redirect(url_for('login', next=url_for('cart')))

    session['cart'].append(product)
    session.modified = True
    return redirect(url_for('cart'))

# Cart Route
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('cart')))

    pending_cart_item = session.pop('pending_cart_item', None)
    if pending_cart_item:
        session['cart'].append(pending_cart_item)
        session.modified = True

    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)
    return render_template('cart.html', cart=cart, total=total)

# Remove from Cart Route
@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    product_id = request.form['product_id']
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))

# Checkout Route
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('checkout')))

    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)

    if request.method == 'POST':
        address = request.form['address']
        contact = request.form['contact']

        # Create an order in the database
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute("INSERT INTO orders (user_id, total_amount, address, contact, payment_method, transaction_id) VALUES (%s, %s, %s, %s, %s, %s)",
                               (session['user_id'], total, address, contact, 'Cash', 'TX' + str(random.randint(100000, 999999))))
                order_id = cursor.lastrowid
                for item in cart:
                    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                                   (order_id, item['id'], 1, item['price']))
                connection.commit()
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                return "An error occurred. Please try again."
            finally:
                connection.close()

        session['success_message'] = "Order placed successfully!"
        session['cart'] = []
        session.modified = True

        return redirect(url_for('home'))

    return render_template('checkout.html', cart=cart, total=total)

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Database logic to insert new user
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
                cursor.execute(query, (username, email, password))
                connection.commit()
                print("Signup data stored successfully.")
                session['user_id'] = cursor.lastrowid  # Store user ID in session
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                return "An error occurred. Please try again."
            finally:
                connection.close()

        return redirect(url_for('home'))  # Redirect to home after signup
    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Database logic to authenticate user
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM users WHERE email = %s AND password = %s"
                cursor.execute(query, (email, password))
                user = cursor.fetchone()
                if user:
                    session['user_id'] = user['id']  # Store user ID in session
                    next_page = request.args.get('next', url_for('home'))
                    return redirect(next_page)  # Redirect to the next page after login
                else:
                    return "Invalid email or password."
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                return "An error occurred. Please try again."
            finally:
                connection.close()

    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove the user_id from session
    session.pop('admin_id', None)  # Remove the admin_id from session
    return redirect(url_for('home'))

# Running the app
if __name__ == "__main__":
    app.run(debug=True)
