from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '123'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(120), nullable=True)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cart_items = db.relationship('CartItem', backref='cart', lazy=True, cascade="all, delete-orphan")

    user = db.relationship('User', backref=db.backref('carts', lazy=True))

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    product = db.relationship('Product', backref=db.backref('cart_items', lazy=True))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    frequency_days = db.Column(db.Integer, nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    house_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    cart = db.relationship('Cart', backref=db.backref('subscriptions', lazy=True))

class CreditCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=False)
    card_number = db.Column(db.String(20), nullable=False)
    card_holder_name = db.Column(db.String(100), nullable=False)
    expiration_date = db.Column(db.String(7), nullable=False) 
    cvv = db.Column(db.String(4), nullable=False)

    subscription = db.relationship('Subscription', backref=db.backref('credit_card', uselist=False))

@app.route('/deactivate_subscription/<int:subscription_id>', methods=['POST'])
def deactivate_subscription(subscription_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    subscription = Subscription.query.get_or_404(subscription_id)
    
    if subscription.user_id != session['user_id']:
        return 'Operação não permitida.', 403

    subscription.is_active = False
    db.session.commit()

    return redirect(url_for('perfil'))

@app.route('/perfil')
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    subscriptions = Subscription.query.filter_by(user_id=user_id).all()

    return render_template('perfil.html', user=user, subscriptions=subscriptions)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            error = 'As senhas não coincidem.'
            return render_template('register.html', error=error)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            error = 'Nome de usuário já cadastrado.'
            return render_template('register.html', error=error)

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            error = 'Email já cadastrado.'
            return render_template('register.html', error=error)

        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone:
            error = 'Telefone já cadastrado.'
            return render_template('register.html', error=error)

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, phone=phone, password_hash=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user is None:
            error = 'Usuário não encontrado.'
        elif not check_password_hash(user.password_hash, password):
            error = 'Senha incorreta.'
        else:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))

        return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/produtos')
def produtos():
    produtos = Product.query.all()
    print(produtos)
    return render_template('produtos.html', produtos=produtos)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = CartItem(cart_id=cart.id, product_id=product_id)
        db.session.add(new_cart_item)
    
    db.session.commit()
    
    return redirect(url_for('produtos'))


@app.route('/carrinho')
def carrinho():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart = Cart.query.filter_by(user_id=user_id).first()
    if cart is None:
        cart_items = []
        total = 0
        cart_id = None
    else:
        cart_items = cart.cart_items
        total = sum(item.product.price * item.quantity for item in cart_items)
        cart_id = cart.id

    return render_template('carrinho.html', cart_items=cart_items, total=total, cart_id=cart_id)


@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    CartItem.query.filter_by(id=item_id).delete()
    db.session.commit()
    
    return redirect(url_for('carrinho'))


@app.route('/confirmar_assinatura/<int:cart_id>', methods=['GET', 'POST'])
def confirmar_assinatura(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cart = Cart.query.get_or_404(cart_id)
    if cart.user_id != user_id:
        return 'Operação não permitida.', 403
    if request.method == 'POST':
        frequency_days = request.form['frequency_days']
        zip_code = request.form['zip_code']
        house_number = request.form['house_number']
        card_number = request.form['card_number']
        card_holder_name = request.form['card_holder_name']
        expiration_date = request.form['expiration_date']
        cvv = request.form['cvv']
        if not luhn_check(card_number):
            error = 'Número do cartão de crédito inválido.'
            cart_items = cart.cart_items
            total = sum(item.product.price * item.quantity for item in cart_items)
            return render_template('confirmar_assinatura.html', cart=cart, cart_items=cart_items, total=total, error=error)
        new_subscription = Subscription(
            user_id=user_id,
            cart_id=cart.id,
            frequency_days=frequency_days,
            zip_code=zip_code,
            house_number=house_number
        )
        db.session.add(new_subscription)
        db.session.commit()
        new_credit_card = CreditCard(
            subscription_id=new_subscription.id,
            card_number=card_number,
            card_holder_name=card_holder_name,
            expiration_date=expiration_date,
            cvv=cvv
        )
        db.session.add(new_credit_card)
        db.session.commit()
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
        return redirect(url_for('home'))

    cart_items = cart.cart_items
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('confirmar_assinatura.html', cart=cart, cart_items=cart_items, total=total)

def luhn_check(card_number):
    card_number = card_number.replace(" ", "") 
    if not card_number.isdigit():
        return False

    num_sum = 0
    num_digits = len(card_number)
    oddeven = num_digits & 1

    for i in range(0, num_digits):
        digit = int(card_number[i])

        if not ((i & 1) ^ oddeven):
            digit = digit * 2
        if digit > 9:
            digit = digit - 9

        num_sum = num_sum + digit

    return (num_sum % 10) == 0

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)