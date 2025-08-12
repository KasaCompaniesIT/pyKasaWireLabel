from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io
import tempfile
import os
import platform
from datetime import datetime

# Import SATO-specific settings
from sato_m80pro_settings import SATO_M84PRO_SETTINGS, get_sato_pdf_settings

# System font mappings for additional fonts
SYSTEM_FONTS = {
    'Verdana': 'verdana.ttf',
    'Calibri': 'calibri.ttf', 
    'Tahoma': 'tahoma.ttf'
}

def get_system_font_path(font_name):
    """Get the system font path for a given font name"""
    if font_name not in SYSTEM_FONTS:
        return None
        
    system = platform.system()
    font_file = SYSTEM_FONTS[font_name]
    
    if system == 'Windows':
        font_dirs = ['C:/Windows/Fonts/', 'C:/Windows/System32/Fonts/']
        for font_dir in font_dirs:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                return font_path
    elif system == 'Darwin':  # macOS
        font_dirs = ['/System/Library/Fonts/', '/Library/Fonts/']
        for font_dir in font_dirs:
            font_path = os.path.join(font_dir, font_file)
            if os.path.exists(font_path):
                return font_path
    elif system == 'Linux':
        font_dirs = ['/usr/share/fonts/', '/usr/local/share/fonts/']
        for font_dir in font_dirs:
            for root, dirs, files in os.walk(font_dir):
                if font_file in files:
                    return os.path.join(root, font_file)
    
    return None

def setup_pdf_font(pdf, font_name, style='', size=12):
    """Setup font for PDF, adding system fonts if needed"""
    # Standard FPDF fonts
    standard_fonts = ['Arial', 'Helvetica', 'Times', 'Courier']
    
    if font_name in standard_fonts:
        pdf.set_font(font_name, style, size)
        return True
    
    # Try to add system font
    font_path = get_system_font_path(font_name)
    if font_path:
        try:
            # Add the font to FPDF
            font_key = font_name.lower()
            if style.upper() == 'B':
                # For bold, try to find bold variant or use regular
                bold_file = font_path.replace('.ttf', 'b.ttf')
                if os.path.exists(bold_file):
                    pdf.add_font(font_key, 'B', bold_file, uni=True)
                else:
                    # Use regular font file for bold (FPDF will simulate)
                    pdf.add_font(font_key, 'B', font_path, uni=True)
            
            # Add regular font
            pdf.add_font(font_key, '', font_path, uni=True)
            pdf.set_font(font_key, style, size)
            return True
        except Exception as e:
            print(f"Warning: Could not load font {font_name}: {e}")
            # Fallback to Arial
            pdf.set_font('Arial', style, size)
            return False
    else:
        print(f"Warning: Font {font_name} not found, using Arial")
        pdf.set_font('Arial', style, size)
        return False

