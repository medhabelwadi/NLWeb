"""Functions for extracting Snowflake connection parameters from configuration."""

from config.config import CONFIG

class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid"""
    pass

def get_pat() -> str:
    """
    Retrieve the Programmatic Access Token (PAT) from the environment, or raise an error.
    """
    config = CONFIG.providers.get("snowflake")
    pat = config.api_key.strip('"') if config and config.api_key else None
    if not pat:
        raise ConfigurationError(f"Unable to determine Snowflake Programmatic Access Token to use (PAT), is SNOWFLAKE_PAT set?")
    return pat


def get_account_url() -> str:
    """
    Retrieve the account URL that is the base URL for all Snowflake Cortex API REST calls, or raise an error.
    """
    config = CONFIG.providers.get("snowflake")
    account_url = config.endpoint.strip('"')
    if not account_url:
        raise ConfigurationError(f"Unable to determine Snowflake Account URL, is SNOWFLAKE_ACCOUNT_URL set?")
    return account_url
