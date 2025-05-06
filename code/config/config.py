# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Basic config services, including loading config from config_llm.yaml, config_retrieval.yaml, config_webserver.yaml, config_nlweb.yaml
WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import os
import yaml
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Dict, Optional, Any, List

@dataclass
class ModelConfig:
    high: str
    low: str

@dataclass
class ProviderConfig:
    api_key: Optional[str] = None
    models: Optional[ModelConfig] = None
    endpoint: Optional[str] = None
    api_version: Optional[str] = None
    embedding_model: Optional[str] = None
    azure_embedding_api_version: Optional[str] = None

@dataclass
class RetrievalProviderConfig:
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    database_path: Optional[str] = None
    index_name: Optional[str] = None
    db_type: Optional[str] = None  

@dataclass
class SSLConfig:
    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None

@dataclass
class LoggingConfig:
    level: str = "info"
    file: str = "./logs/webserver.log"

@dataclass
class StaticConfig:
    enable_cache: bool = True
    cache_max_age: int = 3600
    gzip_enabled: bool = True

@dataclass
class ServerConfig:
    host: str = "localhost"
    enable_cors: bool = True
    max_connections: int = 100
    timeout: int = 30
    ssl: Optional[SSLConfig] = None
    logging: Optional[LoggingConfig] = None
    static: Optional[StaticConfig] = None

@dataclass
class NLWebConfig:
    sites: List[str]  # List of allowed sites