class WireLabelGenerator:
    def __init__(self, width_inches=3.0, printable_height_inches=0.5, margin_top_inches=0.04, margin_right_inches=0.04, margin_bottom_inches=0.04, margin_left_inches=0.04, font_name='Arial', font_size=8, font_bold=True, auto_size_font=True, thermal_optimized=True, show_border=False):
        # Configurable wrap-around wire label dimensions
        # Long strip that wraps around wire with repeated text
        self.label_width_inches = width_inches   # Default: 3 inches - length to wrap around wire
        self.label_printable_height_inches = printable_height_inches  # Default: 0.5 inch - usable height for text
        
        # Convert to mm for FPDF (which uses mm internally)
        self.label_width_mm = width_inches * 25.4
        self.label_height_mm = (printable_height_inches + margin_top_inches + margin_bottom_inches) * 25.4
        
        # Border setting
        self.show_border = show_border
        
        # Convert margins to mm for internal use
        margin_top_mm = margin_top_inches * 25.4
        margin_right_mm = margin_right_inches * 25.4
        margin_bottom_mm = margin_bottom_inches * 25.4
        margin_left_mm = margin_left_inches * 25.4
        
        # Use margins directly for SATO
        self.margin_top_mm = margin_top_mm
        self.margin_right_mm = margin_right_mm
        self.margin_bottom_mm = margin_bottom_mm
        self.margin_left_mm = margin_left_mm
            
        self.font_name = font_name
        self.font_size = font_size
        self.font_bold = font_bold
        self.auto_size_font = auto_size_font
        self.thermal_optimized = thermal_optimized
        
        # Page dimensions for full-page mode
        self.page_width_mm = 215.9  # Letter size width
        # For thermal printers, use a very large page height to accommodate many rows
        if thermal_optimized:
            self.page_height_mm = 1000.0  # Large height for continuous thermal label roll
        else:
            self.page_height_mm = 279.4  # Letter size height for regular printers

    def calculate_optimal_font_size(self, pdf, text, available_width_mm, available_height_mm, base_font_size, lines_per_label=1):
        """Calculate the optimal font size to fit text within available space"""
        if not self.auto_size_font:
            return base_font_size
            
        # Set font style
        font_style = 'B' if self.font_bold else ''
        
        # Start with the base font size and work down if needed
        test_size = base_font_size
        min_size = 6  # SATO-optimized minimum size
        max_size = 12 # SATO-optimized maximum size
        
        while test_size >= min_size:
            # Setup font for testing
            setup_pdf_font(pdf, self.font_name, font_style, test_size)
            
            # Check if text fits horizontally
            text_width = pdf.get_string_width(text)
            
            # Check if text fits vertically (approximate line height)
            line_height = test_size * 0.35  # Approximate line height in mm
            total_text_height = line_height * lines_per_label
            
            if text_width <= available_width_mm and total_text_height <= available_height_mm:
                return test_size
                
            test_size -= 1
            
        return max(min_size, test_size)
    
    def generate_label(self, label_data, lines_per_label=3, sato_optimized=True):
        """Generate a SATO M-84Pro optimized wire label with repeated text"""
        
        try:
            # Always use standard PDF generation for SATO M-84Pro (works correctly)
            pdf = FPDF(unit='mm', format=(self.label_width_mm, self.label_height_mm))
            pdf.add_page()
            
            # Set SATO-specific metadata
            pdf.set_creator('Wire Label Generator - SATO M-84Pro Optimized')
            pdf.set_title(f'Wire Label: {label_data["wire_id"]}')
            pdf.set_subject('SATO M-84Pro Wire Label')
            
            # Use standard dimensions for S100X150VATY labels
            actual_width = self.label_width_mm
            actual_height = self.label_height_mm
            
            # Border removed per user request
            # pdf.set_line_width(0.2)
            # pdf.rect(0.5, 0.5, actual_width - 1, actual_height - 1)
            
            # Calculate line height to fit specified number of lines
            available_height = actual_height - (self.margin_top_mm + self.margin_bottom_mm)
            line_height = available_height / lines_per_label
            
            # Calculate available width for text
            available_width = actual_width - (self.margin_left_mm + self.margin_right_mm)
            
            # Use only the Wire ID for repeated text
            text_to_repeat = label_data['wire_id']
            
            # Determine font size - always use exact font size for SATO
            font_size = self.font_size
                
            # Set font with style
            font_style = 'B' if self.font_bold else ''
            setup_pdf_font(pdf, self.font_name, font_style, font_size)
            
            # SATO M-84Pro direct coordinate positioning (optimal top-left positioning)
            print(f"DEBUG: Using SATO positioning for font_size={font_size}")
            start_x = 0.0    # 0mm from left edge (hardware limit)
            start_y = 2.0    # 2mm from top edge (better position)
            line_spacing = 3.5  # 3.5mm between lines (tighter spacing)
            
            for i in range(lines_per_label):
                y_position = start_y + (i * line_spacing)
                pdf.set_xy(start_x, y_position)
                
                # Use direct text positioning for optimal placement
                pdf.text(start_x, y_position + 1.0, text_to_repeat)  # Reduced baseline offset
            
            # Generate PDF bytes with proper encoding
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            
            return pdf_buffer
            
        except Exception as e:
            print(f"Error generating label: {e}")
            # If there's any error, create a simple fallback
            pdf = FPDF(unit='mm', format=(self.label_width_mm, self.label_height_mm))
            pdf.add_page()
            
            # Use the configured font settings for fallback
            font_style = 'B' if self.font_bold else ''
            fallback_size = min(6, self.font_size) if hasattr(self, 'font_size') else 6
            setup_pdf_font(pdf, self.font_name, font_style, fallback_size)
            
            # Simple fallback with just the wire ID centered
            pdf.set_xy(self.margin_left_mm, self.label_height_mm / 2 - 2)
            pdf.cell(self.label_width_mm - (self.margin_left_mm + self.margin_right_mm), 4, 
                    label_data['wire_id'], align='C')
            
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            return pdf_buffer
    
    def generate_bulk_labels_grouped(self, wire_id_quantities, use_full_page=True, page_margin_top_inches=0.59, 
                                   page_margin_left_inches=0.59, labels_per_row=3, label_spacing_horizontal_inches=3.2, 
                                   label_spacing_vertical_inches=0.62, lines_per_label=3, brother_optimized=False, sato_optimized=False):
        """Generate labels sequentially - for thermal printers, each label gets its own page"""
        
        print(f"DEBUG: generate_bulk_labels_grouped called with {len(wire_id_quantities)} wire types")
        
        try:
            # Convert inches to mm for FPDF
            page_margin_top_mm = page_margin_top_inches * 25.4
            page_margin_left_mm = page_margin_left_inches * 25.4
            label_spacing_horizontal_mm = label_spacing_horizontal_inches * 25.4
            label_spacing_vertical_mm = label_spacing_vertical_inches * 25.4
            
            print(f"DEBUG: Vertical spacing = {label_spacing_vertical_inches} inches = {label_spacing_vertical_mm} mm")
            print(f"DEBUG: page_margin_top_mm = {page_margin_top_mm} mm")
            print(f"DEBUG: page_margin_left_mm = {page_margin_left_mm} mm")
            
            # Create sequential list of labels based on quantities
            # For example: [('AAAA', 1), ('BBBB', 3), ('CCCC', 6), ('DDDD', 1)]
            # becomes: ['AAAA', 'BBBB', 'BBBB', 'BBBB', 'CCCC', 'CCCC', 'CCCC', 'CCCC', 'CCCC', 'CCCC', 'DDDD']
            sequential_labels = []
            for wire_id, quantity in wire_id_quantities:
                sequential_labels.extend([wire_id] * quantity)
            
            total_labels = len(sequential_labels)
            print(f"DEBUG: Total labels to generate: {total_labels}")
            
            # For thermal printers (SATO), use one page per row approach
            if sato_optimized:
                print("DEBUG: Using SATO thermal printer optimization - one page per row")
                
                # Create PDF with extended width for multiple labels per row
                page_width_mm = self.label_width_mm * labels_per_row + (labels_per_row - 1) * label_spacing_horizontal_mm
                pdf = FPDF(unit='mm', format=(page_width_mm, self.label_height_mm))
                pdf.set_creator('Wire Label Generator - SATO M80-Pro Row Layout')
                pdf.set_title(f'SATO Wire Labels: {len(wire_id_quantities)} types, {total_labels} total')
                pdf.set_subject('SATO M80-Pro Row-based Wire Labels')
                
                print(f"DEBUG: Page dimensions: {page_width_mm}mm x {self.label_height_mm}mm")
                print(f"DEBUG: Labels per row: {labels_per_row}")
                
                # Generate labels in rows, one page per row
                current_label_index = 0
                row_number = 0
                
                while current_label_index < total_labels:
                    row_number += 1
                    print(f"DEBUG: Starting row {row_number}")
                    
                    # Add new page for each row
                    pdf.add_page()
                    
                    # Fill this row with labels (up to labels_per_row)
                    labels_in_this_row = 0
                    
                    for col in range(labels_per_row):
                        if current_label_index >= total_labels:
                            break  # No more labels to print
                        
                        wire_id = sequential_labels[current_label_index]
                        
                        # Calculate position within the row
                        label_x = col * (self.label_width_mm + label_spacing_horizontal_mm)
                        label_y = 0.0  # Always at top of page since each row is a new page
                        
                        print(f"DEBUG: Row {row_number}, Col {col + 1}: '{wire_id}' at x={label_x:.1f}mm, y={label_y:.1f}mm")
                        
                        # Draw the label
                        self._draw_label_at_position(pdf, wire_id, label_x, label_y, lines_per_label, brother_optimized, sato_optimized)
                        
                        current_label_index += 1
                        labels_in_this_row += 1
                    
                    print(f"DEBUG: Completed row {row_number} with {labels_in_this_row} labels")
                    
                print(f"DEBUG: Generated {row_number} row pages with {total_labels} total labels for SATO thermal printer")
                
            else:
                # Standard printers - use multi-label pages
                print("DEBUG: Using standard printer approach - multiple labels per page")
                
                # Create PDF with printer-specific optimization
                pdf = FPDF(unit='mm', format='letter')
                pdf.set_creator('Wire Label Generator - Sequential Layout')
                pdf.set_title(f'Wire Labels: {len(wire_id_quantities)} types, {total_labels} total')
                
                # Calculate how many labels fit vertically on a page
                available_height = self.page_height_mm - page_margin_top_mm - 20  # 20mm bottom margin
                labels_per_column = int(available_height / label_spacing_vertical_mm)
                max_labels_per_page = labels_per_row * labels_per_column
                
                print(f"DEBUG: Page height: {self.page_height_mm}mm")
                print(f"DEBUG: Available height: {available_height}mm")
                print(f"DEBUG: Vertical spacing: {label_spacing_vertical_mm}mm")
                print(f"DEBUG: Labels per column: {labels_per_column}")
                print(f"DEBUG: Max labels per page: {max_labels_per_page}")
                
                # Use exact spacing as specified by user - no auto-adjustment
                actual_spacing = label_spacing_horizontal_mm
                
                # Add first page
                pdf.add_page()
                
                # Print labels sequentially
                current_label_index = 0
                labels_on_current_page = 0
                
                while current_label_index < total_labels:
                    # Check if we need a new page
                    if labels_on_current_page >= max_labels_per_page:
                        pdf.add_page()
                        labels_on_current_page = 0
                    
                    # Calculate current position
                    current_row = labels_on_current_page // labels_per_row
                    current_col = labels_on_current_page % labels_per_row
                    
                    # Calculate label position
                    label_x = page_margin_left_mm + (current_col * actual_spacing)
                    # First row starts at 0, subsequent rows use the full spacing (which includes margin)
                    if current_row == 0:
                        label_y = 0.0  # First row at top edge
                    else:
                        label_y = current_row * label_spacing_vertical_mm  # Subsequent rows with full spacing
                    
                    wire_id = sequential_labels[current_label_index]
                    print(f"DEBUG: Label '{wire_id}' at row {current_row}, col {current_col}: x={label_x:.1f}mm, y={label_y:.1f}mm")
                    
                    # Draw the label
                    self._draw_label_at_position(pdf, wire_id, label_x, label_y, lines_per_label, brother_optimized, sato_optimized)
                    
                    current_label_index += 1
                    labels_on_current_page += 1
            
            # Generate PDF bytes
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            
            return pdf_buffer
            
        except Exception as e:
            print(f"Error generating sequential bulk labels: {e}")
            # Fallback to regular bulk generation
            wire_ids_expanded = []
            for wire_id, quantity in wire_id_quantities:
                wire_ids_expanded.extend([wire_id] * quantity)
            return self.generate_bulk_labels_full_page(wire_ids_expanded, 1, page_margin_top_mm, 
                                                     page_margin_left_mm, labels_per_row, 
                                                     label_spacing_horizontal_mm, label_spacing_vertical_mm, lines_per_label)

    def generate_bulk_labels(self, wire_ids, print_qty=1, use_full_page=True, page_margin_top_mm=15.0, 
                            page_margin_left_mm=15.0, labels_per_row=3, label_spacing_horizontal_mm=81.2, 
                            label_spacing_vertical_mm=15.7):
        """Generate multiple labels - either on full pages (default) or small pages"""
        if use_full_page:
            return self.generate_bulk_labels_full_page(wire_ids, print_qty, page_margin_top_mm, 
                                                     page_margin_left_mm, labels_per_row, 
                                                     label_spacing_horizontal_mm, label_spacing_vertical_mm)
        else:
            return self.generate_bulk_labels_small_page(wire_ids, print_qty)
    
    def generate_bulk_labels_full_page(self, wire_ids, print_qty=1, page_margin_top_mm=15.0, page_margin_left_mm=15.0, 
                                      labels_per_row=3, label_spacing_horizontal_mm=81.2, label_spacing_vertical_mm=15.7, lines_per_label=3):
        """Generate multiple labels arranged on full-size pages using proper spacing settings"""
        
        try:
            pdf = FPDF(unit='mm', format='letter')
            
            # Set PDF metadata
            pdf.set_creator('Wire Label Generator - Full Page')
            pdf.set_title(f'Wire Labels: {len(wire_ids)} types, {len(wire_ids) * print_qty} total')
            
            labels_printed = 0
            current_page_labels = 0
            
            # Calculate how many labels fit vertically on a page
            available_height = self.page_height_mm - page_margin_top_mm - 20  # 20mm bottom margin
            labels_per_column = int(available_height / label_spacing_vertical_mm)
            max_labels_per_page = labels_per_row * labels_per_column
            
            # Use exact spacing as specified by user - no auto-adjustment
            actual_spacing = label_spacing_horizontal_mm
            
            for wire_id in wire_ids:
                for qty in range(print_qty):
                    # Add new page if needed
                    if current_page_labels == 0:
                        pdf.add_page()
                    
                    # Calculate position on the grid
                    col = current_page_labels % labels_per_row
                    row = current_page_labels // labels_per_row
                    
                    # Calculate actual position in mm using the exact spacing
                    label_x = page_margin_left_mm + (col * actual_spacing)
                    # First row starts at 0, subsequent rows use the full spacing (which includes margin)
                    if row == 0:
                        label_y = 0.0  # First row at top edge
                    else:
                        label_y = row * label_spacing_vertical_mm  # Subsequent rows with full spacing
                    print(f"DEBUG: Label '{wire_id}' at row {row}, col {col}: x={label_x:.1f}mm, y={label_y:.1f}mm")
                    
                    # Draw the label with specified lines per label
                    self._draw_label_at_position(pdf, wire_id, label_x, label_y, lines_per_label)
                    
                    current_page_labels += 1
                    labels_printed += 1
                    
                    # Start new page after max labels
                    if current_page_labels >= max_labels_per_page:
                        current_page_labels = 0
            
            # Generate PDF bytes
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            
            return pdf_buffer
            
        except Exception as e:
            print(f"Error generating full page bulk labels: {e}")
            print(f"DEBUG: Bulk generation failed, falling back to small pages")
            import traceback
            traceback.print_exc()
            return self.generate_bulk_labels_small_page(wire_ids, print_qty)  # Fallback
    
    def generate_bulk_labels_small_page(self, wire_ids, print_qty=1):
        """Generate multiple labels on small pages (original method)"""
        
        try:
            # Create PDF with multiple pages, each at label size
            pdf = FPDF(unit='mm', format=(self.label_width_mm, self.label_height_mm))
            
            # Set PDF metadata
            pdf.set_creator('Wire Label Generator')
            pdf.set_title(f'Wire Labels: {len(wire_ids)} types, {len(wire_ids) * print_qty} total')
            
            for wire_id in wire_ids:
                # Generate the specified quantity of each label
                for qty in range(print_qty):
                    # Add a new page for each label copy
                    pdf.add_page()
                    
                    # Border removed per user request
                    # pdf.set_line_width(0.2)
                    # pdf.rect(0.5, 0.5, self.label_width_mm - 1, self.label_height_mm - 1)
                    
                    # Calculate line height to fit 3 lines
                    available_height = self.label_height_mm - (self.margin_top_mm + self.margin_bottom_mm)
                    line_height = available_height / 3
                    
                    # Calculate available width for text
                    available_width = self.label_width_mm - (self.margin_left_mm + self.margin_right_mm)
                    
                    # Determine font size based on settings
                    if self.auto_size_font:
                        # Calculate optimal font size for the text to fit
                        base_size = self.font_size if hasattr(self, 'font_size') else 8
                        font_size = self.calculate_optimal_font_size(
                            pdf, wire_id, available_width, available_height, base_size, 3
                        )
                    else:
                        # Use specified font size for SATO
                        font_size = self.font_size
                        
                    # Set font with style
                    font_style = 'B' if self.font_bold else ''
                    setup_pdf_font(pdf, self.font_name, font_style, font_size)
                    
                    # Draw the same text on 3 lines with better positioning
                    for i in range(3):
                        y_position = self.margin_top_mm + (i * line_height) + (line_height * 0.2)
                        pdf.set_xy(self.margin_left_mm, y_position)
                        
                        # Calculate available width for text
                        available_width = self.label_width_mm - (self.margin_left_mm + self.margin_right_mm)
                        
                        # Create cell with precise positioning
                        pdf.cell(available_width, line_height * 0.6, wire_id, align='C', border=0)
            
            # Generate PDF bytes with proper encoding
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            
            return pdf_buffer
            
        except Exception as e:
            print(f"Error generating small page bulk labels: {e}")
            # Simple fallback
            pdf = FPDF(unit='mm', format=(self.label_width_mm, self.label_height_mm))
            
            for wire_id in wire_ids:
                for qty in range(print_qty):
                    pdf.add_page()
                    setup_pdf_font(pdf, self.font_name, 'B', 6)
                    pdf.set_xy(self.margin_left_mm, self.label_height_mm / 2 - 2)
                    pdf.cell(self.label_width_mm - (self.margin_left_mm + self.margin_right_mm), 4, 
                            wire_id, align='C')
            
            pdf_output = pdf.output()
            if isinstance(pdf_output, str):
                pdf_output = pdf_output.encode('latin-1')
            
            pdf_buffer = io.BytesIO(pdf_output)
            pdf_buffer.seek(0)
            return pdf_buffer
    
    def _draw_label_at_position(self, pdf, wire_id, x_mm, y_mm, lines_per_label=3, brother_optimized=False, sato_optimized=False):
        """Draw a single label at the specified position on the page"""
        
        # Printer-specific optimization: adjust positioning and dimensions
        if sato_optimized:
            # SATO M-84Pro: portrait orientation with S100X150VATY-specific margins
            actual_width = self.label_width_mm
            actual_height = self.label_height_mm
            # Use S100X150VATY-specific margins - larger labels, larger margins
            top_margin = 5.0      # Larger top margin for 150mm height
            bottom_margin = 5.0   # Larger bottom margin  
            left_margin = 8.0     # Larger left margin for 100mm width
            right_margin = 8.0    # Balanced right margin
        elif brother_optimized:
            # Brother TDP42H: landscape orientation with Brother-specific margins
            actual_width = max(self.label_width_mm, self.label_height_mm)
            actual_height = min(self.label_width_mm, self.label_height_mm)
            # Use Brother-specific margins
            top_margin = max(self.margin_top_mm, 0.5)
            bottom_margin = max(self.margin_bottom_mm, 0.5)
            left_margin = max(self.margin_left_mm, 1.0)
            right_margin = max(self.margin_right_mm, 1.0)
        else:
            # Standard configuration
            actual_width = self.label_width_mm
            actual_height = self.label_height_mm
            top_margin = self.margin_top_mm
            bottom_margin = self.margin_bottom_mm
            left_margin = self.margin_left_mm
            right_margin = self.margin_right_mm
        
        # Draw border if enabled
        if self.show_border:
            pdf.set_line_width(0.2)
            pdf.set_draw_color(0, 0, 0)  # Black border
            pdf.rect(x_mm, y_mm, actual_width, actual_height)
        
        # Calculate line height to fit the specified number of lines
        available_height = actual_height - (top_margin + bottom_margin)
        line_height = available_height / lines_per_label
        
        # Calculate available width for text
        available_width = actual_width - (left_margin + right_margin)
        
        # Determine font size based on settings and printer optimization
        if self.auto_size_font:
            # Calculate optimal font size for the text to fit
            base_size = self.font_size if hasattr(self, 'font_size') else 8
            font_size = self.calculate_optimal_font_size(
                pdf, wire_id, available_width, available_height, base_size, lines_per_label
            )
        else:
            # Use specified font size - always use exact font size for SATO (same as individual labels)
            if sato_optimized:
                # Use exact font size for SATO (same as individual function)
                font_size = self.font_size
            elif brother_optimized:
                # Brother TDP42H font size range (8-14pt)  
                min_size, max_size = 8, 14
                font_size = min(max_size, max(min_size, self.font_size))
            elif self.thermal_optimized:
                # SATO thermal printer optimization
                min_size, max_size = 6, 12  # SATO-optimized range
                font_size = min(max_size, max(min_size, self.font_size))
            else:
                font_size = self.font_size
            
        # Set font with style
        font_style = 'B' if self.font_bold else ''
        setup_pdf_font(pdf, self.font_name, font_style, font_size)
        
        # Draw the same text on the specified number of lines
        if sato_optimized:
            # Use the same SATO-optimized positioning as individual labels
            start_x = x_mm + 0.0    # 0mm offset from label left edge
            start_y = y_mm + 2.0    # 2mm from label top edge (same as individual labels)
            line_spacing = 3.5      # 3.5mm between lines (same as individual labels)
            
            for i in range(lines_per_label):
                y_position = start_y + (i * line_spacing)
                pdf.set_xy(start_x, y_position)  # Set cursor position first
                # Use direct text positioning for consistency with individual labels
                pdf.text(start_x, y_position + 1.0, wire_id)  # Same baseline offset
        else:
            # Original positioning for other printers
            for i in range(lines_per_label):
                y_position = y_mm + top_margin + (i * line_height) + (line_height * 0.2)
                pdf.set_xy(x_mm + left_margin, y_position)
                
                # Create cell with precise positioning
                pdf.cell(available_width, line_height * 0.6, wire_id, align='C', border=0)
    
    def generate_preview(self, label_data, lines_per_label=3):
        """Generate a PNG preview of the simple wrap-around wire label"""
        
        # Create image for preview
        scale = 4
        img_width = int(self.label_width_mm * scale * 3.78)  # Convert mm to pixels roughly
        img_height = int(self.label_height_mm * scale * 3.78)
        
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to use better fonts
            text_font = ImageFont.truetype("arial.ttf", 12 * scale)
        except:
            # Fallback to default font
            text_font = ImageFont.load_default()
        
        # Border removed per user request
        # draw.rectangle([2, 2, img_width - 2, img_height - 2], outline='black', width=2)
        
        # Calculate line positions for specified number of lines
        margin_top = int(self.margin_top_mm * scale * 3.78)
        margin_left = int(self.margin_left_mm * scale * 3.78)
        margin_right = int(self.margin_right_mm * scale * 3.78)
        margin_bottom = int(self.margin_bottom_mm * scale * 3.78)
        available_height = img_height - margin_top - margin_bottom
        line_height = available_height // lines_per_label
        
        # Text to repeat (Wire ID)
        text_to_repeat = label_data['wire_id']
        
        # Draw the same text on specified number of lines
        for i in range(lines_per_label):
            y_position = margin_top + (i * line_height) + (line_height // 4)  # Center text in line
            
            # Calculate text position to center it
            text_bbox = draw.textbbox((0, 0), text_to_repeat, font=text_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (img_width - text_width) // 2
            
            draw.text((text_x, y_position), text_to_repeat, font=text_font, fill='black')
        
        # Add subtle line separators between text lines
        for i in range(1, lines_per_label):
            y_line = margin_top + (i * line_height)
            draw.line([margin_left, y_line, img_width - margin_right, y_line], fill='lightgray', width=1)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
