import sqlite3
import os
from datetime import datetime, timedelta
import hashlib

DATABASE_PATH = 'pos_database.db'

def init_database():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone_number TEXT,
            pos_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create packages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            duration TEXT NOT NULL,
            pos_type TEXT NOT NULL,
            features TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create subscriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (package_id) REFERENCES packages (id)
        )
    ''')
    
    # Create stores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            pos_type TEXT NOT NULL,
            address TEXT,
            phone_number TEXT,
            is_open BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_sample_packages():
    """Insert sample packages for testing"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if packages already exist
    cursor.execute('SELECT COUNT(*) FROM packages')
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_packages = [
            # Restaurant packages
            ('Basic Restaurant', 'แพ็กเกจพื้นฐานสำหรับร้านตามสั่ง', 990, 'monthly', 'restaurant', 'POS พื้นฐาน,รายงานยอดขาย,จัดการเมนู'),
            ('Pro Restaurant', 'แพ็กเกจมืออาชีพสำหรับร้านตามสั่ง', 1990, 'monthly', 'restaurant', 'POS ครบครัน,รายงานขั้นสูง,จัดการเมนู,จอครัว,AI วิเคราะห์'),
            ('Enterprise Restaurant', 'แพ็กเกจองค์กรสำหรับร้านตามสั่ง', 3990, 'monthly', 'restaurant', 'POS ครบครัน,รายงานขั้นสูง,จัดการเมนู,จอครัว,AI วิเคราะห์,หลายสาขา,การสนับสนุน 24/7'),
            
            # Coffee shop packages
            ('Basic Coffee', 'แพ็กเกจพื้นฐานสำหรับร้านกาแฟ', 890, 'monthly', 'coffee', 'POS พื้นฐาน,รายงานยอดขาย,จัดการเมนูเครื่องดื่ม'),
            ('Pro Coffee', 'แพ็กเกจมืออาชีพสำหรับร้านกาแฟ', 1690, 'monthly', 'coffee', 'POS ครบครัน,รายงานขั้นสูง,จัดการเมนู,จอลูกค้า,ระบบสต็อก'),
            ('Enterprise Coffee', 'แพ็กเกจองค์กรสำหรับร้านกาแฟ', 2990, 'monthly', 'coffee', 'POS ครบครัน,รายงานขั้นสูง,จัดการเมนู,จอลูกค้า,ระบบสต็อก,หลายสาขา,การสนับสนุน 24/7'),
            
            # Grocery packages
            ('Basic Grocery', 'แพ็กเกจพื้นฐานสำหรับร้านขายของชำ', 790, 'monthly', 'grocery', 'POS พื้นฐาน,สแกนบาร์โค้ด,รายงานยอดขาย'),
            ('Pro Grocery', 'แพ็กเกจมืออาชีพสำหรับร้านขายของชำ', 1490, 'monthly', 'grocery', 'POS ครบครัน,สแกนบาร์โค้ด,ระบบสต็อก,รายงานขั้นสูง'),
            ('Enterprise Grocery', 'แพ็กเกจองค์กรสำหรับร้านขายของชำ', 2490, 'monthly', 'grocery', 'POS ครบครัน,สแกนบาร์โค้ด,ระบบสต็อก,รายงานขั้นสูง,หลายสาขา,การสนับสนุน 24/7'),
        ]
        
        cursor.executemany('''
            INSERT INTO packages (name, description, price, duration, pos_type, features)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_packages)
        
        conn.commit()
        print("Sample packages inserted successfully!")
    
    conn.close()

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

def create_user(username, email, password, phone_number, pos_type):
    """Create a new user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, phone_number, pos_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, phone_number, pos_type))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Get the created user
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        return {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'phone_number': user[4],
            'pos_type': user[5],
            'created_at': user[6]
        }
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            raise ValueError('ชื่อผู้ใช้นี้มีอยู่แล้ว')
        elif 'email' in str(e):
            raise ValueError('อีเมลนี้มีอยู่แล้ว')
        else:
            raise ValueError('ข้อมูลซ้ำ')
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticate user login"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
    user = cursor.fetchone()
    
    if user and verify_password(password, user[3]):
        return {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'phone_number': user[4],
            'pos_type': user[5],
            'created_at': user[6]
        }
    
    conn.close()
    return None

def get_packages_by_type(pos_type):
    """Get packages by POS type"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM packages WHERE pos_type = ?', (pos_type,))
    packages = cursor.fetchall()
    
    result = []
    for pkg in packages:
        result.append({
            'id': pkg[0],
            'name': pkg[1],
            'description': pkg[2],
            'price': float(pkg[3]),
            'duration': pkg[4],
            'pos_type': pkg[5],
            'features': pkg[6].split(',') if pkg[6] else []
        })
    
    conn.close()
    return result

def create_subscription(user_id, package_id):
    """Create a new subscription"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get package info
    cursor.execute('SELECT * FROM packages WHERE id = ?', (package_id,))
    package = cursor.fetchone()
    
    if not package:
        conn.close()
        raise ValueError('ไม่พบแพ็กเกจที่เลือก')
    
    # Calculate end date (30 days for monthly)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    cursor.execute('''
        INSERT INTO subscriptions (user_id, package_id, start_date, end_date)
        VALUES (?, ?, ?, ?)
    ''', (user_id, package_id, start_date, end_date))
    
    subscription_id = cursor.lastrowid
    conn.commit()
    
    # Get the created subscription with package info
    cursor.execute('''
        SELECT s.*, p.name, p.description, p.price, p.duration
        FROM subscriptions s
        JOIN packages p ON s.package_id = p.id
        WHERE s.id = ?
    ''', (subscription_id,))
    
    sub = cursor.fetchone()
    conn.close()
    
    return {
        'id': sub[0],
        'user_id': sub[1],
        'package_id': sub[2],
        'start_date': sub[3],
        'end_date': sub[4],
        'status': sub[5],
        'package': {
            'name': sub[7],
            'description': sub[8],
            'price': float(sub[9]),
            'duration': sub[10]
        }
    }

if __name__ == '__main__':
    print("Initializing database...")
    init_database()
    insert_sample_packages()
    print("Database setup complete!")

