# SATO M-84Pro Printer Settings and Configuration
from reportlab.lib.units import mm

# SATO M-84Pro specific settings optimized for S100X150VATY labels
SATO_M84PRO_SETTINGS = {
    'name': 'SATO M-84Pro',
    'model': 'M-84Pro',
    
    # Page dimensions optimized for thermal printing
    'page_width': 216,  # Standard letter width in mm (8.5 inches)
    'page_height': 1000,  # Extended height for continuous thermal roll (increased from 279.4mm)
    
    # Label specifications for S100X150VATY
    'label': {
        'width': 100,  # mm
        'height': 150,  # mm (6 inches)
        'type': 'S100X150VATY',
        'description': '100mm x 150mm Variable length adhesive label'
    },
    
    # Print margins and positioning
    'margins': {
        'top': 0.0,     # mm - start at very top
        'bottom': 0.0,  # mm
        'left': 8.0,    # mm - small left margin for thermal alignment
        'right': 8.0    # mm
    },
    
    # Thermal printer specific settings
    'thermal_settings': {
        'print_speed': 4,          # inches per second (1-8)
        'print_darkness': 10,      # darkness level (1-15)
        'tear_off_position': 0,    # tear-off adjustment
        'label_top_position': 0,   # top of form position
        'ribbon_save': True,       # Enable ribbon saving mode
        'cut_position': 0          # Auto-cut position
    },
    
    # Text and font settings optimized for thermal printing
    'font_settings': {
        'default_font': 'Helvetica',
        'default_size': 8,         # points
        'min_font_size': 6,        # points
        'max_font_size': 72,       # points
        'line_spacing': 1.2,       # multiplier
        'bold_default': False,
        'thermal_optimized': True   # Use thermal-optimized font rendering
    },
    
    # Position and spacing settings
    'positioning': {
        'x_offset': 8.0,           # mm from left edge
        'y_offset': 0.0,           # mm from top edge (start at 0)
        'label_spacing_x': 110,    # mm between labels horizontally
        'label_spacing_y': 45.7,   # mm between labels vertically (1.8 inches)
        'rows_per_page': 20,       # Maximum rows on extended page
        'cols_per_page': 1         # Single column for thermal printer
    },
    
    # Barcode settings
    'barcode_settings': {
        'default_type': 'Code128',
        'height': 15,              # mm
        'show_text': True,
        'font_size': 8,
        'quiet_zone': 2            # mm
    },
    
    # Communication settings
    'communication': {
        'interface': 'USB',
        'baud_rate': 9600,
        'data_bits': 8,
        'stop_bits': 1,
        'parity': 'None',
        'flow_control': 'None'
    }
}

def get_sato_pdf_settings():
    """Get PDF generation settings optimized for SATO M-84Pro"""
    settings = SATO_M84PRO_SETTINGS.copy()
    
    return {
        'pagesize': (settings['page_width'] * mm, settings['page_height'] * mm),
        'margins': {
            'top': settings['margins']['top'] * mm,
            'bottom': settings['margins']['bottom'] * mm,
            'left': settings['margins']['left'] * mm,
            'right': settings['margins']['right'] * mm
        },
        'positioning': {
            'x_offset': settings['positioning']['x_offset'] * mm,
            'y_offset': settings['positioning']['y_offset'] * mm,
            'label_spacing_x': settings['positioning']['label_spacing_x'] * mm,
            'label_spacing_y': settings['positioning']['label_spacing_y'] * mm
        },
        'thermal_optimized': True,
        'extended_page': True,      # Enable extended page height for thermal
        'rows_per_page': settings['positioning']['rows_per_page']
    }

def get_sato_label_dimensions():
    """Get label dimensions for SATO M-84Pro"""
    label = SATO_M84PRO_SETTINGS['label']
    return {
        'width': label['width'] * mm,
        'height': label['height'] * mm,
        'width_mm': label['width'],
        'height_mm': label['height']
    }

def get_sato_positioning():
    """Get positioning settings for SATO M-84Pro"""
    pos = SATO_M84PRO_SETTINGS['positioning']
    return {
        'x_offset': pos['x_offset'] * mm,
        'y_offset': pos['y_offset'] * mm,
        'spacing_x': pos['label_spacing_x'] * mm,
        'spacing_y': pos['label_spacing_y'] * mm,
        'rows_per_page': pos['rows_per_page'],
        'cols_per_page': pos['cols_per_page']
    }

def optimize_for_thermal():
    """Return thermal-specific optimizations"""
    return {
        'use_thermal_fonts': True,
        'high_contrast': True,
        'avoid_fine_lines': True,
        'minimize_solid_fills': True,
        'optimize_barcode_density': True
    }
