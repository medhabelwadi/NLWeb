import os
import sys
import time
import tempfile

class AzureLogger:
    """
    Logger that redirects output to a temporary file when running on Azure,
    but preserves normal print behavior on local machines.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AzureLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not AzureLogger._initialized:
            self.running_on_azure = 'WEBSITE_SITE_NAME' in os.environ
            self.log_file = None
            self.original_stdout = sys.stdout
            
            if self.running_on_azure:
                try:
                    # Create a timestamped log file in the temp directory
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    log_dir = tempfile.gettempdir()
                    self.log_filename = os.path.join(log_dir, f"azure_app_log_{timestamp}.txt")
                    self.log_file = open(self.log_filename, 'a', buffering=1)  # Line buffered
                    self.log(f"Azure logger initialized. Logs will be written to {self.log_filename}")
                except Exception as e:
                    # If we can't open the log file, print to stdout and continue
                    print(f"Error initializing Azure logger: {str(e)}")
            
            AzureLogger._initialized = True
    
    def log(self, message):
        """Log a message to file if on Azure, or print it if local"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if self.running_on_azure and self.log_file:
            try:
                self.log_file.write(formatted_message + "\n")
                self.log_file.flush()
            except Exception as e:
                # Fall back to standard output if writing to file fails
                print(f"Error writing to log file: {str(e)}")
                print(formatted_message)
        else:
            # Local execution - just print normally
            print(formatted_message)
    
    def close(self):
        """Close the log file if open"""
        if self.log_file:
            try:
                self.log_file.close()
                self.log_file = None
            except:
                pass

# Create a global instance and function for easy access
_logger = AzureLogger()

def log(message):
    """Global log function to be used throughout the application"""
    _logger.log(message)

def close_logs():
    """Close log files when application exits"""
    _logger.close()