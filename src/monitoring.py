import logging
import time
import os
from datetime import datetime
from functools import wraps
import sqlite3

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for general logs
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'app.log')
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # File handler for error logs
    error_handler = logging.FileHandler(
        os.path.join(log_dir, 'error.log')
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logging.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logging.error(f"{func.__name__} failed after {execution_time:.4f} seconds: {str(e)}")
            raise
    return wrapper

# System monitoring
class SystemMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_system_stats(self):
        """Get current system statistics"""
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'network_io': psutil.net_io_counters()._asdict(),
            }
            return stats
        except Exception as e:
            self.logger.error(f"Error getting system stats: {str(e)}")
            return None
    
    def log_system_stats(self):
        """Log current system statistics"""
        stats = self.get_system_stats()
        if stats:
            self.logger.info(f"System Stats: CPU: {stats['cpu_percent']}%, "
                           f"Memory: {stats['memory_percent']}%, "
                           f"Disk: {stats['disk_percent']}%")
    
    def check_system_health(self):
        """Check system health and alert if necessary"""
        stats = self.get_system_stats()
        if not stats:
            return False
        
        alerts = []
        
        if stats['cpu_percent'] > 80:
            alerts.append(f"High CPU usage: {stats['cpu_percent']}%")
        
        if stats['memory_percent'] > 80:
            alerts.append(f"High memory usage: {stats['memory_percent']}%")
        
        if stats['disk_percent'] > 90:
            alerts.append(f"High disk usage: {stats['disk_percent']}%")
        
        if alerts:
            for alert in alerts:
                self.logger.warning(f"SYSTEM ALERT: {alert}")
            return False
        
        return True

# Database monitoring
class DatabaseMonitor:
    def __init__(self, db_path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def check_database_health(self):
        """Check database health"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if database is accessible
            cursor.execute("SELECT 1")
            
            # Get database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size = page_count * page_size
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'database_size': db_size,
                'table_count': table_count,
                'accessible': True
            }
            
            self.logger.info(f"Database Health: Size: {db_size} bytes, Tables: {table_count}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'accessible': False,
                'error': str(e)
            }

# Application monitoring
class AppMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
    
    def log_request(self, method, endpoint, status_code, response_time):
        """Log API request"""
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
        
        self.logger.info(f"API Request: {method} {endpoint} - {status_code} - {response_time:.4f}s")
    
    def get_app_stats(self):
        """Get application statistics"""
        uptime = datetime.now() - self.start_time
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate_percent': error_rate
        }

# Initialize monitoring
def init_monitoring():
    """Initialize all monitoring systems"""
    logger = setup_logging()
    system_monitor = SystemMonitor()
    db_monitor = DatabaseMonitor('pos_database.db')
    app_monitor = AppMonitor()
    
    logger.info("Monitoring system initialized")
    
    return {
        'logger': logger,
        'system_monitor': system_monitor,
        'db_monitor': db_monitor,
        'app_monitor': app_monitor
    }

if __name__ == "__main__":
    # Test monitoring system
    monitors = init_monitoring()
    
    # Test system monitoring
    monitors['system_monitor'].log_system_stats()
    monitors['system_monitor'].check_system_health()
    
    # Test database monitoring
    monitors['db_monitor'].check_database_health()
    
    # Test app monitoring
    print("App stats:", monitors['app_monitor'].get_app_stats())

