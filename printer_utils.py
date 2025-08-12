# Windows Printer Utilities for Wire Label Generator
import os
import tempfile
import subprocess
import sys

# Check if win32 modules are available
try:
    import win32print
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32print = None
    win32api = None
    win32con = None

class WindowsPrinter:
    """Windows-specific printer utilities using win32 API"""
    
    def __init__(self):
        self.win32_available = WIN32_AVAILABLE
        self._printer_cache = {}
        self._last_refresh = 0
        
    def get_printer_list(self):
        """Get list of available printers"""
        if not self.win32_available:
            return []
        
        try:
            printers = []
            # Get all printers
            printer_info = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            for printer in printer_info:
                printers.append(printer[2])  # Printer name is at index 2
            return sorted(printers)
        except Exception as e:
            print(f"Error getting printer list: {e}")
            return []
    
    def get_default_printer(self):
        """Get the default printer name"""
        if not self.win32_available:
            return None
        
        try:
            return win32print.GetDefaultPrinter()
        except Exception as e:
            print(f"Error getting default printer: {e}")
            return None
    
    def refresh_printers(self):
        """Refresh the printer cache"""
        self._printer_cache.clear()
        return self.get_printer_list()
    
    def get_printer_status(self, printer_name):
        """Get printer status"""
        if not self.win32_available or not printer_name:
            return "Unknown"
        
        try:
            # Open printer handle
            printer_handle = win32print.OpenPrinter(printer_name)
            try:
                # Get printer info
                printer_info = win32print.GetPrinter(printer_handle, 2)
                status = printer_info['Status']
                
                # Translate status codes to readable text
                if status == 0:
                    return "Ready"
                elif status & win32print.PRINTER_STATUS_PAUSED:
                    return "Paused"
                elif status & win32print.PRINTER_STATUS_ERROR:
                    return "Error"
                elif status & win32print.PRINTER_STATUS_PENDING_DELETION:
                    return "Pending Deletion"
                elif status & win32print.PRINTER_STATUS_PAPER_JAM:
                    return "Paper Jam"
                elif status & win32print.PRINTER_STATUS_PAPER_OUT:
                    return "Paper Out"
                elif status & win32print.PRINTER_STATUS_MANUAL_FEED:
                    return "Manual Feed"
                elif status & win32print.PRINTER_STATUS_PAPER_PROBLEM:
                    return "Paper Problem"
                elif status & win32print.PRINTER_STATUS_OFFLINE:
                    return "Offline"
                elif status & win32print.PRINTER_STATUS_IO_ACTIVE:
                    return "Busy"
                elif status & win32print.PRINTER_STATUS_BUSY:
                    return "Busy"
                elif status & win32print.PRINTER_STATUS_PRINTING:
                    return "Printing"
                elif status & win32print.PRINTER_STATUS_OUTPUT_BIN_FULL:
                    return "Output Bin Full"
                elif status & win32print.PRINTER_STATUS_NOT_AVAILABLE:
                    return "Not Available"
                elif status & win32print.PRINTER_STATUS_WAITING:
                    return "Waiting"
                elif status & win32print.PRINTER_STATUS_PROCESSING:
                    return "Processing"
                elif status & win32print.PRINTER_STATUS_INITIALIZING:
                    return "Initializing"
                elif status & win32print.PRINTER_STATUS_WARMING_UP:
                    return "Warming Up"
                elif status & win32print.PRINTER_STATUS_TONER_LOW:
                    return "Toner Low"
                elif status & win32print.PRINTER_STATUS_NO_TONER:
                    return "No Toner"
                elif status & win32print.PRINTER_STATUS_PAGE_PUNT:
                    return "Page Punt"
                elif status & win32print.PRINTER_STATUS_USER_INTERVENTION:
                    return "User Intervention Required"
                elif status & win32print.PRINTER_STATUS_OUT_OF_MEMORY:
                    return "Out of Memory"
                elif status & win32print.PRINTER_STATUS_DOOR_OPEN:
                    return "Door Open"
                else:
                    return f"Status Code: {status}"
                    
            finally:
                win32print.ClosePrinter(printer_handle)
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def print_pdf_direct(self, pdf_buffer, printer_name=None):
        """Print PDF directly to printer using system print command"""
        if not printer_name:
            printer_name = self.get_default_printer()
            if not printer_name:
                print("No printer specified and no default printer found")
                return False
        
        try:
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_buffer.read())
                temp_pdf_path = temp_file.name
            
            try:
                # Print using Windows shell command
                print(f"Attempting to print to specific printer: {printer_name}")
                
                # Use SumatraPDF if available, otherwise use default association
                sumatra_path = self._find_sumatra_pdf()
                if sumatra_path:
                    # Use SumatraPDF for better printer control
                    cmd = [sumatra_path, '-print-to', printer_name, '-silent', temp_pdf_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    success = result.returncode == 0
                    if not success:
                        print(f"SumatraPDF error: {result.stderr}")
                else:
                    # Fallback to shell print command
                    cmd = ['powershell', '-Command', f'Start-Process -FilePath "{temp_pdf_path}" -ArgumentList "/t","{printer_name}" -WindowStyle Hidden -Wait']
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    success = result.returncode == 0
                    if not success:
                        print(f"PowerShell print error: {result.stderr}")
                        # Try alternative method
                        cmd = f'print /D:"{printer_name}" "{temp_pdf_path}"'
                        result = os.system(cmd)
                        success = result == 0
                
                if success:
                    print(f"Print job sent using 'printto' to: {printer_name}")
                else:
                    print(f"Failed to send print job to: {printer_name}")
                
                return success
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_pdf_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error printing PDF: {e}")
            return False
    
    def _find_sumatra_pdf(self):
        """Find SumatraPDF executable"""
        possible_paths = [
            r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
            r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

# Create global instance
windows_printer = WindowsPrinter() if WIN32_AVAILABLE else None
