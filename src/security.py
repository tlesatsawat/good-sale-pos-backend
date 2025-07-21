import hashlib
import secrets
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque
import re

class SecurityManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        self.rate_limits = defaultdict(lambda: deque(maxlen=100))
        
        # Security settings
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.rate_limit_requests = 60  # requests per minute
        self.rate_limit_window = timedelta(minutes=1)
    
    def hash_password(self, password, salt=None):
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        
        return salt + password_hash.hex()
    
    def verify_password(self, password, hashed_password):
        """Verify password against hash"""
        try:
            salt = hashed_password[:64]  # First 64 chars are salt
            password_hash = hashed_password[64:]
            
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            
            return new_hash.hex() == password_hash
        except Exception as e:
            self.logger.error(f"Password verification error: {str(e)}")
            return False
    
    def validate_password_strength(self, password):
        """Validate password strength"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def record_failed_attempt(self, ip_address, username=None):
        """Record failed login attempt"""
        now = datetime.now()
        self.failed_attempts[ip_address].append({
            'timestamp': now,
            'username': username
        })
        
        # Clean old attempts
        cutoff = now - self.lockout_duration
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt['timestamp'] > cutoff
        ]
        
        # Check if IP should be blocked
        if len(self.failed_attempts[ip_address]) >= self.max_failed_attempts:
            self.blocked_ips.add(ip_address)
            self.logger.warning(f"IP {ip_address} blocked due to {self.max_failed_attempts} failed attempts")
    
    def is_ip_blocked(self, ip_address):
        """Check if IP is blocked"""
        if ip_address in self.blocked_ips:
            # Check if lockout period has expired
            now = datetime.now()
            cutoff = now - self.lockout_duration
            
            recent_attempts = [
                attempt for attempt in self.failed_attempts[ip_address]
                if attempt['timestamp'] > cutoff
            ]
            
            if len(recent_attempts) < self.max_failed_attempts:
                self.blocked_ips.discard(ip_address)
                return False
            
            return True
        
        return False
    
    def check_rate_limit(self, ip_address):
        """Check if IP is within rate limits"""
        now = datetime.now()
        cutoff = now - self.rate_limit_window
        
        # Clean old requests
        while self.rate_limits[ip_address] and self.rate_limits[ip_address][0] < cutoff:
            self.rate_limits[ip_address].popleft()
        
        # Check current rate
        if len(self.rate_limits[ip_address]) >= self.rate_limit_requests:
            self.logger.warning(f"Rate limit exceeded for IP {ip_address}")
            return False
        
        # Record current request
        self.rate_limits[ip_address].append(now)
        return True
    
    def sanitize_input(self, input_string):
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_string, str):
            return str(input_string)
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        return sanitized[:1000]
    
    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def generate_session_token(self):
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def get_security_headers(self):
        """Get security headers for HTTP responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

class PerformanceMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_times = deque(maxlen=1000)
        self.slow_requests = []
        self.error_counts = defaultdict(int)
        
        # Performance thresholds
        self.slow_request_threshold = 2.0  # seconds
        self.max_slow_requests = 100
    
    def record_request(self, method, endpoint, response_time, status_code):
        """Record request performance"""
        self.request_times.append(response_time)
        
        if response_time > self.slow_request_threshold:
            slow_request = {
                'timestamp': datetime.now(),
                'method': method,
                'endpoint': endpoint,
                'response_time': response_time,
                'status_code': status_code
            }
            
            self.slow_requests.append(slow_request)
            
            # Keep only recent slow requests
            if len(self.slow_requests) > self.max_slow_requests:
                self.slow_requests.pop(0)
            
            self.logger.warning(f"Slow request: {method} {endpoint} - {response_time:.2f}s")
        
        if status_code >= 400:
            self.error_counts[status_code] += 1
    
    def get_performance_stats(self):
        """Get performance statistics"""
        if not self.request_times:
            return {}
        
        times = list(self.request_times)
        times.sort()
        
        stats = {
            'total_requests': len(times),
            'avg_response_time': sum(times) / len(times),
            'min_response_time': min(times),
            'max_response_time': max(times),
            'median_response_time': times[len(times) // 2],
            'p95_response_time': times[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            'slow_requests_count': len(self.slow_requests),
            'error_counts': dict(self.error_counts)
        }
        
        return stats
    
    def get_slow_requests(self, limit=10):
        """Get recent slow requests"""
        return self.slow_requests[-limit:] if self.slow_requests else []

# Decorators for security and monitoring
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This would integrate with your auth system
        # For now, it's a placeholder
        return f(*args, **kwargs)
    return decorated_function

def monitor_performance(performance_monitor):
    """Decorator to monitor endpoint performance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Extract method and endpoint from Flask request if available
                method = getattr(kwargs.get('request', {}), 'method', 'UNKNOWN')
                endpoint = f.__name__
                status_code = 200
                
                performance_monitor.record_request(method, endpoint, response_time, status_code)
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                performance_monitor.record_request('UNKNOWN', f.__name__, response_time, 500)
                raise
        return decorated_function
    return decorator

def init_security_monitoring():
    """Initialize security and performance monitoring"""
    security_manager = SecurityManager()
    performance_monitor = PerformanceMonitor()
    
    logging.getLogger(__name__).info("Security and performance monitoring initialized")
    
    return security_manager, performance_monitor

if __name__ == "__main__":
    # Test security and performance monitoring
    logging.basicConfig(level=logging.INFO)
    
    security_manager, performance_monitor = init_security_monitoring()
    
    # Test password hashing
    password = "TestPassword123!"
    is_strong, errors = security_manager.validate_password_strength(password)
    print(f"Password strength: {is_strong}, Errors: {errors}")
    
    hashed = security_manager.hash_password(password)
    verified = security_manager.verify_password(password, hashed)
    print(f"Password verification: {verified}")
    
    # Test rate limiting
    ip = "192.168.1.1"
    for i in range(5):
        allowed = security_manager.check_rate_limit(ip)
        print(f"Request {i+1} allowed: {allowed}")
    
    # Test performance monitoring
    performance_monitor.record_request("GET", "/api/test", 0.5, 200)
    performance_monitor.record_request("POST", "/api/slow", 3.0, 200)
    
    stats = performance_monitor.get_performance_stats()
    print(f"Performance stats: {stats}")
    
    slow_requests = performance_monitor.get_slow_requests()
    print(f"Slow requests: {len(slow_requests)}")

