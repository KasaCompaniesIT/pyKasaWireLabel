# Wire Label Generator

A Flask web application for generating and printing wire labels, optimized for thermal printers like the SATO M-84Pro.

## Features

- **Web-based Interface** - Easy-to-use web interface for label creation
- **Thermal Printer Optimization** - Specifically optimized for SATO M-84Pro thermal printer
- **Sequential Label Generation** - Generate labels in sequence with proper quantities
- **Profile Management** - Save and manage different printer and label configurations
- **CSV Import** - Import label data from CSV files
- **Multiple Print Methods** - Sequential bulk printing or individual labels
- **Label Spacing Control** - Precise control over margins and spacing

## Supported Printers

### Primary Support
- **SATO M-84Pro** - Full optimization with S100X150VATY labels (100mm x 150mm)

### Secondary Support  
- **Brother TDP-42H** - Basic support with configuration guides
- **Standard Windows Printers** - Basic PDF printing support

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access Web Interface**
   - Open browser to `http://localhost:5000`
   - Default login: `admin` / `wirelabel`

## Label Generation Methods

### Sequential (Recommended for Thermal Printers)
- Generates labels in sequence based on quantities
- One page per row for thermal printers
- Perfect alignment and spacing
- Example: `[('WIRE-001', 3), ('WIRE-002', 2)]` → 5 labels in order

### Individual Labels
- Each label on separate page
- Good for single label printing
- Standard printer compatibility

## Configuration

### Profile Settings
Access via Settings page (requires login):
- **Printer Selection** - Choose target printer
- **Margins** - Top, bottom, left, right margins
- **Spacing** - Horizontal and vertical label spacing
- **Label Dimensions** - Automatic for supported printers

### SATO M-84Pro Recommended Settings
- **Labels per Row:** 1-3 (depending on label width)
- **Vertical Spacing:** 1.8" (45.7mm)
- **Horizontal Spacing:** 4.25" (108mm)
- **Top Margin:** 0.0" (starts at edge)
- **Label Type:** S100X150VATY (100mm x 150mm)

## File Structure

```
pyKasaWireLabel/
├── app.py                      # Main Flask application
├── label_generator.py          # Core PDF generation
├── printer_utils.py            # Windows printer integration
├── sato_m80pro_settings.py     # SATO printer configuration
├── brother_tdp42h_settings.py  # Brother printer configuration
├── config.py                   # Application configuration
├── label_profiles.json         # Saved printer profiles
├── templates/                  # Web interface templates
│   ├── index.html             # Main interface
│   ├── settings.html          # Settings page
│   └── settings_login.html    # Login page
├── static/                    # CSS and static files
└── uploads/                   # Temporary file uploads
```

## Usage Examples

### Manual Entry
1. Select "Manual Entry" input method
2. Enter wire IDs one per line:
   ```
   WIRE-001
   WIRE-002  
   WIRE-003
   ```
3. Choose "Sequential" print method
4. Click "Generate Labels"

### CSV Import
1. Select "CSV Upload" input method
2. Upload CSV file with wire IDs
3. Specify column index (0-based) or column name
4. Choose print method and generate

### Quantity-based Generation
For labels with quantities, use format:
```
WIRE-001,3
WIRE-002,5
WIRE-003,2
```

## Thermal Printer Optimization

### SATO M-84Pro Features
- **One Page Per Row** - Each row gets its own page for clean cutting
- **Precise Positioning** - Labels start at (0,0) with accurate spacing
- **Extended Page Support** - No limitations on number of rows
- **Thermal-Optimized Fonts** - Clear printing on thermal media

### Print Workflow
1. Generate sequential labels
2. Each row becomes a separate page
3. Print to SATO M-84Pro
4. Cut between pages for clean label strips

## Troubleshooting

### Common Issues
- **Labels cut off:** Check page height settings and use sequential method
- **Spacing issues:** Verify vertical spacing in profile settings
- **Printer not found:** Refresh printer list in settings
- **File corruption:** Restart application if files become empty

### SATO M-84Pro Specific
- Use S100X150VATY labels for best results
- Set print darkness to 10-12 for clear text
- Enable ribbon saving mode for longer ribbon life
- Use sequential print method for multiple labels

## Development

### Dependencies
- Flask - Web framework
- FPDF2 - PDF generation
- Pillow (PIL) - Image processing
- pywin32 - Windows printer integration (Windows only)

### Adding Printer Support
1. Create settings file (e.g., `new_printer_settings.py`)
2. Add configuration in `config.py`
3. Update `label_generator.py` for optimization
4. Test with printer-specific features

## Security

### Settings Access
- Protected by username/password authentication
- Default credentials: `admin` / `wirelabel`
- Change credentials after first login
- Session-based authentication

### File Handling
- Temporary files cleaned automatically
- Upload directory isolated
- PDF files generated in memory when possible

## License

This project is designed for internal use with thermal label printers. Modify and distribute according to your organization's policies.

## Support

For issues specific to:
- **SATO M-84Pro:** Check printer settings and label type
- **Label Generation:** Verify input format and print method
- **Web Interface:** Clear browser cache and restart application
- **File Issues:** Check file permissions and disk space

## Version History

- **v1.0** - Initial release with SATO M-84Pro support
- **v1.1** - Added sequential printing and CSV import
- **v1.2** - Thermal printer optimization with one-page-per-row
- **v1.3** - Profile management and settings interface
