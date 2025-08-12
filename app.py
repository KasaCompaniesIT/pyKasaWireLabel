from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session, jsonify
from datetime import datetime
import os
import io
import json
from label_generator import WireLabelGenerator

# Import printer utilities (will handle import errors gracefully)
try:
    from printer_utils import windows_printer, WIN32_AVAILABLE
    PRINTER_AVAILABLE = WIN32_AVAILABLE and windows_printer.win32_available
except ImportError:
    PRINTER_AVAILABLE = False
    windows_printer = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Simple password for settings access - CHANGE THIS PASSWORD!
SETTINGS_PASSWORD = 'admin123'  # Default password - change this to something secure

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Persistent profile storage configuration
PROFILES_FILE = 'label_profiles.json'

def load_profiles_from_file():
    """Load profiles from JSON file"""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_profiles_to_file(profiles):
    """Save profiles to JSON file"""
    try:
        with open(PROFILES_FILE, 'w') as f:
            json.dump(profiles, f, indent=2)
        return True
    except IOError:
        return False

def is_authenticated():
    """Check if user is authenticated for settings access"""
    return session.get('settings_authenticated', False)

def get_label_settings():
    """Get label settings optimized for SATO M-84Pro printer"""
    # SATO M-84Pro S100X150VATY label defaults (150mm x 100mm)
    default_width = 5.91  # 150mm = 5.91 inches
    default_height = 3.94  # 100mm = 3.94 inches
    default_font_size = 6  # Small font for optimal positioning
    default_spacing_h = 6.1  # 155mm = 6.1 inches spacing
    default_spacing_v = 1.8  # 1.8 inches vertical spacing (updated from 1.5")
    
    return {
        'width_inches': session.get('label_width_inches', default_width),
        'font_name': session.get('label_font_name', 'Arial'),
        'font_size': session.get('label_font_size', default_font_size),
        'font_bold': session.get('label_font_bold', True),
        'auto_size_font': session.get('label_auto_size_font', False),  # Disabled for precise control
        'lines_per_label': session.get('lines_per_label', 4),
        'labels_per_row': session.get('labels_per_row', 4),  # 4 labels per row for sequential printing
        'page_margin_top_inches': session.get('page_margin_top_inches', 0.0),  # Set to 0 as requested
        'page_margin_left_inches': session.get('page_margin_left_inches', 0.0),  # Set to 0 as requested
        'label_printable_height_inches': session.get('label_printable_height_inches', default_height),
        'label_spacing_horizontal_inches': session.get('label_spacing_horizontal_inches', default_spacing_h),
        'label_spacing_vertical_inches': session.get('label_spacing_vertical_inches', default_spacing_v),
        'show_border': session.get('show_border', False),
        'selected_printer': session.get('selected_printer', 'PTR3')  # Always SATO
    }

def get_default_profiles():
    """Get default label profiles"""
    return {
        # Default profiles commented out for now
    }

def get_saved_profiles():
    """Get user-saved label profiles from file"""
    return load_profiles_from_file()

def save_profile(name, profile_data):
    """Save a label profile to file"""
    profiles = load_profiles_from_file()
    profiles[name] = profile_data
    success = save_profiles_to_file(profiles)
    return success

def delete_profile(name):
    """Delete a saved profile from file"""
    profiles = load_profiles_from_file()
    if name in profiles:
        del profiles[name]
        return save_profiles_to_file(profiles)
    return False

def load_profile(profile_name):
    """Load a profile (from defaults or saved)"""
    # Check saved profiles first
    saved_profiles = get_saved_profiles()
    if profile_name in saved_profiles:
        return saved_profiles[profile_name]
    
    # Check default profiles
    default_profiles = get_default_profiles()
    if profile_name in default_profiles:
        return default_profiles[profile_name]
    
    return None

