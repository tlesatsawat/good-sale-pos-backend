from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    stores = db.relationship('Store', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Package(db.Model):
    __tablename__ = 'packages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(Numeric(10, 2), nullable=False)
    duration = db.Column(db.String(20), nullable=False)  # monthly, yearly
    pos_type = db.Column(db.String(50), nullable=False)  # restaurant, coffee, grocery
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='package', lazy=True)
    features = db.relationship('Feature', secondary='package_features', backref='packages')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'duration': self.duration,
            'pos_type': self.pos_type,
            'features': [feature.to_dict() for feature in self.features]
        }

class Feature(db.Model):
    __tablename__ = 'features'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

# Association table for many-to-many relationship between Package and Feature
package_features = db.Table('package_features',
    db.Column('package_id', db.Integer, db.ForeignKey('packages.id'), primary_key=True),
    db.Column('feature_id', db.Integer, db.ForeignKey('features.id'), primary_key=True)
)

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, expired, cancelled
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'package_id': self.package_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'package': self.package.to_dict() if self.package else None
        }

class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone_number = db.Column(db.String(20))
    promptpay_account = db.Column(db.String(50))
    pos_type = db.Column(db.String(50), nullable=False)  # restaurant, coffee, grocery
    is_open = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='store', lazy=True)
    menu_items = db.relationship('MenuItem', backref='store', lazy=True)
    stock_items = db.relationship('StockItem', backref='store', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'address': self.address,
            'phone_number': self.phone_number,
            'promptpay_account': self.promptpay_account,
            'pos_type': self.pos_type,
            'is_open': self.is_open,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    order_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, qr_code
    status = db.Column(db.String(20), default='new')  # new, preparing, ready, completed
    qr_code_slip_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'order_time': self.order_time.isoformat() if self.order_time else None,
            'total_amount': float(self.total_amount),
            'payment_method': self.payment_method,
            'status': self.status,
            'qr_code_slip_url': self.qr_code_slip_url,
            'notes': self.notes,
            'order_items': [item.to_dict() for item in self.order_items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    item_name = db.Column(db.String(200), nullable=False)
    price = db.Column(Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'item_name': self.item_name,
            'price': float(self.price),
            'quantity': self.quantity,
            'notes': self.notes
        }

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    is_custom_order = db.Column(db.Boolean, default=False)
    
    # Relationships
    toppings = db.relationship('Topping', backref='menu_item', lazy=True)
    sizes = db.relationship('Size', backref='menu_item', lazy=True)
    sweetness_levels = db.relationship('Sweetness', backref='menu_item', lazy=True)
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'category': self.category,
            'image_url': self.image_url,
            'is_custom_order': self.is_custom_order,
            'toppings': [topping.to_dict() for topping in self.toppings],
            'sizes': [size.to_dict() for size in self.sizes],
            'sweetness_levels': [sweetness.to_dict() for sweetness in self.sweetness_levels]
        }

class Topping(db.Model):
    __tablename__ = 'toppings'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(Numeric(10, 2), default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'name': self.name,
            'price': float(self.price)
        }

class Size(db.Model):
    __tablename__ = 'sizes'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(Numeric(10, 2), default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'name': self.name,
            'price': float(self.price)
        }

class Sweetness(db.Model):
    __tablename__ = 'sweetness'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    level = db.Column(db.String(50), nullable=False)
    price = db.Column(Numeric(10, 2), default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'level': self.level,
            'price': float(self.price)
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(50))
    barcode_number = db.Column(db.String(100), unique=True)
    
    # Relationships
    stock_items = db.relationship('StockItem', backref='product', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'barcode_number': self.barcode_number
        }

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=10)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'low_stock_threshold': self.low_stock_threshold,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'product': self.product.to_dict() if self.product else None
        }

