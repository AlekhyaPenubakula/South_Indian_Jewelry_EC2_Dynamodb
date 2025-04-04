from flask import Flask, request, session, redirect, url_for, render_template, jsonify
import boto3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# Define DynamoDB tables
user_table = dynamodb.Table('UserTable')
wishlist_table = dynamodb.Table('WishlistTable')


# Home route
@app.route('/')
def home():
    logged_in = 'email' in session
    return render_template('home.html', logged_in=logged_in)

# User registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Store user data in DynamoDB
        user_table.put_item(
            Item={
                'email': email,
                'username': username,
                'hashed_password': hashed_password,
                'login_count': 0
            }
        )
        return redirect(url_for('login'))
    return render_template('register.html')

# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user details from DynamoDB
        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['hashed_password'], password):
            # Update login count
            user_table.update_item(
                Key={'email': email},
                UpdateExpression='SET login_count = login_count + :val',
                ExpressionAttributeValues={':val': 1}
            )
            session['email'] = email
            session['username'] = user['username']  # Store the username
            return redirect(url_for('user_dashboard'))
        else:
            return 'Invalid credentials! Please try again.'
    return render_template('login.html')

# User dashboard route
@app.route('/user_dashboard')
def user_dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    return render_template('user_dashboard.html')

# Add to wishlist route
@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    item_id = request.json['item_id']
    item_name = request.json['item_name']
    item_details = request.json['item_details']

    # Add item to WishlistTable in DynamoDB
    wishlist_table.put_item(
        Item={
            'email': session['email'],
            'item_id': item_id,
            'item_name': item_name,
            'item_details': item_details,
            'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Store the current UTC date
        }
    )
    return jsonify({'success': True, 'message': 'Item added to wishlist'})

# View wishlist route
@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    # Retrieve wishlist items from DynamoDB for the logged-in user
    response = wishlist_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('email').eq(session['email'])
    )
    wishlist_items = response.get('Items', [])  # Ensure all items are passed to the frontend

    return render_template('wishlist.html')

@app.route('/wishlist_data')
def wishlist_data():
    if 'email' not in session:
        return jsonify({'wishlist': []})

    # Fetch wishlist items from DynamoDB
    response = wishlist_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('email').eq(session['email'])
    )
    wishlist_items = response.get('Items', [])

    return jsonify({'wishlist': wishlist_items})

# Route to remove an item from the wishlist
@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    item_id = request.json.get('item_id')

    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID not provided'})

    # Remove the item from WishlistTable in DynamoDB
    try:
        wishlist_table.delete_item(
            Key={
                'email': session['email'],
                'item_id': item_id
            }
        )
        return jsonify({'success': True, 'message': 'Item removed from wishlist'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# Virtual exhibition route
@app.route('/virtual_exhibition', methods=['POST'])
def virtual_exhibition():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in. Please log in to add items to your wishlist.'})

    item_data = request.json
    item_name = item_data.get('name')
    item_metal = item_data.get('metal')
    item_weight = item_data.get('weight')
    item_price = item_data.get('price')
    item_image = item_data.get('image')

    # Basic validation
    if not all([item_name, item_metal, item_weight, item_price, item_image]):
        return jsonify({'success': False, 'message': 'Invalid item data. Please try again.'})

    try:
        wishlist_table.put_item(
            Item={
                'email': session['email'],
                'item_id': item_name,
                'item_name': item_name,
                'item_details': f"Metal: {item_metal}, Weight: {item_weight}, Price: {item_price}",
                'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),  # Store the current UTC date and time
                'item_image': item_image
            }
        )
        return jsonify({'success': True, 'message': f'Item "{item_name}" added to wishlist successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding item to wishlist: {str(e)}'})
    return render_template('virtual_exhibition.html')
# Quiz page and submission
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        score = int(request.form.get('score', 0))
        if score >= 12:
            session['won_quiz'] = True  # Set the status for quiz win
        else:
            session['won_quiz'] = False
        return redirect(url_for('user_dashboard'))
    return render_template('quiz.html')

# User logout route
@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
