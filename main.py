from flask import Flask, render_template, url_for, request, redirect, session, jsonify
import random
import mysql.connector  # For database connection
import stripe

app = Flask(__name__)
scss(app)

# Set your Stripe secret key
stripe.api_key = 'sk_test_51QkJsDRxZJyYZLXmVstJI7TBlPxiGH5q62ccQnVwy59v24Syp7Y2t0vo4bXDTW0MJB93VmnMoE8UBLJ6OhfptPVT004MOTCjEj'

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
    return render_template('homepage.html')

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

# Create Checkout Session Route
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)

    stripe_checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',  # Change currency to INR
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': int(item['price'] * 100),  # Stripe expects amount in smallest currency unit (paisa for INR)
            },
            'quantity': 1,
        } for item in cart],
        mode='payment',
        success_url=url_for('receipt', _external=True),
        cancel_url=url_for('cart', _external=True),
        metadata={
            'address': data['address'],
            'contact': data['contact']
        }
    )
    return jsonify({'id': stripe_checkout_session.id})

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
                               (session['user_id'], total, address, contact, 'Stripe', 'TX' + str(random.randint(100000, 999999))))
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

        receipt = {
            'transaction_id': 'TX' + str(random.randint(100000, 999999)),
            'total': total,
            'address': address,
            'contact': contact,
            'payment_method': 'Stripe',
            'cart': cart
        }

        session['receipt'] = receipt  # Store receipt in session
        session['cart'] = []
        session.modified = True

        return redirect(url_for('receipt'))

    return render_template('checkout.html', cart=cart, total=total)

# Receipt Route
@app.route('/receipt')
def receipt():
    # Assuming the receipt data is stored in the session after a successful payment
    receipt = session.get('receipt', None)
    if not receipt:
        return redirect(url_for('cart'))
    return render_template('receipt.html', receipt=receipt)

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login', next=url_for('dashboard')))

    user_id = session['user_id']
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        cursor.execute("SELECT o.id, o.total_amount, o.address, o.contact, o.payment_method, o.transaction_id, o.created_at, GROUP_CONCAT(oi.product_id, ':', oi.quantity, ':', oi.price SEPARATOR ';') as items FROM orders o JOIN order_items oi ON o.id = oi.order_id WHERE o.user_id = %s GROUP BY o.id", (user_id,))
        orders = cursor.fetchall()

        for order in orders:
            order['items'] = [{'product_id': int(item.split(':')[0]), 'quantity': int(item.split(':')[1]), 'price': float(item.split(':')[2])} for item in order['items'].split(';')]

        connection.close()
    else:
        user = None
        orders = []

    return render_template('dashboard.html', user=user, orders=orders)

# Admin Login Route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Database logic to authenticate admin user
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM users WHERE email = %s AND password = %s"
                cursor.execute(query, (email, password))
                user = cursor.fetchone()
                if user:
                    session['admin_id'] = user['id']  # Store admin ID in session
                    return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after login
                else:
                    return "Invalid email or password."
            except mysql.connector.Error as err:
                print(f"Error: {err}")
                return "An error occurred. Please try again."
            finally:
                connection.close()

    return render_template('admin_login.html')

# Admin Dashboard Route
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT o.id, o.total_amount, o.address, o.contact, o.payment_method, o.transaction_id, o.created_at, GROUP_CONCAT(oi.product_id, ':', oi.quantity, ':', oi.price SEPARATOR ';') as items FROM orders o JOIN order_items oi ON o.id = oi.order_id GROUP BY o.id")
        orders = cursor.fetchall()

        for order in orders:
            order['items'] = [{'product_id': int(item.split(':')[0]), 'quantity': int(item.split(':')[1]), 'price': float(item.split(':')[2])} for item in order['items'].split(';')]

        connection.close()
    else:
        orders = []

    return render_template('admin_dashboard.html', orders=orders)

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
                    return redirect(url_for('home'))  # Redirect to home after login
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
    app.run(debug=False,host='0.0.0.0')