@app.route('/')
def index():
    """Main page with label creation form"""
    settings = get_label_settings()
    # Restore any previously entered wire IDs from session
    wire_ids = session.get('temp_wire_ids', '')
    
    # Get all available profiles
    default_profiles = get_default_profiles()
    saved_profiles = get_saved_profiles()
    all_profiles = {**default_profiles, **saved_profiles}
    
    # Get current profile name
    current_profile = session.get('current_profile', 'Wire Labels')
    
    # Get printer information
    printer_info = {}
    if PRINTER_AVAILABLE:
        printer_info = {
            'available': True,
            'printers': windows_printer.get_printer_list(),
            'default': windows_printer.get_default_printer(),
            'status': windows_printer.get_printer_status(settings.get('selected_printer'))
        }
    else:
        printer_info = {'available': False}
    
    return render_template('index.html', 
                         settings=settings, 
                         wire_ids=wire_ids, 
                         printer_info=printer_info,
                         profiles=all_profiles,
                         current_profile=current_profile)

@app.route('/select_profile', methods=['POST'])
def select_profile():
    """Select a label profile"""
    try:
        profile_name = request.form.get('profile_name', '')
        if profile_name:
            profile_data = load_profile(profile_name)
            if profile_data:
                # Handle backward compatibility - convert mm to inches if needed
                if 'width_mm' in profile_data:
                    # Old mm-based profile, convert to inches
                    session['label_width_inches'] = profile_data['width_mm'] / 25.4
                    session['page_margin_top_inches'] = profile_data.get('page_margin_top_mm', 15.0) / 25.4
                    session['page_margin_left_inches'] = profile_data.get('page_margin_left_mm', 15.0) / 25.4
                    session['label_printable_height_inches'] = profile_data.get('label_text_margin_mm', 1.0) / 25.4  # Convert old margin to printable height
                    session['label_spacing_horizontal_inches'] = profile_data.get('label_spacing_horizontal_mm', 81.2) / 25.4
                    session['label_spacing_vertical_inches'] = profile_data.get('label_spacing_vertical_mm', 15.7) / 25.4
                else:
                    # New inches-based profile
                    session['label_width_inches'] = profile_data['width_inches']
                    session['page_margin_top_inches'] = profile_data.get('page_margin_top_inches', 0.0)
                    session['page_margin_left_inches'] = profile_data.get('page_margin_left_inches', 0.0)
                    session['label_printable_height_inches'] = profile_data.get('label_printable_height_inches', 0.5)
                    session['label_spacing_horizontal_inches'] = profile_data.get('label_spacing_horizontal_inches', 3.2)
                    session['label_spacing_vertical_inches'] = profile_data.get('label_spacing_vertical_inches', 1.8)
                
                # Common settings
                session['label_font_name'] = profile_data['font_name']
                session['label_font_size'] = profile_data.get('font_size', 8)
                session['label_font_bold'] = profile_data.get('font_bold', True)
                session['label_auto_size_font'] = profile_data.get('auto_size_font', True)
                session['lines_per_label'] = profile_data.get('lines_per_label', 4)
                session['labels_per_row'] = profile_data.get('labels_per_row', 4)
                session['show_border'] = profile_data.get('show_border', False)
                
                session['current_profile'] = profile_name
                
                flash(f'Profile "{profile_name}" selected successfully!', 'success')
            else:
                flash('Profile not found', 'error')
        else:
            flash('No profile selected', 'error')
    except Exception as e:
        flash(f'Error selecting profile: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/settings_login', methods=['GET', 'POST'])
