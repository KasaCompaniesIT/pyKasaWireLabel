from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session, jsonify
from datetime import datetime
import time
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
UPLOAD_FOLDER = os.path.abspath('uploads')  # Use absolute path for uploads
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
        print(f"DEBUG: Attempting to save {len(profiles)} profiles to {PROFILES_FILE}")
        print(f"DEBUG: Profile names: {list(profiles.keys())}")
        
        with open(PROFILES_FILE, 'w') as f:
            json.dump(profiles, f, indent=2)
        
        print(f"DEBUG: Successfully wrote profiles to file")
        return True
    except IOError as e:
        print(f"DEBUG: IOError saving profiles: {e}")
        return False
    except Exception as e:
        print(f"DEBUG: Unexpected error saving profiles: {e}")
        return False

def is_authenticated():
    """Check if user is authenticated for settings access"""
    return session.get('settings_authenticated', False)

def get_pure_label_settings(profile_name):
    """Get pure label settings from profile without session overrides"""
    profiles = load_profiles_from_file()
    profile = profiles.get(profile_name, {})
    
    # Return pure profile settings without session overrides
    settings_dict = {
        'width_inches': profile.get('width_inches', 0.875),
        'font_name': profile.get('font_name', 'Arial'),
        'font_size': profile.get('font_size', 11),
        'font_bold': profile.get('font_bold', True),
        'auto_size_font': profile.get('auto_size_font', False),
        'lines_per_label': profile.get('lines_per_label', 3),
        'labels_per_row': profile.get('labels_per_row', 4),
        'page_margin_top_inches': profile.get('page_margin_top_inches', 0.0),
        'page_margin_left_inches': profile.get('page_margin_left_inches', 0.0),
        'label_printable_height_inches': profile.get('label_printable_height_inches', 0.4),
        'label_spacing_horizontal_inches': profile.get('label_spacing_horizontal_inches', 1.0),
        'label_spacing_vertical_inches': profile.get('label_spacing_vertical_inches', 1.8),
        'show_border': profile.get('show_border', False),
        'selected_printer': 'PTR3',  # Always SATO
    }
    
    return settings_dict

