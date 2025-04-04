from flask import Flask, request, session, redirect, url_for, render_template, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

# DynamoDB tables
user_table = dynamodb.Table('UserTable')
wishlist_table = dynamodb.Table('WishlistTable')


@app.route('/')
def home():
    logged_in = 'email' in session
    return render_template('home.html', logged_in=logged_in)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = user_table.get_item(Key={'email': email})
        user = response.get('Item')

        if user and check_password_hash(user['hashed_password'], password):
            user_table.update_item(
                Key={'email': email},
                UpdateExpression='SET login_count = login_count + :val',
                ExpressionAttributeValues={':val': 1}
            )
            session['email'] = email
            session['username'] = user['username']
            return redirect(url_for('user_dashboard'))
        else:
            return 'Invalid credentials! Please try again.'
    return render_template('login.html')


@app.route('/user_dashboard')
def user_dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')


@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    item = request.json
    wishlist_table.put_item(
        Item={
            'email': session['email'],
            'item_id': item['item_id'],
            'item_name': item['item_name'],
            'item_details': item['item_details'],
            'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    return jsonify({'success': True, 'message': 'Item added to wishlist'})


@app.route('/wishlist')
def wishlist():
    if 'email' not in session:
        return redirect(url_for('login'))

    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    wishlist_items = response.get('Items', [])
    return render_template('wishlist.html', wishlist=wishlist_items)


@app.route('/wishlist_data')
def wishlist_data():
    if 'email' not in session:
        return jsonify({'wishlist': []})

    response = wishlist_table.query(
        KeyConditionExpression=Key('email').eq(session['email'])
    )
    wishlist_items = response.get('Items', [])
    return jsonify({'wishlist': wishlist_items})


@app.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    item_id = request.json.get('item_id')
    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID not provided'})

    try:
        wishlist_table.delete_item(
            Key={
                'email': session['email'],
                'item_id': item_id
            }
        )
        return jsonify({'success': True, 'message': 'Item removed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/virtual_exhibition', methods=['POST'])
def virtual_exhibition():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})

    item = request.json
    try:
        wishlist_table.put_item(
            Item={
                'email': session['email'],
                'item_id': item['name'],
                'item_name': item['name'],
                'item_details': f"Metal: {item['metal']}, Weight: {item['weight']}, Price: {item['price']}",
                'added_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'item_image': item['image']
            }
        )
        return jsonify({'success': True, 'message': f"{item['name']} added to wishlist!"})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        score = int(request.form.get('score', 0))
        session['won_quiz'] = score >= 12
        return redirect(url_for('user_dashboard'))
    return render_template('quiz.html')


@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=True)
