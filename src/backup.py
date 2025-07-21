import os
import shutil
import sqlite3
import zipfile
import logging
from datetime import datetime, timedelta
import schedule
import time
import threading

class BackupManager:
    def __init__(self, db_path, backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.logger = logging.getLogger(__name__)
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_database_backup(self):
        """Create a backup of the database"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"pos_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {str(e)}")
            return None
    
    def create_full_backup(self):
        """Create a full backup including database and logs"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"full_backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup database
                if os.path.exists(self.db_path):
                    zipf.write(self.db_path, 'database.db')
                
                # Backup logs
                logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                if os.path.exists(logs_dir):
                    for root, dirs, files in os.walk(logs_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(logs_dir))
                            zipf.write(file_path, arcname)
                
                # Backup configuration files
                config_files = ['src/main.py', 'src/monitoring.py', 'src/backup.py']
                for config_file in config_files:
                    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_file)
                    if os.path.exists(config_path):
                        zipf.write(config_path, config_file)
            
            self.logger.info(f"Full backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create full backup: {str(e)}")
            return None
    
    def cleanup_old_backups(self, days_to_keep=7):
        """Remove backups older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            removed_count = 0
            
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        removed_count += 1
                        self.logger.info(f"Removed old backup: {filename}")
            
            self.logger.info(f"Cleanup completed. Removed {removed_count} old backups.")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {str(e)}")
    
    def restore_database(self, backup_path):
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current database before restore
            current_backup = self.create_database_backup()
            if current_backup:
                self.logger.info(f"Current database backed up before restore: {current_backup}")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            self.logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore database: {str(e)}")
            return False
    
    def list_backups(self):
        """List all available backups"""
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    backups.append({
                        'filename': filename,
                        'path': file_path,
                        'size': file_stats.st_size,
                        'created': datetime.fromtimestamp(file_stats.st_ctime),
                        'modified': datetime.fromtimestamp(file_stats.st_mtime)
                    })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {str(e)}")
            return []
    
    def get_backup_stats(self):
        """Get backup statistics"""
        try:
            backups = self.list_backups()
            total_size = sum(backup['size'] for backup in backups)
            
            stats = {
                'total_backups': len(backups),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_backup': backups[-1]['created'] if backups else None,
                'newest_backup': backups[0]['created'] if backups else None
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get backup stats: {str(e)}")
            return {}

class ScheduledBackup:
    def __init__(self, backup_manager):
        self.backup_manager = backup_manager
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.thread = None
    
    def setup_schedule(self):
        """Setup backup schedule"""
        # Daily database backup at 2 AM
        schedule.every().day.at("02:00").do(self.backup_manager.create_database_backup)
        
        # Weekly full backup on Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(self.backup_manager.create_full_backup)
        
        # Daily cleanup at 4 AM
        schedule.every().day.at("04:00").do(self.backup_manager.cleanup_old_backups)
        
        self.logger.info("Backup schedule configured")
    
    def run_scheduler(self):
        """Run the backup scheduler"""
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start(self):
        """Start the backup scheduler in a separate thread"""
        if not self.running:
            self.setup_schedule()
            self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.thread.start()
            self.logger.info("Backup scheduler started")
    
    def stop(self):
        """Stop the backup scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Backup scheduler stopped")

def init_backup_system(db_path='pos_database.db'):
    """Initialize backup system"""
    backup_manager = BackupManager(db_path)
    scheduled_backup = ScheduledBackup(backup_manager)
    
    # Create initial backup
    backup_manager.create_database_backup()
    
    # Start scheduled backups
    scheduled_backup.start()
    
    return backup_manager, scheduled_backup

if __name__ == "__main__":
    # Test backup system
    logging.basicConfig(level=logging.INFO)
    
    backup_manager = BackupManager('pos_database.db')
    
    # Create test backups
    print("Creating database backup...")
    db_backup = backup_manager.create_database_backup()
    
    print("Creating full backup...")
    full_backup = backup_manager.create_full_backup()
    
    # List backups
    print("\nAvailable backups:")
    backups = backup_manager.list_backups()
    for backup in backups:
        print(f"- {backup['filename']} ({backup['size']} bytes, {backup['created']})")
    
    # Get stats
    print("\nBackup statistics:")
    stats = backup_manager.get_backup_stats()
    for key, value in stats.items():
        print(f"- {key}: {value}")
    
    # Cleanup old backups (for testing, keep only 1 day)
    print("\nCleaning up old backups...")
    backup_manager.cleanup_old_backups(days_to_keep=1)