def get_label_settings():
    """Get label settings from the selected profile"""
    # Load profiles and get current selection
    profiles = load_profiles_from_file()
    current_profile_name = session.get('selected_profile', 'Wire Labels')
    profile = profiles.get(current_profile_name, profiles.get('Wire Labels', {}))
    
    print(f"DEBUG: get_label_settings using profile '{current_profile_name}': {profile}")
    
    # Use profile settings with session overrides
    settings_dict = {
        'width_inches': session.get('label_width_inches', profile.get('width_inches', 0.875)),
        'font_name': session.get('label_font_name', profile.get('font_name', 'Arial')),
        'font_size': session.get('label_font_size', profile.get('font_size', 11)),
        'font_bold': session.get('label_font_bold', profile.get('font_bold', True)),
        'auto_size_font': session.get('label_auto_size_font', profile.get('auto_size_font', False)),
        'lines_per_label': session.get('lines_per_label', profile.get('lines_per_label', 3)),
        'labels_per_row': session.get('labels_per_row', profile.get('labels_per_row', 4)),
        'page_margin_top_inches': session.get('page_margin_top_inches', profile.get('page_margin_top_inches', 0.0)),
        'page_margin_left_inches': session.get('page_margin_left_inches', profile.get('page_margin_left_inches', 0.0)),
        'label_printable_height_inches': session.get('label_printable_height_inches', profile.get('label_printable_height_inches', 0.4)),
        'label_spacing_horizontal_inches': session.get('label_spacing_horizontal_inches', profile.get('label_spacing_horizontal_inches', 1.0)),
        'label_spacing_vertical_inches': session.get('label_spacing_vertical_inches', profile.get('label_spacing_vertical_inches', 1.8)),
        'show_border': session.get('show_border', profile.get('show_border', False)),
        'selected_printer': session.get('selected_printer', 'PTR3'),  # Always SATO
    }
    
    # Add mm conversions for template compatibility
    settings_dict.update({
        'width_mm': settings_dict['width_inches'] * 25.4,
        'height_mm': settings_dict['label_printable_height_inches'] * 25.4,
        'margin_top_mm': settings_dict['page_margin_top_inches'] * 25.4,
        'margin_right_mm': 0.0,  # Not used in profile
        'margin_bottom_mm': 0.0,  # Not used in profile
        'margin_left_mm': settings_dict['page_margin_left_inches'] * 25.4
    })
    
    return settings_dict

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
    # Load existing profiles first
    profiles = load_profiles_from_file()
    print(f"DEBUG: Loaded existing profiles: {list(profiles.keys())}")
    
    # Add the new profile
    profiles[name] = profile_data
    print(f"DEBUG: Saving profile '{name}' with data: {profile_data}")
    print(f"DEBUG: All profiles to save: {list(profiles.keys())}")
    
    # Save back to file
    success = save_profiles_to_file(profiles)
    if success:
        print(f"DEBUG: Successfully saved profile '{name}'")
    else:
        print(f"DEBUG: Failed to save profile '{name}'")
    
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

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page with label creation form"""
    if request.method == 'POST':
        return handle_label_generation()
    
    # GET request - show the form
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
        # Fallback for Docker/Linux environments - provide common thermal printer names
        printer_info = {
            'available': False,
            'printers': ['PTR3', 'SATO CL4NX', 'Zebra ZD420', 'Brother QL-700', 'DYMO LabelWriter'],
            'default': 'PTR3',
            'status': 'Docker Mode - PDF Export Only'
        }
    
    return render_template('index.html', 
                         settings=settings, 
                         wire_ids=wire_ids, 
                         printer_info=printer_info,
                         profiles=all_profiles,
                         current_profile=current_profile)

def handle_label_generation():
    """Handle the modern form submission for label generation"""
    print("DEBUG: handle_label_generation called")  # Debug line
    
    try:
        # Get form data
        input_method = request.form.get('input_method', 'manual')
        data_format = request.form.get('data_format', 'simple')
        action = request.form.get('action', 'preview')
        print_method = request.form.get('print_method', 'sequential')
        
        print(f"DEBUG: action={action}, input_method={input_method}")  # Debug line
        
        # Label customization options
        font_size = int(request.form.get('font_size', 8))
        font_style = request.form.get('font_style', 'normal')
        text_color = request.form.get('text_color', 'black')
        alignment = request.form.get('alignment', 'left')
        lines_per_label = int(request.form.get('lines_per_label', 1))  # Default to 1 for PTR3
        thermal_optimized = request.form.get('thermal_optimized', 'auto')
        
        # Print configuration
        copies = int(request.form.get('copies', 1))
        labels_per_row = int(request.form.get('labels_per_row', 1))
        
        # Process input based on method
        wire_id_quantities = []
        
        if input_method == 'manual':
            label_data = request.form.get('label_data', '').strip()
            if not label_data:
                flash('Please enter label data', 'error')
                return redirect(url_for('index'))
            
            wire_id_quantities = parse_label_data(label_data, data_format)
            
        elif input_method == 'csv':
            if 'csv_file' not in request.files:
                flash('Please select a CSV file', 'error')
                return redirect(url_for('index'))
            
            csv_file = request.files['csv_file']
            if csv_file.filename == '':
                flash('Please select a CSV file', 'error')
                return redirect(url_for('index'))
            
            csv_column = request.form.get('csv_column', '0')
            csv_qty_column = request.form.get('csv_qty_column', '')
            csv_desc_column = request.form.get('csv_desc_column', '')
            
            wire_id_quantities = parse_csv_data(csv_file, csv_column, csv_qty_column, csv_desc_column, data_format)
            
        elif input_method == 'batch':
            batch_prefix = request.form.get('batch_prefix', 'WIRE')
            batch_start = int(request.form.get('batch_start', 1))
            batch_count = int(request.form.get('batch_count', 10))
            
            wire_id_quantities = generate_batch_data(batch_prefix, batch_start, batch_count)
        
        if not wire_id_quantities:
            flash('No valid label data found', 'error')
            return redirect(url_for('index'))
        
        # Get current profile settings
        profiles = load_profiles_from_file()
        settings = get_label_settings()
        current_profile_name = settings.get('selected_profile', 'Wire Labels')
        profile = profiles.get(current_profile_name, profiles.get('Wire Labels', {}))
        
        print(f"DEBUG: Using profile '{current_profile_name}' with settings: {profile}")
        
        # Generate labels using profile settings for SATO M-84Pro
        generator = WireLabelGenerator(
            width_inches=profile.get('width_inches', 0.875),
            printable_height_inches=profile.get('label_printable_height_inches', 0.4),
            margin_top_inches=profile.get('page_margin_top_inches', 0.0),
            margin_left_inches=profile.get('page_margin_left_inches', 0.0),
            margin_right_inches=0.0,
            margin_bottom_inches=0.0,
            font_name=profile.get('font_name', 'Arial'),
            font_size=profile.get('font_size', font_size),
            font_bold=profile.get('font_bold', True),
            auto_size_font=profile.get('auto_size_font', False),
            thermal_optimized=True,  # Always enabled for SATO
            show_border=profile.get('show_border', False)
        )
        
        # Generate the PDF using profile settings
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"wire_labels_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        # Use profile settings for spacing and layout
        success = generator.generate_bulk_labels_grouped(
            wire_id_quantities,
            use_full_page=True,
            page_margin_top_inches=profile.get('page_margin_top_inches', 0.0),
            page_margin_left_inches=profile.get('page_margin_left_inches', 0.0),
            labels_per_row=profile.get('labels_per_row', labels_per_row),
            label_spacing_horizontal_inches=profile.get('label_spacing_horizontal_inches', 1.0),
            label_spacing_vertical_inches=profile.get('label_spacing_vertical_inches', 1.8),
            lines_per_label=profile.get('lines_per_label', lines_per_label),
            sato_optimized=True,  # Enable SATO thermal optimization
            output_filename=pdf_path  # Save directly to file
        )
        
        if success:
            # Handle different actions
            if action == 'print' and PRINTER_AVAILABLE:
                # Print directly
                settings = get_label_settings()
                printer_name = settings.get('selected_printer')
                if printer_name:
                    # Always use direct thermal printing for all printers - call the working method directly
                    print(f"Using direct thermal printing for {printer_name}")
                    
                    # Use the working thermal printing method directly with correct settings
                    print_success = True
                    for wire_id, qty in wire_id_quantities:
                        for copy in range(qty):
                            # Use the correct number of lines per label from settings
                            text_lines = [str(wire_id).strip()] * lines_per_label
                            print(f"Printing label {copy+1}/{qty} for '{wire_id}' with {lines_per_label} lines")
                            success = windows_printer.print_thermal_direct(text_lines, printer_name, 1)
                            if not success:
                                print_success = False
                                break
                        if not print_success:
                            break
                    
                    if print_success:
                        flash(f'Labels printed directly to {printer_name} (thermal)', 'success')
                    else:
                        flash('Direct thermal printing failed - PDF generated for download', 'warning')
                else:
                    flash('No printer selected - PDF generated for download', 'warning')
            
            # Always provide download link
            pdf_url = f'/uploads/{pdf_filename}'
            flash(f'Labels generated successfully! {len(wire_id_quantities)} unique wire IDs processed.', 'success')
            
            return render_template('index.html', 
                                 pdf_url=pdf_url,
                                 pdf_filename=pdf_filename,
                                 label_count=sum(qty for _, qty in wire_id_quantities),
                                 generation_stats={
                                     'total_labels': sum(qty for _, qty in wire_id_quantities),
                                     'unique_ids': len(wire_id_quantities),
                                     'method': print_method,
                                     'thermal_optimized': thermal_optimized
                                 })
        else:
            flash('Failed to generate labels', 'error')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'Error generating labels: {str(e)}', 'error')
        return redirect(url_for('index'))

def parse_label_data(label_data, data_format):
    """Parse manual label data based on format"""
    wire_id_quantities = []
    
    for line in label_data.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if data_format == 'simple':
            wire_id_quantities.append((line, 1))
        elif data_format == 'quantity':
            parts = line.split(',', 1)
            wire_id = parts[0].strip()
            quantity = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 1
            wire_id_quantities.append((wire_id, quantity))
        elif data_format == 'detailed':
            parts = line.split(',', 2)
            wire_id = parts[0].strip()
            quantity = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 1
            description = parts[2].strip() if len(parts) > 2 else ''
            # For now, just use wire_id (could extend to include description)
            wire_id_quantities.append((wire_id, quantity))
    
    return wire_id_quantities

def parse_csv_data(csv_file, csv_column, csv_qty_column, csv_desc_column, data_format):
    """Parse CSV file data"""
    import csv
    wire_id_quantities = []
    
    try:
        # Read CSV file
        csv_content = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(csv_content.splitlines())
        
        headers = None
        for row_idx, row in enumerate(csv_reader):
            if row_idx == 0:
                headers = row
                continue
            
            if not row:
                continue
            
            # Get wire ID
            wire_id_col = get_column_index(csv_column, headers)
            if wire_id_col >= len(row):
                continue
            wire_id = row[wire_id_col].strip()
            
            # Get quantity if specified
            quantity = 1
            if csv_qty_column:
                qty_col = get_column_index(csv_qty_column, headers)
                if qty_col < len(row) and row[qty_col].strip().isdigit():
                    quantity = int(row[qty_col].strip())
            
            if wire_id:
                wire_id_quantities.append((wire_id, quantity))
                
    except Exception as e:
        print(f"Error parsing CSV: {e}")
    
    return wire_id_quantities

def get_column_index(column_spec, headers):
    """Get column index from specification (number or header name)"""
    if column_spec.isdigit():
        return int(column_spec)
    else:
        try:
            return headers.index(column_spec)
        except ValueError:
            return 0

def generate_batch_data(prefix, start, count):
    """Generate batch wire ID data"""
    wire_id_quantities = []
    
    for i in range(count):
        wire_id = f"{prefix}-{str(start + i).zfill(3)}"
        wire_id_quantities.append((wire_id, 1))
    
    return wire_id_quantities

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/print_pdf', methods=['POST'])
# def print_pdf():
#     """Print a PDF file to the selected printer"""
#     if not PRINTER_AVAILABLE:
#         return jsonify({'success': False, 'error': 'Printing not available'})
    
#     try:
#         data = request.get_json()
#         pdf_url = data.get('pdf_url', '')
        
#         if not pdf_url:
#             return jsonify({'success': False, 'error': 'No PDF URL provided'})
        
#         # Extract filename from URL
#         filename = pdf_url.split('/')[-1]
#         pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
#         if not os.path.exists(pdf_path):
#             return jsonify({'success': False, 'error': 'PDF file not found'})
        
#         settings = get_label_settings()
#         printer_name = settings.get('selected_printer')
        
#         if not printer_name:
#             return jsonify({'success': False, 'error': 'No printer selected'})
        
#         success = windows_printer.print_pdf(pdf_path, printer_name, 1)
        
#         if success:
#             return jsonify({'success': True, 'message': f'PDF sent to {printer_name}'})
#         else:
#             return jsonify({'success': False, 'error': 'Failed to send PDF to printer'})
            
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)})
    
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

@app.route('/select_printer', methods=['POST'])
def select_printer():
    """Select a printer"""
    try:
        printer_name = request.form.get('printer_name', '')
        if printer_name:
            session['selected_printer'] = printer_name
            flash(f'Printer selected: {printer_name}', 'success')
        else:
            flash('Please select a printer', 'error')
            
    except Exception as e:
        flash(f'Error selecting printer: {str(e)}', 'error')
    
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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings page for label configuration"""
    # Check authentication
    if not is_authenticated():
        return redirect(url_for('settings_login', **request.args))
    
    if request.method == 'POST':
        return handle_settings_update()
    
    # GET request - show settings page
    # Save current wire IDs to session before going to settings
    wire_ids = request.args.get('wire_ids', '')
    if wire_ids:
        session['temp_wire_ids'] = wire_ids
    
    current_settings = get_label_settings()
    
    # Get all available profiles (pure profile data, not session-modified)
    default_profiles = get_default_profiles()
    saved_profiles = get_saved_profiles()
    
    # Combine all profiles for template (these should be the pure profile values)
    all_profiles = {}
    all_profiles.update(default_profiles)
    all_profiles.update(saved_profiles)
    
    current_profile = session.get('current_profile', 'Wire Labels')
    
    # For the settings page, use pure profile data initially to avoid showing session-modified values
    # This ensures the form shows the actual profile values, not accidentally modified ones
    if current_profile in all_profiles:
        current_settings = get_pure_label_settings(current_profile)
    
    # Get printer information
    printer_info = {}
    if PRINTER_AVAILABLE:
        printer_info = {
            'available': True,
            'printers': windows_printer.get_printer_list(),
            'default': windows_printer.get_default_printer()
        }
    else:
        printer_info = {'available': False}
    
    return render_template('settings.html', 
                         settings=current_settings,
                         profiles=all_profiles,
                         current_profile=current_profile,
                         printer_info=printer_info)

