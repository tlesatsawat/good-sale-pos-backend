import logging
import time
import os
from datetime import datetime
from functools import wraps
import sqlite3

# Configure logging
def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', mode='a')
        ]
    )
    
    # Create logger
    logger = logging.getLogger('monitoring')
    return logger

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

# Simple system monitoring without psutil
class SimpleSystemMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
    
    def get_system_stats(self):
        """Get basic system statistics without psutil"""
        try:
            # Get basic disk usage using os.statvfs
            try:
                statvfs = os.statvfs('/')
                disk_total = statvfs.f_frsize * statvfs.f_blocks
                disk_free = statvfs.f_frsize * statvfs.f_available
                disk_used = disk_total - disk_free
                disk_percent = (disk_used / disk_total) * 100 if disk_total > 0 else 0
            except:
                disk_percent = 0
            
            # Get load average (Unix-like systems only)
            try:
                load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            except:
                load_avg = 0
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time() - self.start_time,
                'disk_percent': disk_percent,
                'load_average': load_avg,
                'process_id': os.getpid(),
            }
            return stats
        except Exception as e:
            self.logger.error(f"Error getting system stats: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time() - self.start_time,
                'disk_percent': 0,
                'load_average': 0,
                'process_id': os.getpid(),
                'error': str(e)
            }
    
    def log_system_stats(self):
        """Log current system statistics"""
        stats = self.get_system_stats()
        if stats:
            self.logger.info(f"System Stats: Uptime: {stats['uptime']:.1f}s, "
                           f"Disk: {stats['disk_percent']:.1f}%, "
                           f"Load: {stats['load_average']:.2f}")
    
    def check_system_health(self):
        """Check basic system health"""
        stats = self.get_system_stats()
        health_status = 'healthy'
        issues = []
        
        # Check disk usage
        if stats.get('disk_percent', 0) > 90:
            health_status = 'warning'
            issues.append('High disk usage')
        
        # Check load average
        if stats.get('load_average', 0) > 5:
            health_status = 'warning'
            issues.append('High load average')
        
        return {
            'status': health_status,
            'issues': issues,
            'stats': stats
        }

# Database monitoring
class DatabaseMonitor:
    def __init__(self, db_path='pos_database.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            # Get file size
            if os.path.exists(self.db_path):
                file_size = os.path.getsize(self.db_path)
            else:
                file_size = 0
            
            # Get table count
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                conn.close()
            except:
                table_count = 0
            
            return {
                'file_size': file_size,
                'table_count': table_count,
                'file_exists': os.path.exists(self.db_path)
            }
        except Exception as e:
            self.logger.error(f"Error getting database stats: {str(e)}")
            return {
                'file_size': 0,
                'table_count': 0,
                'file_exists': False,
                'error': str(e)
            }
    
    def log_database_health(self):
        """Log database health status"""
        stats = self.get_database_stats()
        self.logger.info(f"Database Health: Size: {stats['file_size']} bytes, "
                        f"Tables: {stats['table_count']}")

# API monitoring
class APIMonitor:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.logger = logging.getLogger(__name__)
    
    def log_request(self, method, endpoint, status_code, response_time):
        """Log API request"""
        self.request_count += 1
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_count += 1
        
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times.pop(0)
        
        self.logger.info(f"API Request: {method} {endpoint} - {status_code} - {response_time:.4f}s")
    
    def get_api_stats(self):
        """Get API statistics"""
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            max_response_time = max(self.response_times)
        else:
            avg_response_time = 0
            max_response_time = 0
        
        error_rate = (self.error_count / max(self.request_count, 1)) * 100
        
        return {
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': error_rate,
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time
        }

# Initialize monitoring systems
def init_simple_monitoring():
    """Initialize simple monitoring systems"""
    logger = setup_logging()
    
    system_monitor = SimpleSystemMonitor()
    db_monitor = DatabaseMonitor()
    api_monitor = APIMonitor()
    
    logger.info("Simple monitoring system initialized")
    
    return {
        'system': system_monitor,
        'database': db_monitor,
        'api': api_monitor,
        'logger': logger
    }

# Flask request monitoring decorator
def monitor_api_request(api_monitor):
    """Decorator to monitor Flask API requests"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            start_time = time.time()
            
            try:
                response = func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Get status code from response
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                else:
                    status_code = 200
                
                api_monitor.log_request(
                    request.method,
                    request.endpoint or 'unknown',
                    status_code,
                    response_time
                )
                
                return response
                
            except Exception as e:
                response_time = time.time() - start_time
                api_monitor.log_request(
                    request.method,
                    request.endpoint or 'unknown',
                    500,
                    response_time
                )
                raise
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test monitoring system
    monitors = init_simple_monitoring()
    
    system_monitor = monitors['system']
    db_monitor = monitors['database']
    
    # Test system monitoring
    system_monitor.log_system_stats()
    health = system_monitor.check_system_health()
    print(f"System health: {health}")
    
    # Test database monitoring
    db_monitor.log_database_health()
    db_stats = db_monitor.get_database_stats()
    print(f"Database stats: {db_stats}")

