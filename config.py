# Configuration file for Wire Label Generator
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Application settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'wire-label-generator-secret-key-2024'
    
    # Flask settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'txt'}
    
    # Label generation settings
    DEFAULT_FONT_SIZE = 8
    MAX_LABELS_PER_JOB = 1000
    DEFAULT_COPIES = 1
    
    # Printer settings
    DEFAULT_PRINTER_TIMEOUT = 30  # seconds
    PRINTER_REFRESH_INTERVAL = 60  # seconds
    
    # Profile settings
    PROFILE_FILE = 'label_profiles.json'
    DEFAULT_PROFILE_NAME = 'Wire Labels'
    
    # Authentication settings
    DEFAULT_USERNAME = 'admin'
    DEFAULT_PASSWORD = 'wirelabel'
    LOGIN_REQUIRED_FOR_SETTINGS = True
    SESSION_TIMEOUT_HOURS = 2
    
    # PDF generation settings
    PDF_TEMP_DIR = 'temp_pdfs'
    PDF_CLEANUP_INTERVAL = 3600  # 1 hour in seconds
    
    # SATO M-84Pro specific settings
    SATO_SETTINGS = {
        'model': 'M-84Pro',
        'default_labels_per_row': 1,
        'max_labels_per_row': 3,
        'thermal_optimized': True,
        'one_page_per_row': True,  # New feature for row-based pages
        'label_dimensions': {
            'width_mm': 100,
            'height_mm': 150,
            'type': 'S100X150VATY'
        },
        'print_settings': {
            'speed': 4,           # inches per second
            'darkness': 10,       # 1-15 scale
            'tear_off': 0,        # tear-off position
        }
    }
    
    # Brother TDP-42H specific settings  
    BROTHER_SETTINGS = {
        'model': 'TDP-42H',
        'default_labels_per_row': 2,
        'max_labels_per_row': 4,
        'thermal_optimized': False,
        'label_dimensions': {
            'width_mm': 62,
            'height_mm': 100,
            'type': 'Standard'
        }
    }
    
    # Default label settings (inches)
    DEFAULT_MARGINS = {
        'top': 0.0,
        'bottom': 0.5,
        'left': 0.5,
        'right': 0.5
    }
    
    DEFAULT_SPACING = {
        'horizontal': 4.25,  # inches between labels horizontally
        'vertical': 1.8,     # inches between label rows
    }
    
    # Font settings
    FONT_SETTINGS = {
        'default_family': 'Helvetica',
        'default_size': 8,
        'min_size': 6,
        'max_size': 72,
        'available_fonts': ['Helvetica', 'Arial', 'Times', 'Courier'],
        'bold_default': False
    }
    
    # Color settings
    COLOR_SETTINGS = {
        'default_text_color': 'black',
        'available_colors': ['black', 'blue', 'red', 'green'],
        'background_color': 'white'
    }
    
    # Alignment settings
    ALIGNMENT_SETTINGS = {
        'default': 'left',
        'available': ['left', 'center', 'right']
    }
    
    # Debug settings
    DEBUG_LABEL_GENERATION = os.environ.get('DEBUG_LABELS', 'False').lower() == 'true'
    VERBOSE_LOGGING = os.environ.get('VERBOSE_LOG', 'False').lower() == 'true'
    
    # Security settings
    REQUIRE_AUTH_FOR_SETTINGS = True
    ALLOW_PROFILE_EXPORT = True
    ALLOW_PROFILE_IMPORT = True
    
    @staticmethod
    def init_app(app):
        """Initialize application with config settings"""
        # Create upload directory if it doesn't exist
        upload_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # Create PDF temp directory if it doesn't exist
        pdf_temp_dir = app.config.get('PDF_TEMP_DIR', 'temp_pdfs')
        if not os.path.exists(pdf_temp_dir):
            os.makedirs(pdf_temp_dir)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    DEBUG_LABEL_GENERATION = True
    VERBOSE_LOGGING = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    DEBUG_LABEL_GENERATION = False
    VERBOSE_LOGGING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'testing-secret-key'
    UPLOAD_FOLDER = 'test_uploads'
    PDF_TEMP_DIR = 'test_temp_pdfs'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# Utility functions
def get_allowed_file_extensions():
    """Get list of allowed file extensions"""
    return Config.ALLOWED_EXTENSIONS

def is_allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_printer_settings(printer_type='sato'):
    """Get printer-specific settings"""
    if printer_type.lower() == 'sato':
        return Config.SATO_SETTINGS
    elif printer_type.lower() == 'brother':
        return Config.BROTHER_SETTINGS
    else:
        return {}

def get_default_profile():
    """Get default profile settings"""
    return {
        'name': Config.DEFAULT_PROFILE_NAME,
        'description': 'Default wire label profile',
        'printer_name': '',
        'margin_top': Config.DEFAULT_MARGINS['top'],
        'margin_bottom': Config.DEFAULT_MARGINS['bottom'],
        'margin_left': Config.DEFAULT_MARGINS['left'],
        'margin_right': Config.DEFAULT_MARGINS['right'],
        'horizontal_spacing': Config.DEFAULT_SPACING['horizontal'],
        'vertical_spacing': Config.DEFAULT_SPACING['vertical'],
        'font_size': Config.FONT_SETTINGS['default_size'],
        'font_family': Config.FONT_SETTINGS['default_family'],
        'text_color': Config.COLOR_SETTINGS['default_text_color'],
        'alignment': Config.ALIGNMENT_SETTINGS['default'],
        'bold_text': Config.FONT_SETTINGS['bold_default']
    }
