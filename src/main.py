import os
import sys
# DON'T CHANGE: Add the src directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import time
from datetime import datetime

# Import monitoring and security
from monitoring_simple import init_simple_monitoring
from backup import init_backup_system
from security import init_security_monitoring

# Import blueprints
from routes.auth import auth_bp
from routes.packages import packages_bp
from routes.stores import stores_bp
from routes.menu import menu_bp
from routes.orders import orders_bp
from routes.reports import reports_bp
from routes.stock import stock_bp
from routes.stock_management import stock_mgmt_bp
from routes.loyalty import loyalty_bp
from routes.ai_recommendations import ai_bp
from routes.hardware import hardware_bp
try:
    from routes.barcode import barcode_bp
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    print("Warning: Barcode scanner not available - missing dependencies")
from routes.payment import payment_bp
from routes.auto_store import auto_store_bp
from routes.customer_display import customer_display_bp

# Global monitoring instances
monitors = None
security_manager = None
performance_monitor = None

def create_app():
    global monitors, security_manager, performance_monitor
    
    # Set static folder path relative to the project root
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    app = Flask(__name__, static_folder=static_folder)
    
    # Configure secret key for sessions
    app.secret_key = 'your-secret-key-change-in-production'
    
    # Enable CORS for all routes
    CORS(app, supports_credentials=True, origins=['*'])
    
    # Initialize monitoring systems
    monitors = init_simple_monitoring()
    security_manager, performance_monitor = init_security_monitoring()
    
    # Initialize backup system
    backup_manager, scheduled_backup = init_backup_system()
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        headers = security_manager.get_security_headers()
        for header, value in headers.items():
            response.headers[header] = value
        return response
    
    # Add request monitoring
    @app.before_request
    def before_request():
        request.start_time = time.time()
        
        # Check rate limiting
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not security_manager.check_rate_limit(client_ip):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Check if IP is blocked
        if security_manager.is_ip_blocked(client_ip):
            return jsonify({'error': 'IP blocked due to security violations'}), 403
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            
            # Log request
            if 'api' in monitors:
                monitors['api'].log_request(
                    request.method,
                    request.endpoint or request.path,
                    response.status_code,
                    response_time
                )
            
            # Record performance
            if 'performance_monitor' in globals():
                performance_monitor.record_request(
                    request.method,
                    request.endpoint or request.path,
                    response.status_code,
                    response_time
                )
        
        return response
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(packages_bp, url_prefix='/api')
    app.register_blueprint(stores_bp, url_prefix='/api')
    app.register_blueprint(menu_bp, url_prefix='/api')
    app.register_blueprint(orders_bp, url_prefix='/api')
    app.register_blueprint(reports_bp, url_prefix='/api')
    app.register_blueprint(stock_bp, url_prefix='/api')
    app.register_blueprint(stock_mgmt_bp, url_prefix='/api')
    app.register_blueprint(loyalty_bp, url_prefix='/api')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(hardware_bp, url_prefix='/api/hardware')
    if BARCODE_AVAILABLE:
        app.register_blueprint(barcode_bp, url_prefix='/api/barcode')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(auto_store_bp, url_prefix='/api/auto-store')
    app.register_blueprint(customer_display_bp, url_prefix='/api/customer-display')
    
    @app.route('/api')
    def api_index():
        return {'message': 'GOOD SALE POS API Server', 'status': 'running', 'timestamp': datetime.now().isoformat()}
    
    @app.route('/')
    def index():
        """Root endpoint - redirect to frontend"""
        return '''
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GOOD SALE POS</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    margin: 0;
                    padding: 0;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                }
                .container {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    max-width: 600px;
                    margin: 20px;
                }
                h1 {
                    font-size: 3rem;
                    margin-bottom: 20px;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                }
                p {
                    font-size: 1.2rem;
                    margin-bottom: 30px;
                    opacity: 0.9;
                }
                .features {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-top: 30px;
                }
                .feature {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 20px;
                    text-align: left;
                }
                .feature h3 {
                    margin-top: 0;
                    color: #ffd700;
                }
                .api-links {
                    margin-top: 30px;
                    text-align: left;
                }
                .api-links a {
                    color: #ffd700;
                    text-decoration: none;
                    display: block;
                    margin: 5px 0;
                }
                .api-links a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏪 GOOD SALE POS</h1>
                <p>ระบบขายหน้าร้านครบครัน สำหรับร้านอาหาร ร้านกาแฟ และร้านค้าทั่วไป</p>
                
                <div class="features">
                    <div class="feature">
                        <h3>🤖 AI Analysis</h3>
                        <p>วิเคราะห์ยอดขายและแนะนำเมนูขายดี</p>
                    </div>
                    <div class="feature">
                        <h3>💳 QR Payment</h3>
                        <p>รองรับการชำระเงินผ่าน QR Code</p>
                    </div>
                    <div class="feature">
                        <h3>📱 Customer Display</h3>
                        <p>จอแสดงผลลูกค้าพร้อมโฆษณา</p>
                    </div>
                    <div class="feature">
                        <h3>🔧 Hardware Integration</h3>
                        <p>เชื่อมต่ออุปกรณ์ POS เสริม</p>
                    </div>
                </div>
                
                <div class="api-links">
                    <h3>🔗 API Endpoints</h3>
                    <a href="/api/health">Health Check</a>
                    <a href="/api/ai/insights">AI Insights</a>
                    <a href="/api/customer-display/display/1">Customer Display</a>
                    <a href="/api/customer-display/content/1">Display Content</a>
                </div>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Check system health
            system_healthy = monitors['system_monitor'].check_system_health()
            
            # Check database health
            db_stats = monitors['db_monitor'].check_database_health()
            
            # Get app stats
            app_stats = monitors['app_monitor'].get_app_stats()
            
            # Get performance stats
            perf_stats = performance_monitor.get_performance_stats()
            
            health_status = {
                'status': 'healthy' if system_healthy and db_stats.get('accessible', False) else 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'system_healthy': system_healthy,
                'database_accessible': db_stats.get('accessible', False),
                'uptime_seconds': app_stats.get('uptime_seconds', 0),
                'total_requests': app_stats.get('total_requests', 0),
                'error_rate': app_stats.get('error_rate_percent', 0),
                'avg_response_time': perf_stats.get('avg_response_time', 0)
            }
            
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return jsonify(health_status), status_code
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }), 500
    
    @app.route('/api/metrics')
    def metrics():
        """Metrics endpoint for monitoring"""
        try:
            system_stats = monitors['system_monitor'].get_system_stats()
            app_stats = monitors['app_monitor'].get_app_stats()
            perf_stats = performance_monitor.get_performance_stats()
            
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'system': system_stats,
                'application': app_stats,
                'performance': perf_stats
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Serve React app
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    
    # Log startup
    if monitors:
        monitors['logger'].info(f"GOOD SALE POS starting on port {port}")
        monitors['logger'].info("Monitoring, backup, and security systems active")
    
    app.run(host='0.0.0.0', port=port, debug=False)

