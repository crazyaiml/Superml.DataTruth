"""
Configuration Loader

Loads configuration from database at application startup and updates settings.
"""

import os
import logging
from typing import Optional, Dict
import psycopg2

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get connection to internal database with retry logic."""
    import time
    max_retries = 5
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(
                host=os.getenv("INTERNAL_DB_HOST", "localhost"),
                port=int(os.getenv("INTERNAL_DB_PORT", "5432")),
                database=os.getenv("INTERNAL_DB_NAME", "datatruth_internal"),
                user=os.getenv("INTERNAL_DB_USER", "postgres"),
                password=os.getenv("INTERNAL_DB_PASSWORD", "postgres")
            )
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"[DEBUG] DB connection attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise


def load_config_from_db() -> Dict[str, str]:
    """
    Load configuration from database and return as dictionary.
    Returns empty dict if table doesn't exist or query fails.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM system_config")
        config = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()
        
        logger.info(f"Loaded {len(config)} configuration items from database")
        return config
        
    except Exception as e:
        logger.warning(f"Could not load config from database: {e}")
        return {}


def apply_config_to_env(config: Dict[str, str]):
    """Apply configuration from database to environment variables."""
    print(f"[DEBUG] apply_config_to_env called with {len(config)} items: {list(config.keys())}")
    for key, value in config.items():
        # Convert to uppercase for env var format
        env_key = key.upper()
        existing_value = os.environ.get(env_key, '')
        print(f"[DEBUG] Checking {env_key}: existing='{existing_value[:20] if existing_value else 'EMPTY'}', new='{value[:20] if value else 'EMPTY'}'")
        if env_key not in os.environ or not os.environ[env_key]:
            os.environ[env_key] = value
            print(f"[DEBUG] ✅ Set {env_key} = '{value[:20]}...'")
            logger.debug(f"Set {env_key} from database config")
        else:
            print(f"[DEBUG] ⏭️  Skipped {env_key} (already set)")


def initialize_config():
    """
    Initialize configuration at application startup.
    Loads config from database and applies to environment.
    """
    print("🔧 Initializing configuration from database...")
    logger.info("Initializing configuration from database...")
    try:
        config = load_config_from_db()
        if config:
            apply_config_to_env(config)
            print(f"✅ Configuration loaded successfully - {len(config)} keys loaded")
            print(f"   Loaded keys: {list(config.keys())}")
            logger.info(f"✅ Configuration loaded successfully - {len(config)} keys loaded")
            # Log loaded keys (without values for security)
            logger.info(f"Loaded configuration keys: {list(config.keys())}")
        else:
            print("⚠️  No database configuration found, using environment defaults")
            logger.warning("⚠️  No database configuration found, using environment defaults")
    except Exception as e:
        print(f"❌ Failed to initialize configuration: {e}")
        logger.error(f"❌ Failed to initialize configuration: {e}", exc_info=True)
        # Don't raise - allow API to start with env defaults
        import traceback
        traceback.print_exc()
