import logging
import sys
import os
from enum import Enum
from typing import Optional, Dict, Any
from functools import lru_cache


class LogLevel(Enum):
    """Enumeration for logging verbosity levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

    @classmethod
    def level_matches(cls, logger_level, message_level):
        """
        Check if a message at message_level should be logged given the logger's logger_level.
        
        Args:
            logger_level: The configured level of the logger
            message_level: The level of the message being logged
            
        Returns:
            True if the message should be logged, False otherwise
        """
        return message_level.value >= logger_level.value


class LoggerUtility:
    """A configurable logging utility with different verbosity levels."""
    
    def __init__(
        self,
        name: str = "AppLogger",
        level: LogLevel = LogLevel.ERROR,
        format_string: Optional[str] = None,
        log_file: Optional[str] = None,
        console_output: bool = True
    ):
        """
        Initialize the logger utility.
        
        Args:
            name: Logger name
            level: Initial logging level
            format_string: Custom format for log messages
            log_file: Path to log file (if None, no file logging)
            console_output: Whether to output to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.value)
        
        # Store the current level for reference
        self._current_level = level

      #  print(f"Logger level: {level} {name}")
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Default format if none provided
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = logging.Formatter(format_string)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def set_level(self, level: LogLevel):
        """Set the logging verbosity level."""
        self._current_level = level
        self.logger.setLevel(level.value)
    
    def get_level(self) -> LogLevel:
        """Get the current logging level."""
        return self._current_level
    
    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        if LogLevel.level_matches(self.get_level(), LogLevel.DEBUG):
            self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log an info message."""
        if LogLevel.level_matches(self.get_level(), LogLevel.INFO):
            self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        if LogLevel.level_matches(self.get_level(), LogLevel.WARNING):
            self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log an error message."""
        if LogLevel.level_matches(self.get_level(), LogLevel.ERROR):
            self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log a critical message."""
        if LogLevel.level_matches(self.get_level(), LogLevel.CRITICAL):
            self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log an exception with traceback."""
        self.logger.exception(message, **kwargs)
    
    def log_with_context(self, level: LogLevel, message: str, context: Dict[str, Any]):
        """
        Log a message with additional context information.
        
        Args:
            level: Log level
            message: Log message
            context: Dictionary of context information
        """
        if LogLevel.level_matches(self.get_level(), level):
            context_str = " - ".join(f"{k}={v}" for k, v in context.items())
            full_message = f"{message} | Context: {context_str}"
            self.logger.log(level.value, full_message)


@lru_cache(maxsize=None)
def get_logger(
    name: str,
    level_env_var: str = "LOG_LEVEL",
    default_level: LogLevel = LogLevel.ERROR,
    log_file: Optional[str] = None
) -> LoggerUtility:
    """
    Get or create a logger instance with caching.
    
    Args:
        name: Logger name
        level_env_var: Environment variable name for log level
        default_level: Default log level if env var not set
        log_file: Optional log file path
    
    Returns:
        LoggerUtility instance
    """
    # Check environment variable for log level
    env_level = os.getenv(level_env_var, "").upper()
    level = default_level
    
    if env_level:
        try:
            level = LogLevel[env_level]
        except KeyError:
            # Invalid env value, use default
            pass
    
    # Create logger
    return LoggerUtility(
        name=name,
        level=level,
        log_file=log_file,
        console_output=True
    )


# Configuration-based logger getter
def get_logger_from_config(module_name: str, config_path: str = "config/logging_config.yaml") -> LoggerUtility:
    """
    Get a logger configured from YAML configuration file.
    
    Args:
        module_name: Name of the module
        config_path: Path to the YAML configuration file
    
    Returns:
        LoggerUtility instance
    """
    try:
        from .logging_config_helper import get_configured_logger
        return get_configured_logger(module_name)
    except ImportError:
        # Fallback to default logger if config helper not available
        return get_logger(module_name)


# Example usage
if __name__ == "__main__":
    # Create logger with default settings
    logger = LoggerUtility("MyApp")
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print("\n--- Changing to DEBUG level ---")
    logger.set_level(LogLevel.DEBUG)
    
    logger.debug("Now debug messages are visible")
    logger.info("Info still visible")
    
    print("\n--- Changing to ERROR level ---")
    logger.set_level(LogLevel.ERROR)
    
    logger.debug("Debug not visible at ERROR level")
    logger.info("Info not visible at ERROR level")
    logger.error("Error messages are still visible")
    
    print("\n--- Using context logging ---")
    logger.set_level(LogLevel.INFO)
    logger.log_with_context(
        LogLevel.INFO,
        "User action",
        {"user_id": 123, "action": "login", "ip": "192.168.1.1"}
    )
    
    print("\n--- Creating a file logger ---")
    file_logger = LoggerUtility(
        "FileLogger",
        level=LogLevel.DEBUG,
        log_file="app.log",
        format_string='%(asctime)s [%(levelname)8s] %(message)s'
    )
    
    file_logger.info("This message goes to both console and file")
    file_logger.debug("Debug message in custom format")
    
    # Demonstrate exception logging
    try:
        result = 1 / 0
    except Exception as e:
        file_logger.exception("An error occurred during calculation")