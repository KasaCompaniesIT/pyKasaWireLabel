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
    
    def print_pdf(self, pdf_path, printer_name, copies=1):
        """Print PDF file to specified printer (file path version)"""
        if not self.win32_available:
            print("WIN32 modules not available")
            return False
        
        # Convert to absolute path if relative
        pdf_path = os.path.abspath(pdf_path)
        print(f"DEBUG: Absolute PDF path: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"PDF file not found: {pdf_path}")
            print(f"Current working directory: {os.getcwd()}")
            return False
            
        if not printer_name:
            printer_name = self.get_default_printer()
            if not printer_name:
                print("No printer specified and no default printer found")
                return False
        
        try:
            print(f"Attempting to print {pdf_path} to printer: {printer_name}")
            
            print("Trying win32api ShellExecute method...")
            result = win32api.ShellExecute(
                0,                      # parent window handle
                "printto",             # operation
                pdf_path,              # file to print
                f'"{printer_name}"',   # printer name as parameter
                os.path.dirname(pdf_path),  # working directory
                0                      # SW_HIDE - don't show window
            )
            
            print(f"ShellExecute result code: {result}")
            # ShellExecute returns > 32 for success
            success = result > 32
            
            if success:
                print(f"ShellExecute print successful to: {printer_name}")
                return True
            else:
                print(f"ShellExecute printto failed with code: {result}")
        
            print(f"Print job sent to {printer_name} successfully")
            return True
            
            
            # # Method 1: Try direct Windows print command first (most reliable for thermal printers)
            # print("Trying Windows print command...")
            # cmd = f'powershell -Command "Get-Content \'{pdf_path}\' | Out-Printer -Name \'{printer_name}\'"'
            # result = os.system(cmd)
            # if result == 0:
            #     print(f"Windows print command successful to: {printer_name}")
            #     return True
            # else:
            #     print(f"Windows print command failed with code: {result}")
            
            # # Method 2: Try CMD COPY command for direct printing
            # print("Trying CMD COPY command...")
            # cmd = f'copy /B "{pdf_path}" "{printer_name}"'
            # result = os.system(cmd)
            # if result == 0:
            #     print(f"CMD COPY successful to: {printer_name}")
            #     return True
            # else:
            #     print(f"CMD COPY failed with code: {result}")
            
            # # Method 3: Use SumatraPDF if available for best results
            # sumatra_path = self._find_sumatra_pdf()
            # if sumatra_path:
            #     print(f"Using SumatraPDF for printing to {printer_name}")
            #     cmd = [sumatra_path, '-print-to', printer_name, '-silent', pdf_path]
            #     if copies > 1:
            #         # SumatraPDF doesn't have direct copies parameter, repeat the command
            #         for i in range(copies):
            #             result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            #             if result.returncode != 0:
            #                 print(f"SumatraPDF error on copy {i+1}: {result.stderr}")
            #                 return False
            #         success = True
            #     else:
            #         result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            #         success = result.returncode == 0
            #         if not success:
            #             print(f"SumatraPDF error: {result.stderr}")
                
            #     if success:
            #         print(f"SumatraPDF print successful to: {printer_name}")
            #         return True
            
            # # Method 4: Try PowerShell with more specific print parameters
            # print("Using enhanced PowerShell method...")
            # ps_cmd = f'''
            # Add-Type -AssemblyName System.Drawing
            # Add-Type -AssemblyName System.Windows.Forms
            # $pdf = "{pdf_path}"
            # $printer = "{printer_name}"
            
            # # Try to print directly using .NET PrintDocument
            # try {{
            #     $printDoc = New-Object System.Drawing.Printing.PrintDocument
            #     $printDoc.PrinterSettings.PrinterName = $printer
            #     $printDoc.DocumentName = "Wire Labels"
                
            #     # Set to not show print dialog
            #     $printDoc.PrinterSettings.PrintToFile = $false
                
            #     # Use the default PDF print verb
            #     Start-Process -FilePath $pdf -ArgumentList "/t", $printer -WindowStyle Hidden -Wait
                
            #     Write-Output "Print job sent successfully"
            # }} catch {{
            #     Write-Error "Failed to print: $_"
            #     exit 1
            # }}
            # '''
            # cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_cmd]
            # result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            # success = result.returncode == 0
            
            # if success:
            #     print(f"Enhanced PowerShell method successful to: {printer_name}")
            #     return True
            # else:
            #     print(f"Enhanced PowerShell method failed: {result.stderr}")
                
            #     # Method 5: Last resort - try win32api.ShellExecute with printto
            #     print("Trying win32api ShellExecute method...")
            #     try:
            #         result = win32api.ShellExecute(
            #             0,                      # parent window handle
            #             "printto",             # operation
            #             pdf_path,              # file to print
            #             f'"{printer_name}"',   # printer name as parameter
            #             os.path.dirname(pdf_path),  # working directory
            #             0                      # SW_HIDE - don't show window
            #         )
                    
            #         print(f"ShellExecute result code: {result}")
            #         # ShellExecute returns > 32 for success
            #         success = result > 32
                    
            #         if success:
            #             print(f"ShellExecute print successful to: {printer_name}")
            #             return True
            #         else:
            #             print(f"ShellExecute printto failed with code: {result}")
                        
            # except Exception as e:
            #     print(f"win32api method failed: {e}")
            
            # print(f"All print methods failed for: {printer_name}")
            # return False            

        except Exception as e:
            print(f"Error printing PDF: {e}")
            return False
    
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
                print(f"Attempting to print buffer to printer: {printer_name}")
                print(f"Temporary file created: {temp_pdf_path}")
                
                # Use SumatraPDF if available for best results
                sumatra_path = self._find_sumatra_pdf()
                if sumatra_path:
                    print(f"Using SumatraPDF for printing to {printer_name}")
                    cmd = [sumatra_path, '-print-to', printer_name, '-silent', temp_pdf_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    success = result.returncode == 0
                    if not success:
                        print(f"SumatraPDF error: {result.stderr}")
                else:
                    # Direct printing using win32 API without shell commands
                    print(f"Using direct win32print API for {printer_name}")
                    try:
                        # Method 1: Use win32api.ShellExecute with proper parameters
                        result = win32api.ShellExecute(
                            0,                      # parent window handle
                            "printto",             # operation
                            temp_pdf_path,         # file to print
                            f'"{printer_name}"',   # printer name as parameter
                            os.path.dirname(temp_pdf_path),  # working directory
                            0                      # SW_HIDE - don't show window
                        )
                        
                        print(f"ShellExecute result code: {result}")
                        # ShellExecute returns > 32 for success
                        success = result > 32
                        
                        if not success:
                            print(f"ShellExecute printto failed with code: {result}")
                            # Method 2: Try PowerShell with Start-Process
                            print("Trying PowerShell method...")
                            ps_cmd = f'Start-Process -FilePath "{temp_pdf_path}" -ArgumentList @("/t", "{printer_name}") -WindowStyle Hidden -Wait'
                            cmd = ['powershell', '-NoProfile', '-Command', ps_cmd]
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                            success = result.returncode == 0
                            
                            if not success:
                                print(f"PowerShell method failed: {result.stderr}")
                                # Method 3: Last resort - system print command
                                print("Trying system print command...")
                                cmd = f'print /D:"{printer_name}" "{temp_pdf_path}"'
                                result = os.system(cmd)
                                success = result == 0
                            
                    except Exception as e:
                        print(f"win32api method failed: {e}")
                        success = False
                
                if success:
                    print(f"Print job sent to: {printer_name}")
                else:
                    print(f"Failed to send print job to: {printer_name}")
                
                return success
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_pdf_path)
                    print(f"Cleaned up temporary file: {temp_pdf_path}")
                except Exception as e:
                    print(f"Could not clean up temporary file: {e}")
                    
        except Exception as e:
            print(f"Error printing PDF: {e}")
            return False
    
    # def print_thermal_direct(self, text_lines, printer_name, copies=1):
    #     """Print text directly to thermal printer without PDF"""
    #     if not self.win32_available:
    #         print("WIN32 modules not available")
    #         return False
            
    #     if not printer_name:
    #         printer_name = self.get_default_printer()
    #         if not printer_name:
    #             print("No printer specified and no default printer found")
    #             return False
        
    #     try:
    #         print(f"Sending direct thermal print to: {printer_name}")
    #         print(f"Text lines to print: {text_lines}")
            
    #         # Open printer handle
    #         printer_handle = win32print.OpenPrinter(printer_name)
            
    #         try:
    #             # Use TEXT datatype with overprinting for darkness
    #             job_info = ("Wire Label Direct Print", None, "TEXT")
    #             job_id = win32print.StartDocPrinter(printer_handle, 1, job_info)
    #             win32print.StartPagePrinter(printer_handle)
                
    #             # Generate text with overprinting technique for darkness
    #             for copy in range(copies):
    #                 text_to_print = ""
                    
    #                 # Add each line of text with overprinting
    #                 for line in text_lines:
    #                     if line.strip():
    #                         line_text = line.strip()
    #                         # Overprint the same line multiple times with slight variations
    #                         text_to_print += line_text + "\r"  # Carriage return without line feed
    #                         text_to_print += line_text + "\r"  # Print again on same line
    #                         text_to_print += line_text + "\r"  # Print third time
    #                         text_to_print += line_text + "\n"  # Final print with line feed
                    
    #                 # Add form feed
    #                 text_to_print += "\f"
                    
    #                 # Convert to bytes
    #                 text_bytes = text_to_print.encode('utf-8', errors='ignore')
    #                 print(f"Sending overprinted text: {repr(text_to_print[:30])}...")
                    
    #                 # Send the text
    #                 win32print.WritePrinter(printer_handle, text_bytes)
                
    #             win32print.EndPagePrinter(printer_handle)
    #             win32print.EndDocPrinter(printer_handle)
                
    #             print(f"Overprinted text job sent to: {printer_name}")
    #             return True
                
    #         finally:
    #             win32print.ClosePrinter(printer_handle)
                
    #     except Exception as e:
    #         print(f"Error sending direct thermal print: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return False

    # def print_labels_direct(self, wire_ids, printer_name, copies=1):
    #     """Print wire labels directly to thermal printer without PDF"""
    #     if not isinstance(wire_ids, list):
    #         wire_ids = [wire_ids]
        
    #     print(f"Printing {len(wire_ids)} labels directly to thermal printer")
        
    #     for wire_id in wire_ids:
    #         # For thermal printing, we typically print one line per label
    #         text_lines = [str(wire_id).strip()]
    #         success = self.print_thermal_direct(text_lines, printer_name, copies)
    #         if not success:
    #             return False
        
    #     return True

    # def _find_sumatra_pdf(self):
    #     """Find SumatraPDF executable"""
    #     possible_paths = [
    #         r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    #         r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    #     ]
        
    #     for path in possible_paths:
    #         if os.path.exists(path):
    #             return path
    #     return None

# Create global instance
windows_printer = WindowsPrinter() if WIN32_AVAILABLE else None