def settings_login():
    """Login page for settings access"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == SETTINGS_PASSWORD:
            session['settings_authenticated'] = True
            # Redirect to settings with any original parameters
            return redirect(url_for('settings', **request.args))
        else:
            flash('Incorrect password', 'error')
    
    return render_template('settings_login.html')

@app.route('/settings')
def settings():
    """Settings page for label configuration"""
    # Check authentication
    if not is_authenticated():
        return redirect(url_for('settings_login', **request.args))
    # Save current wire IDs to session before going to settings
    wire_ids = request.args.get('wire_ids', '')
    if wire_ids:
        session['temp_wire_ids'] = wire_ids
    
    current_settings = get_label_settings()
    
    # Get all available profiles
    default_profiles = get_default_profiles()
    saved_profiles = get_saved_profiles()
    
    # Combine all profiles for template
    all_profiles = {}
    all_profiles.update(default_profiles)
    all_profiles.update(saved_profiles)
    
    current_profile = session.get('current_profile', 'Wire Labels')
    
    return render_template('settings.html', 
                         settings=current_settings,
                         profiles=all_profiles,
                         current_profile=current_profile)

@app.route('/save_temp_wire_ids', methods=['POST'])
def save_temp_wire_ids():
    """Save wire IDs temporarily to session"""
    wire_ids = request.form.get('wire_ids', '')
    session['temp_wire_ids'] = wire_ids
    return '', 200  # Return empty success response

@app.route('/print_labels', methods=['POST'])
def print_labels():
    """Print labels directly to selected printer"""
    if not PRINTER_AVAILABLE:
        flash('Direct printing not available. Please install pywin32.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get form data
        wire_ids_text = request.form.get('wire_ids', '').strip()
        
        # Validate required fields
        if not wire_ids_text:
            flash('Please enter at least one Wire ID', 'error')
            return redirect(url_for('index'))
        
        # Parse wire IDs with individual quantities (format: "WIRE-ID,QTY" or just "WIRE-ID")
        wire_id_quantities = []
        for line in wire_ids_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if ',' in line:
                parts = line.split(',', 1)  # Split only on first comma
                wire_id = parts[0].strip()
                try:
                    quantity = int(parts[1].strip())
                    if quantity < 1:
                        quantity = 1
                except (ValueError, IndexError):
                    quantity = 1
            else:
                wire_id = line.strip()
                quantity = 1
            
            if wire_id:
                wire_id_quantities.append((wire_id, quantity))
        
        if not wire_id_quantities:
            flash('Please enter at least one valid Wire ID', 'error')
            return redirect(url_for('index'))
        
        # Get settings
        settings = get_label_settings()
        
        # Check if printer is selected
        if not settings['selected_printer']:
            flash('Please select a printer in settings before printing', 'error')
            return redirect(url_for('settings'))
        
        # Create label generator with thermal transfer printer optimization
        # SATO M-84Pro thermal printer - always use small margins for optimal positioning
        margin_top = 2.0 / 25.4     # 2mm to inches
        margin_bottom = 2.0 / 25.4  # 2mm to inches  
        margin_left = 3.0 / 25.4    # 3mm to inches
        margin_right = 3.0 / 25.4   # 3mm to inches
        
        generator = WireLabelGenerator(
            width_inches=settings['width_inches'],
            printable_height_inches=settings['label_printable_height_inches'],
            margin_top_inches=margin_top,
            margin_right_inches=margin_right,
            margin_bottom_inches=margin_bottom,
            margin_left_inches=margin_left,
            font_name=settings['font_name'],
            font_size=settings['font_size'],
            font_bold=settings['font_bold'],
            auto_size_font=settings['auto_size_font'],
            thermal_optimized=True,  # Always enabled for SATO
            show_border=settings['show_border']
        )
        
        # SATO M-84Pro - use bulk generation for sequential labeling
        print(f"DEBUG: Using vertical spacing: {settings['label_spacing_vertical_inches']} inches")
        pdf_buffer = generator.generate_bulk_labels_grouped(
            wire_id_quantities,
            page_margin_top_inches=settings['page_margin_top_inches'],
            page_margin_left_inches=settings['page_margin_left_inches'],
            labels_per_row=settings['labels_per_row'],
            label_spacing_horizontal_inches=settings['label_spacing_horizontal_inches'],
            label_spacing_vertical_inches=settings['label_spacing_vertical_inches'],
            lines_per_label=settings['lines_per_label'],
            sato_optimized=True
        )
        
        # Print the bulk PDF with all labels
        success = windows_printer.print_pdf_direct(
            pdf_buffer, 
            printer_name=settings['selected_printer']
        )
        
        if success:
            total_labels = sum(quantity for _, quantity in wire_id_quantities)
            unique_ids = len(wire_id_quantities)
            flash(f'Successfully sent {total_labels} sequential labels ({unique_ids} unique Wire IDs) to SATO printer: {settings["selected_printer"]}', 'success')
            print_success = True
        else:
            flash(f'Failed to print labels to SATO printer: {settings["selected_printer"]}', 'error')
            print_success = False
        
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error printing labels: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