class AppConfig:
    config_paths = ["config.yaml", "config_llm.yaml", "config_retrieval.yaml", "config_webserver.yaml", "config_nlweb.yaml"]

    def __init__(self):
        load_dotenv()
        self.load_llm_config()
        self.load_retrieval_config()
        self.load_webserver_config()
        self.load_nlweb_config()

    def _get_config_value(self, value: Any, default: Any = None) -> Any:
        """
        Get configuration value. If value is a string, return it directly.
        Otherwise, treat it as an environment variable name and fetch from environment.
        Returns default if environment variable is not set or value is None.
        """
        if value is None:
            return default
            
        if isinstance(value, str):
            # If it's clearly an environment variable name (e.g., "OPENAI_API_KEY_ENV")
            if value.endswith('_ENV') or value.isupper():
                return os.getenv(value, default)
            # Otherwise, treat it as a literal string value
            else:
                return value
        
        # For non-string values, return as-is
        return value

    def load_llm_config(self, path: str = "config_llm.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        with open(full_path, "r") as f:
            data = yaml.safe_load(f)

            self.preferred_provider: str = data["preferred_provider"]
            self.providers: Dict[str, ProviderConfig] = {}

            for name, cfg in data.get("providers", {}).items():
                m = cfg.get("models", {})
                models = ModelConfig(
                    high=self._get_config_value(m.get("high")),
                    low=self._get_config_value(m.get("low"))
                ) if m else None
                
                # Extract configuration values from the YAML with the new method
                api_key = self._get_config_value(cfg.get("api_key_env"))
                api_endpoint = self._get_config_value(cfg.get("api_endpoint_env"))
                api_version = self._get_config_value(cfg.get("api_version_env"))
                embedding_model = self._get_config_value(cfg.get("embedding_model_env"))
                azure_embedding_api_version = self._get_config_value(cfg.get("azure-embedding-api-version"))

                # Create the provider config
                self.providers[name] = ProviderConfig(
                    api_key=api_key,
                    models=models,
                    endpoint=api_endpoint,
                    api_version=api_version,
                    embedding_model=embedding_model,
                    azure_embedding_api_version=azure_embedding_api_version
                )

    def load_retrieval_config(self, path: str = "config_retrieval.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        with open(full_path, "r") as f:
            data = yaml.safe_load(f)

        # Changed from preferred_provider to preferred_endpoint
            self.preferred_retrieval_endpoint: str = data["preferred_endpoint"]
            self.retrieval_endpoints: Dict[str, RetrievalProviderConfig] = {}

            # Changed from providers to endpoints
            for name, cfg in data.get("endpoints", {}).items():
                # Use the new method for all configuration values
                self.retrieval_endpoints[name] = RetrievalProviderConfig(
                    api_key=self._get_config_value(cfg.get("api_key_env")),
                    api_endpoint=self._get_config_value(cfg.get("api_endpoint_env")),
                    database_path=self._get_config_value(cfg.get("database_path")),
                    index_name=self._get_config_value(cfg.get("index_name")),
                    db_type=self._get_config_value(cfg.get("db_type"))  # Add db_type
                )
    
    def load_webserver_config(self, path: str = "config_webserver.yaml"):
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default webserver configuration.")
            data = {
                "port": 8080,
                "static_directory": "./static",
                "server": {}
            }
        
        # Load basic configurations with the new method
        self.port: int = self._get_config_value(data.get("port"), 8080)
        self.static_directory: str = self._get_config_value(data.get("static_directory"), "./static")
        self.mode: str = self._get_config_value(data.get("mode"), "production")
        
        # Convert relative paths to absolute paths based on config file location
        if not os.path.isabs(self.static_directory):
            self.static_directory = os.path.abspath(os.path.join(config_dir, self.static_directory))
        
        # Load server configurations
        server_data = data.get("server", {})
        
        # SSL configuration
        ssl_data = server_data.get("ssl", {})
        ssl_config = SSLConfig(
            enabled=self._get_config_value(ssl_data.get("enabled"), False),
            cert_file=self._get_config_value(ssl_data.get("cert_file_env")),
            key_file=self._get_config_value(ssl_data.get("key_file_env"))
        )
        
        # Logging configuration
        logging_data = server_data.get("logging", {})
        logging_config = LoggingConfig(
            level=self._get_config_value(logging_data.get("level"), "info"),
            file=self._get_config_value(logging_data.get("file"), "./logs/webserver.log")
        )
        
        # Convert logging file path to absolute if relative
        if not os.path.isabs(logging_config.file):
            logging_config.file = os.path.abspath(os.path.join(config_dir, logging_config.file))
        
        # Static file configuration
        static_data = server_data.get("static", {})
        static_config = StaticConfig(
            enable_cache=self._get_config_value(static_data.get("enable_cache"), True),
            cache_max_age=self._get_config_value(static_data.get("cache_max_age"), 3600),
            gzip_enabled=self._get_config_value(static_data.get("gzip_enabled"), True)
        )
        
        # Create the server config
        self.server = ServerConfig(
            host=self._get_config_value(server_data.get("host"), "localhost"),
            enable_cors=self._get_config_value(server_data.get("enable_cors"), True),
            max_connections=self._get_config_value(server_data.get("max_connections"), 100),
            timeout=self._get_config_value(server_data.get("timeout"), 30),
            ssl=ssl_config,
            logging=logging_config,
            static=static_config
        )

    def load_nlweb_config(self, path: str = "config_nlweb.yaml"):
        """Load Natural Language Web configuration."""
        # Get the directory where this config.py file is located
        config_dir = os.path.dirname(os.path.abspath(__file__))
        # Build the full path to the config file
        full_path = os.path.join(config_dir, path)
        
        try:
            with open(full_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            # If config file doesn't exist, use defaults
            print(f"Warning: {path} not found. Using default NLWeb configuration.")
            data = {
                "sites": ""
            }
        
        # Parse the comma-separated sites string into a list
        sites_str = self._get_config_value(data.get("sites"), "")
        sites_list = [site.strip() for site in sites_str.split(",") if site.strip()]
        
        self.nlweb = NLWebConfig(sites=sites_list)
    
    def get_ssl_cert_path(self) -> Optional[str]:
        """Get the SSL certificate file path."""
        if self.server.ssl:
            return self.server.ssl.cert_file
        return None
    
    def get_ssl_key_path(self) -> Optional[str]:
        """Get the SSL key file path."""
        if self.server.ssl:
            return self.server.ssl.key_file
        return None
    
    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled and properly configured."""
        return (self.server.ssl and 
                self.server.ssl.enabled and 
                self.server.ssl.cert_file is not None and 
                self.server.ssl.key_file is not None)
    
    def is_production_mode(self) -> bool:
        """Returns True if the system is running in production mode."""
        return getattr(self, 'mode', 'production').lower() == 'production'
    
    def is_development_mode(self) -> bool:
        """Returns True if the system is running in development mode."""
        return getattr(self, 'mode', 'production').lower() == 'development'
    
    def get_allowed_sites(self) -> List[str]:
        """Get the list of allowed sites from NLWeb configuration."""
        return self.nlweb.sites if hasattr(self, 'nlweb') else []
    
    def is_site_allowed(self, site: str) -> bool:
        """Check if a site is in the allowed sites list."""
        allowed_sites = self.get_allowed_sites()
        # If no sites are configured, allow all sites
        if not allowed_sites:
            return True
        return site in allowed_sites

# Global singleton
CONFIG = AppConfig()