def handle_settings_update():
    """Handle settings form submission"""
    try:
        action = request.form.get('action', '')
        
        if action == 'update_printer':
            return handle_printer_update()
        elif action == 'update_label_specs':
            return handle_label_specs_update()
        elif action == 'update_font_settings':
            return handle_font_settings_update()
        elif action == 'update_advanced_settings':
            return handle_advanced_settings_update()
        elif action == 'update_settings':
            return handle_complete_settings_update()
        else:
            flash('Unknown action', 'error')
            return redirect(url_for('settings'))
            
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
        return redirect(url_for('settings'))

def handle_printer_update():
    """Handle printer configuration update"""
    try:
        printer_name = request.form.get('printer_name', '')
        printer_type = request.form.get('printer_type', 'auto')
        
        if printer_name:
            session['selected_printer'] = printer_name
            session['printer_type'] = printer_type
            flash(f'Printer updated to: {printer_name}', 'success')
        else:
            flash('Please select a printer', 'error')
            
    except Exception as e:
        flash(f'Error updating printer: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

def handle_label_specs_update():
    """Handle label specifications update"""
    try:
        session['width_inches'] = float(request.form.get('label_width', 5.91))
        session['label_printable_height_inches'] = float(request.form.get('label_height', 3.94))
        session['label_spacing_horizontal_inches'] = float(request.form.get('horizontal_spacing', 6.10))
        session['label_spacing_vertical_inches'] = float(request.form.get('vertical_spacing', 1.8))
        session['page_margin_top_inches'] = float(request.form.get('margin_top', 0.0))
        session['page_margin_left_inches'] = float(request.form.get('margin_left', 0.0))
        
        flash('Label specifications updated successfully', 'success')
        
    except ValueError as e:
        flash('Invalid numeric value in label specifications', 'error')
    except Exception as e:
        flash(f'Error updating label specifications: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

def handle_font_settings_update():
    """Handle font settings update"""
    try:
        session['label_font_name'] = request.form.get('font_name', 'Arial')
        session['label_font_size'] = int(request.form.get('font_size', 8))
        session['label_font_bold'] = request.form.get('font_bold', 'false') == 'true'
        session['lines_per_label'] = int(request.form.get('lines_per_label', 4))
        
        flash('Font settings updated successfully', 'success')
        
    except ValueError as e:
        flash('Invalid numeric value in font settings', 'error')
    except Exception as e:
        flash(f'Error updating font settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

def handle_advanced_settings_update():
    """Handle advanced settings update"""
    try:
        session['labels_per_row'] = int(request.form.get('labels_per_row', 1))
        session['label_auto_size_font'] = request.form.get('auto_size_font', 'false') == 'true'
        session['show_border'] = request.form.get('show_border', 'false') == 'true'
        session['thermal_optimized'] = request.form.get('thermal_optimization', 'true') == 'true'
        
        flash('Advanced settings updated successfully', 'success')
        
    except ValueError as e:
        flash('Invalid numeric value in advanced settings', 'error')
    except Exception as e:
        flash(f'Error updating advanced settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

def handle_complete_settings_update():
    """Handle complete settings form submission from the unified settings form"""
    try:
        # Update all settings from the form
        session['label_width_inches'] = float(request.form.get('label_width', 6.0))
        session['label_printable_height_inches'] = float(request.form.get('label_height', 4.0))
        session['page_margin_top_inches'] = float(request.form.get('margin_top', 0.5))
        session['page_margin_left_inches'] = float(request.form.get('margin_left', 0.5))
        session['lines_per_label'] = int(request.form.get('lines_per_label', 1))
        session['labels_per_row'] = int(request.form.get('labels_per_row', 1))
        session['label_spacing_horizontal_inches'] = float(request.form.get('horizontal_spacing', 4.0))
        session['label_spacing_vertical_inches'] = float(request.form.get('vertical_spacing', 1.8))
        session['label_font_name'] = request.form.get('font_name', 'Arial')
        session['label_font_size'] = int(request.form.get('font_size', 8))
        session['label_font_bold'] = 'font_bold' in request.form
        
        flash('Settings updated successfully', 'success')
        
    except ValueError as e:
        flash('Invalid numeric value in settings', 'error')
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/load_profile', methods=['POST'])
def load_profile_route():
    """Load a profile and return its settings"""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        profile_name = data.get('profile_name', '')
        
        if not profile_name:
            return jsonify({'success': False, 'error': 'Profile name required'})
        
        # Load profile from saved profiles
        profiles = get_saved_profiles()
        if profile_name not in profiles:
            return jsonify({'success': False, 'error': f'Profile "{profile_name}" not found'})

        # Get pure profile data (not session-modified)
        profile_data = get_pure_label_settings(profile_name)        # Apply profile to session
        session.update({
            'label_width_inches': profile_data.get('width_inches', 6.0),
            'label_printable_height_inches': profile_data.get('label_printable_height_inches', 4.0),
            'page_margin_top_inches': profile_data.get('page_margin_top_inches', 0.5),
            'page_margin_left_inches': profile_data.get('page_margin_left_inches', 0.5),
            'label_spacing_horizontal_inches': profile_data.get('label_spacing_horizontal_inches', 4.0),
            'label_spacing_vertical_inches': profile_data.get('label_spacing_vertical_inches', 1.8),
            'label_font_name': profile_data.get('font_name', 'Arial'),
            'label_font_size': profile_data.get('font_size', 8),
            'label_font_bold': profile_data.get('font_bold', False),
            'label_auto_size_font': profile_data.get('auto_size_font', False),
            'lines_per_label': profile_data.get('lines_per_label', 3),
            'labels_per_row': profile_data.get('labels_per_row', 4),
            'show_border': profile_data.get('show_border', False),
            'current_profile': profile_name,
            'selected_profile': profile_name
        })
        
        return jsonify({'success': True, 'settings': profile_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_profile', methods=['POST'])
def save_profile_route():
    """Save current settings as a new profile"""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        profile_name = data.get('profile_name', '')
        settings = data.get('settings', {})
        
        if not profile_name:
            return jsonify({'success': False, 'error': 'Profile name required'})
        
        if not settings:
            return jsonify({'success': False, 'error': 'Settings data required'})
        
        # Save profile using existing function
        success = save_profile(profile_name, settings)
        
        if success:
            # Also update session to use this profile
            session.update({
                'label_width_inches': settings.get('width_inches', 6.0),
                'label_printable_height_inches': settings.get('label_printable_height_inches', 4.0),
                'page_margin_top_inches': settings.get('page_margin_top_inches', 0.5),
                'page_margin_left_inches': settings.get('page_margin_left_inches', 0.5),
                'label_spacing_horizontal_inches': settings.get('label_spacing_horizontal_inches', 4.0),
                'label_spacing_vertical_inches': settings.get('label_spacing_vertical_inches', 1.8),
                'label_font_name': settings.get('font_name', 'Arial'),
                'label_font_size': settings.get('font_size', 8),
                'label_font_bold': settings.get('font_bold', False),
                'current_profile': profile_name
            })
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to save profile to file'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_temp_wire_ids', methods=['POST'])
def save_temp_wire_ids():
    """Save wire IDs temporarily to session"""
    wire_ids = request.form.get('wire_ids', '')
    session['temp_wire_ids'] = wire_ids
    return '', 200  # Return empty success response

@app.route('/print_labels', methods=['POST'])
def print_labels():
    """Print labels directly to selected printer"""
    print("DEBUG: /print_labels route called")  # Debug line
    
    if not PRINTER_AVAILABLE:
        flash('Direct printing not available. Please install pywin32.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Get form data
        wire_ids_text = request.form.get('wire_ids', '').strip()
        print(f"DEBUG: Received wire_ids_text: {wire_ids_text[:100]}...")  # Debug line
        
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
        printer_name = settings['selected_printer']
        
        # Check if printer is selected
        if not printer_name:
            flash('Please select a printer in settings before printing', 'error')
            return redirect(url_for('settings'))
        
        # For SATO thermal printers, use PowerShell Out-Printer (most reliable method)
#         if "sato" in printer_name.lower() or "ptr3" in printer_name.lower():
#             print(f"Using PowerShell Out-Printer for SATO printer: {printer_name}")
            
#             # Get the first wire ID to print
#             wire_id = wire_id_quantities[0][0] if wire_id_quantities else "TEST"
            
#             # Use PowerShell Out-Printer method
#             try:
#                 import subprocess
                
#                 # Create text content for the label
#                 text_content = f"{wire_id}\n{wire_id}\n{wire_id}\n"
                
#                 # PowerShell command to print text directly
#                 ps_command = f'''
#                 $text = @"
# {text_content}
# "@
#                 $text | Out-Printer -Name "{printer_name}"
#                 Write-Host "Label printed successfully"
#                 '''
                
#                 print(f"DEBUG: Executing PowerShell Out-Printer command")
                
#                 # Execute PowerShell command
#                 result = subprocess.run(
#                     ['powershell', '-Command', ps_command],
#                     capture_output=True,
#                     text=True,
#                     timeout=30
#                 )
                
#                 print(f"DEBUG: PowerShell return code: {result.returncode}")
#                 print(f"DEBUG: PowerShell output: {result.stdout}")
                
#                 if result.returncode == 0:
#                     print(f"✅ PowerShell label printed successfully to {printer_name}")
#                     return {"success": True, "message": f"Label sent to printer {printer_name} via PowerShell"}
#                 else:
#                     print(f"❌ PowerShell printing failed: {result.stderr}")
#                     # Continue to PDF fallback
                
#             except Exception as e:
#                 print(f"❌ PowerShell printing failed: {e}")
#                 # Continue to PDF fallback
        
        # Skip complex PDF generation and use legacy PDF approach for non-thermal printers
        print(f"Using PDF printing method for {printer_name}")
        
        # Create label generator using profile settings
        generator = WireLabelGenerator(
            width_inches=settings['width_inches'],
            printable_height_inches=settings['label_printable_height_inches'],
            margin_top_inches=settings['page_margin_top_inches'],  # Use profile margins
            margin_right_inches=0.0,
            margin_bottom_inches=0.0,
            margin_left_inches=settings['page_margin_left_inches'],  # Use profile margins
            font_name=settings['font_name'],
            font_size=settings['font_size'],  # Use exact profile font size
            font_bold=settings['font_bold'],  # Use profile bold setting
            auto_size_font=settings['auto_size_font'],  # Use profile auto-size setting
            thermal_optimized=True,  # Always enabled for SATO
            show_border=settings['show_border']
        )
        
        # Create temporary PDF file for printing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_pdf_filename = f"temp_print_labels_{timestamp}.pdf"
        temp_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_pdf_filename)
        
        success = generator.generate_bulk_labels_grouped(
            wire_id_quantities,
            use_full_page=True,
            page_margin_top_inches=settings['page_margin_top_inches'],  # Use profile margins
            page_margin_left_inches=settings['page_margin_left_inches'],  # Use profile margins
            labels_per_row=settings['labels_per_row'],
            label_spacing_horizontal_inches=settings['label_spacing_horizontal_inches'],
            label_spacing_vertical_inches=settings['label_spacing_vertical_inches'],
            lines_per_label=settings['lines_per_label'],
            sato_optimized=True,  # Enable advanced SATO optimization
            output_filename=temp_pdf_path  # Save to temporary file
        )
        
        if success:
            # Print the PDF file directly without opening viewer
            print(f"Attempting to print PDF directly to {printer_name}")
            # print_success = windows_printer.print_labels_direct(temp_pdf_path, printer_name, 1)
            print_success = windows_printer.print_pdf(temp_pdf_path, printer_name, 1)
            # pause to allow printing to finish before deleting the temp pdf
            time.sleep(2)

            # Clean up temporary file after printing attempt
            try:
                os.remove(temp_pdf_path)
                print(f"Cleaned up temporary PDF: {temp_pdf_filename}")
            except:
                print(f"Could not clean up temporary file: {temp_pdf_filename}")
                
            if print_success:
                total_labels = sum(quantity for _, quantity in wire_id_quantities)
                unique_ids = len(wire_id_quantities)
                flash(f'Successfully sent {total_labels} labels ({unique_ids} unique Wire IDs) to printer: {printer_name} (PDF)', 'success')
            else:
                flash(f'Failed to print labels to printer: {printer_name}. PDF may have opened instead.', 'error')
        else:
            flash('Failed to generate labels for printing', 'error')
        
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error printing labels: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/refresh_printers', methods=['POST'])
def refresh_printers():
    """Refresh printer list"""
    try:
        if PRINTER_AVAILABLE:
            printers = windows_printer.get_printer_list()
            return jsonify({'success': True, 'printers': printers})
        else:
            # Fallback for Docker/Linux environments
            printers = ['PTR3', 'SATO CL4NX', 'Zebra ZD420', 'Brother QL-700', 'DYMO LabelWriter']
            return jsonify({'success': True, 'printers': printers, 'docker_mode': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_print', methods=['POST'])
def test_print_route():
    """Send a test print to the selected printer"""
    try:
        if not PRINTER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Printing not available'})
        
        data = request.get_json()
        printer = data.get('printer', '')
        
        if not printer:
            settings = get_label_settings()
            printer = settings.get('selected_printer', '')
        
        if not printer:
            return jsonify({'success': False, 'error': 'No printer selected'})
        
        # Create a simple test label
        generator = WireLabelGenerator(
            width_inches=5.91,
            printable_height_inches=3.94,
            margin_top_inches=0.0,
            margin_left_inches=0.0,
            margin_right_inches=0.0,
            margin_bottom_inches=0.0,
            font_name='Arial',
            font_size=8,
            font_bold=True,
            auto_size_font=False,
            thermal_optimized=True,
            show_border=False
        )
        
        # Generate test label
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"test_label_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        
        test_data = [('TEST-001', 1)]
        success = generator.generate_bulk_labels_grouped(
            test_data,
            use_full_page=True,
            page_margin_top_inches=0.0,
            page_margin_left_inches=0.0,
            label_spacing_vertical_inches=1.8,
            label_spacing_horizontal_inches=6.1,
            lines_per_label=4,
            output_filename=pdf_path
        )
        
        if success:
            print_success = windows_printer.print_pdf(pdf_path, printer, 1)
            if print_success:
                return jsonify({'success': True, 'message': f'Test label sent to {printer}'})
            else:
                return jsonify({'success': False, 'error': 'Failed to print test label'})
        else:
            return jsonify({'success': False, 'error': 'Failed to generate test label'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reset_settings', methods=['POST'])
def reset_settings():
    """Reset all settings to defaults"""
    try:
        # Clear all label-related session variables
        keys_to_clear = [k for k in session.keys() if k.startswith('label_') or k in ['width_inches', 'page_margin_top_inches', 'page_margin_left_inches', 'selected_printer', 'current_profile', 'thermal_optimized']]
        for key in keys_to_clear:
            session.pop(key, None)
        
        return jsonify({'success': True, 'message': 'Settings reset to defaults'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/detect_printer_type', methods=['POST'])
def detect_printer_type():
    """Auto-detect printer type"""
    try:
        data = request.get_json()
        printer = data.get('printer', '')
        
        if not printer:
            return jsonify({'success': False, 'error': 'No printer specified'})
        
        # Simple heuristic - check printer name for thermal printer keywords
        printer_upper = printer.upper()
        if any(keyword in printer_upper for keyword in ['SATO', 'THERMAL', 'ZEBRA', 'DATAMAX']):
            printer_type = 'thermal'
        else:
            printer_type = 'office'
        
        return jsonify({'success': True, 'type': printer_type})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/export_settings', methods=['POST'])
def export_settings():
    """Export current settings as JSON"""
    try:
        settings = get_label_settings()
        
        # Create export data
        export_data = {
            'export_date': datetime.now().isoformat(),
            'version': '2.0',
            'settings': settings,
            'profiles': {
                'current_profile': session.get('current_profile', 'Wire Labels'),
                'default_profiles': get_default_profiles(),
                'saved_profiles': get_saved_profiles()
            }
        }
        
        # Create JSON response
        json_data = json.dumps(export_data, indent=2)
        
        # Create response
        response = send_file(
            io.BytesIO(json_data.encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'wire_label_settings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/import_settings', methods=['POST'])
def import_settings():
    """Import settings from JSON file"""
    try:
        if 'settings_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['settings_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Read and parse JSON
        content = file.read().decode('utf-8')
        import_data = json.loads(content)
        
        # Validate structure
        if 'settings' not in import_data:
            return jsonify({'success': False, 'error': 'Invalid settings file format'})
        
        # Import settings
        settings = import_data['settings']
        for key, value in settings.items():
            if key.startswith('label_') or key in ['width_inches', 'page_margin_top_inches', 'page_margin_left_inches', 'selected_printer', 'thermal_optimized']:
                session[key] = value
        
        # Import current profile if available
        if 'profiles' in import_data and 'current_profile' in import_data['profiles']:
            session['current_profile'] = import_data['profiles']['current_profile']
        
        return jsonify({'success': True, 'message': 'Settings imported successfully'})
        
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Invalid JSON file'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/import_legacy', methods=['POST'])
def import_legacy():
    """Import legacy .lbl files with alternating wireID/qty format"""
    try:
        if 'legacy_file' not in request.files:
            flash('No file provided', 'error')
            return redirect(url_for('index'))
        
        file = request.files['legacy_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        # Read file content
        content = file.read().decode('utf-8', errors='ignore')
        lines = content.strip().split('\n')
        
        # Parse legacy format: wireID, qty, wireID, qty, ...
        wire_id_quantities = []
        i = 0
        
        while i < len(lines):
            if i + 1 >= len(lines):
                break  # Need both wireID and qty
            
            wire_id = lines[i].strip().upper()
            qty_line = lines[i + 1].strip()
            
            # Skip empty lines
            if not wire_id or not qty_line:
                i += 2
                continue
            
            # Parse quantity
            try:
                quantity = int(qty_line)
                if quantity < 1:
                    quantity = 1
            except ValueError:
                # If qty line is not a number, treat it as another wire ID
                # and assume qty of 1 for the previous wire ID
                quantity = 1
                i += 1  # Only advance by 1 to reprocess this line as wire ID
            else:
                i += 2  # Advance by 2 for normal wire ID + qty pair
            
            if wire_id:
                wire_id_quantities.append((wire_id, quantity))
        
        if not wire_id_quantities:
            flash('No valid wire IDs found in legacy file', 'error')
            return redirect(url_for('index'))
        
        # Convert to session format and store
        wire_ids_text = '\n'.join([f"{wire_id},{qty}" for wire_id, qty in wire_id_quantities])
        session['temp_wire_ids'] = wire_ids_text
        
        # Count totals
        total_unique = len(wire_id_quantities)
        total_labels = sum(qty for _, qty in wire_id_quantities)
        
        flash(f'Successfully imported {total_unique} wire IDs ({total_labels} total labels) from legacy file', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error importing legacy file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/import_csv', methods=['POST'])
def import_csv():
    """Import CSV files with wire IDs and quantities"""
    try:
        if 'csv_file' not in request.files:
            flash('No file provided', 'error')
            return redirect(url_for('index'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        # Read CSV content
        content = file.read().decode('utf-8', errors='ignore')
        lines = content.strip().split('\n')
        
        wire_id_quantities = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Parse CSV line (expecting: wireID,quantity)
            parts = line.split(',')
            if len(parts) >= 1:
                wire_id = parts[0].strip().upper()
                
                # Get quantity if provided, default to 1
                if len(parts) >= 2:
                    try:
                        quantity = int(parts[1].strip())
                        if quantity < 1:
                            quantity = 1
                    except ValueError:
                        quantity = 1
                else:
                    quantity = 1
                
                if wire_id:
                    wire_id_quantities.append((wire_id, quantity))
        
        if not wire_id_quantities:
            flash('No valid wire IDs found in CSV file', 'error')
            return redirect(url_for('index'))
        
        # Convert to session format and store
        wire_ids_text = '\n'.join([f"{wire_id},{qty}" for wire_id, qty in wire_id_quantities])
        session['temp_wire_ids'] = wire_ids_text
        
        # Count totals
        total_unique = len(wire_id_quantities)
        total_labels = sum(qty for _, qty in wire_id_quantities)
        
        flash(f'Successfully imported {total_unique} wire IDs ({total_labels} total labels) from CSV file', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error importing CSV file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/create_label', methods=['POST'])
def create_label():
    """Export wire IDs to CSV file for download"""
    try:
        # Get wire IDs from form
        wire_ids_text = request.form.get('wire_ids', '').strip()
        
        if not wire_ids_text:
            flash('No wire IDs to export', 'error')
            return redirect(url_for('index'))
        
        # Parse wire IDs
        wire_id_quantities = []
        for line in wire_ids_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if ',' in line:
                parts = line.split(',', 1)
                wire_id = parts[0].strip()
                try:
                    quantity = int(parts[1].strip())
                except (ValueError, IndexError):
                    quantity = 1
            else:
                wire_id = line.strip()
                quantity = 1
            
            if wire_id:
                wire_id_quantities.append((wire_id, quantity))
        
        if not wire_id_quantities:
            flash('No valid wire IDs found', 'error')
            return redirect(url_for('index'))
        
        # Generate CSV content
        csv_lines = ['Wire ID,Quantity']  # Header
        for wire_id, quantity in wire_id_quantities:
            csv_lines.append(f'{wire_id},{quantity}')
        
        csv_content = '\n'.join(csv_lines)
        
        # Create response with CSV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wire_labels_{timestamp}.csv"
        
        response = send_file(
            io.BytesIO(csv_content.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
        # Clear temporary wire IDs from session
        session.pop('temp_wire_ids', None)
        
        return response
        
    except Exception as e:
        flash(f'Error creating CSV export: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout from settings"""
    session.pop('settings_authenticated', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
