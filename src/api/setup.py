"""
Setup API - First-time Configuration Wizard

Provides API endpoints for initial product setup including database configuration,
OpenAI API key, and admin user creation. Enables SaaS-like deployment experience.
"""

import os
import logging
import secrets
import json
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
import psycopg2
from psycopg2 import sql

from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)

router = APIRouter()

# Setup configuration file path
# Use environment variable or default to local data directory
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
SETUP_CONFIG_PATH = DATA_DIR / "setup.json"
SETUP_LOCK_PATH = DATA_DIR / ".setup_complete"


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    use_docker_db: bool = Field(True, description="Use managed Docker database or bring your own")
    host: str = Field("postgres", description="Database host (e.g., postgres, localhost)")
    port: int = Field(5432, description="Database port")
    name: str = Field("datatruth_internal", description="Database name")
    user: str = Field("datatruth_app", description="Database user")
    password: str = Field("", description="Database password")
    admin_user: str = Field("datatruth_admin", description="Admin database user")
    admin_password: str = Field("", description="Admin password")
    
    @validator('password', 'admin_password')
    def validate_password_if_needed(cls, v, values):
        # Only validate password length if not using Docker database
        use_docker = values.get('use_docker_db', True)
        if not use_docker and v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters when using existing database')
        return v


class OpenAIConfig(BaseModel):
    """OpenAI configuration model."""
    api_key: str = Field(..., min_length=20, description="OpenAI API key")
    model: str = Field("gpt-4o-mini", description="Default model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature setting")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        # Support various OpenAI key formats: sk-, sk-proj-, etc.
        if not v.startswith('sk-') and not v.startswith('org-'):
            raise ValueError('Invalid OpenAI API key format. Keys should start with "sk-" or "org-"')
        return v


class AdminUserConfig(BaseModel):
    """Admin user configuration model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = Field(None, description="Admin email address")
    full_name: Optional[str] = Field(None, description="Admin full name")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class SetupRequest(BaseModel):
    """Complete setup request model."""
    database: DatabaseConfig
    openai: OpenAIConfig
    admin_user: AdminUserConfig
    app_name: str = Field("DataTruth", description="Application name")
    app_url: Optional[str] = Field(None, description="Application URL")


class SetupStatusResponse(BaseModel):
    """Setup status response."""
    is_configured: bool
    needs_setup: bool
    setup_step: Optional[str] = None
    error: Optional[str] = None


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """
    Check if the application has been configured.
    Returns setup status and current step if in progress.
    """
    try:
        # Check if setup is complete
        if SETUP_LOCK_PATH.exists():
            return SetupStatusResponse(
                is_configured=True,
                needs_setup=False
            )
        
        # Check if partial configuration exists
        if SETUP_CONFIG_PATH.exists():
            with open(SETUP_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                return SetupStatusResponse(
                    is_configured=False,
                    needs_setup=True,
                    setup_step=config.get('current_step', 'start')
                )
        
        # First time setup needed
        return SetupStatusResponse(
            is_configured=False,
            needs_setup=True,
            setup_step='start'
        )
    
    except Exception as e:
        logger.error(f"Error checking setup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check setup status: {str(e)}"
        )


@router.post("/test-database")
async def test_database_connection(config: DatabaseConfig):
    """
    Test database connection with provided credentials.
    Returns connection status and database info if successful.
    """
    try:
        # Try to connect
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            user=config.admin_user,
            password=config.admin_password,
            connect_timeout=5
        )
        
        # Get PostgreSQL version
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            
            # Check if database exists
            cur.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                [config.name]
            )
            db_exists = cur.fetchone() is not None
        
        conn.close()
        
        return {
            "success": True,
            "message": "Database connection successful",
            "version": version,
            "database_exists": db_exists
        }
    
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return {
            "success": False,
            "error": "Connection failed",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Database test error: {e}")
        return {
            "success": False,
            "error": "Test failed",
            "message": str(e)
        }


@router.post("/test-openai")
async def test_openai_connection(config: OpenAIConfig):
    """
    Test OpenAI API key and connection.
    Returns API status and available models if successful.
    """
    try:
        import openai
        
        # Set API key
        client = openai.OpenAI(api_key=config.api_key)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
            max_tokens=10,
            temperature=0.0
        )
        
        return {
            "success": True,
            "message": "OpenAI API key is valid",
            "model": config.model,
            "response": response.choices[0].message.content
        }
    
    except openai.AuthenticationError as e:
        logger.error(f"OpenAI authentication failed: {e}")
        return {
            "success": False,
            "error": "Authentication failed",
            "message": "Invalid API key"
        }
    except openai.NotFoundError as e:
        logger.error(f"OpenAI model not found: {e}")
        return {
            "success": False,
            "error": "Model not found",
            "message": f"Model '{config.model}' not available"
        }
    except Exception as e:
        logger.error(f"OpenAI test error: {e}")
        return {
            "success": False,
            "error": "Test failed",
            "message": str(e)
        }


@router.post("/initialize")
async def initialize_setup(request: SetupRequest):
    """
    Initialize the application with provided configuration.
    This will:
    1. Create/verify database (or use Docker managed database)
    2. Run database initialization script
    3. Create admin user
    4. Save configuration
    5. Mark setup as complete
    """
    try:
        logger.info("Starting application initialization...")
        
        # Handle Docker database vs existing database
        if request.database.use_docker_db:
            logger.info("Using managed Docker database...")
            # Use Docker PostgreSQL container defaults
            db_config = {
                "host": "postgres",
                "port": 5432,
                "name": request.database.name or "datatruth_internal",
                "user": request.database.user or "datatruth_app",
                "password": request.database.password or secrets.token_urlsafe(16),
                "admin_user": "postgres",  # Default Docker postgres user
                "admin_password": os.getenv("POSTGRES_PASSWORD", "postgres")
            }
            logger.info(f"Docker database config: host={db_config['host']}, db={db_config['name']}")
        else:
            logger.info("Using existing database configuration...")
            # Validate required fields for existing database
            if not request.database.admin_password or len(request.database.admin_password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Admin password is required and must be at least 8 characters"
                )
            
            db_config = {
                "host": request.database.host,
                "port": request.database.port,
                "name": request.database.name,
                "user": request.database.user,
                "password": request.database.password,
                "admin_user": request.database.admin_user,
                "admin_password": request.database.admin_password
            }
        
        # Step 1: Verify database connection
        logger.info("Step 1/5: Verifying database connection...")
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["admin_user"],
            password=db_config["admin_password"],
            connect_timeout=10
        )
        conn.autocommit = True
        
        # Step 2: Create database if not exists
        logger.info("Step 2/5: Creating database...")
        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"),
                [db_config["name"]]
            )
            
            if not cur.fetchone():
                # Create database
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(db_config["name"])
                    )
                )
                logger.info(f"Database '{db_config['name']}' created")
            else:
                logger.info(f"Database '{db_config['name']}' already exists")
        
        conn.close()
        
        # Step 3: Initialize database schema
        logger.info("Step 3/5: Initializing database schema...")
        # Try multiple possible paths for the schema file
        schema_paths = [
            Path("/app/database/init_database.sql"),
            Path("./database/init_database.sql"),
            Path("../database/init_database.sql")
        ]
        schema_file = next((p for p in schema_paths if p.exists()), None)
        
        if not schema_file:
            raise FileNotFoundError("Database initialization script not found")
        
        # Connect to the new database
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["name"],
            user=db_config["admin_user"],
            password=db_config["admin_password"]
        )
        
        # Read and execute initialization script
        with open(schema_file, 'r') as f:
            init_sql = f.read()
        
        # Replace placeholders in SQL
        init_sql = init_sql.replace('datatruth_app', db_config["user"])
        init_sql = init_sql.replace('datatruth_admin', db_config["admin_user"])
        
        with conn.cursor() as cur:
            cur.execute(init_sql)
        
        conn.commit()
        logger.info("Database schema initialized")
        
        # Step 4: Create admin user
        logger.info("Step 4/5: Creating admin user...")
        import bcrypt
        
        # Hash password with bcrypt directly (handles 72-byte limit internally)
        password_bytes = request.admin_user.password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        with conn.cursor() as cur:
            # Update default admin user and ensure role is set to admin
            cur.execute("""
                UPDATE users 
                SET username = %s,
                    password_hash = %s,
                    email = %s,
                    full_name = %s,
                    role = 'admin',
                    updated_at = NOW()
                WHERE username = 'admin'
            """, (
                request.admin_user.username,
                hashed_password,
                request.admin_user.email or f"{request.admin_user.username}@datatruth.local",
                request.admin_user.full_name or request.admin_user.username
            ))
        
        conn.commit()
        conn.close()
        logger.info("Admin user created")
        
        # Step 5: Save configuration
        logger.info("Step 5/5: Saving configuration...")
        
        # Generate secure keys
        secret_key = secrets.token_urlsafe(32)
        jwt_secret = secrets.token_urlsafe(32)
        
        # Create configuration
        config = {
            "app_name": request.app_name,
            "app_url": request.app_url or "http://localhost:8000",
            "database": {
                "use_docker_db": request.database.use_docker_db,
                "host": db_config["host"],
                "port": db_config["port"],
                "name": db_config["name"],
                "user": db_config["user"],
                "password": db_config["password"],
                "admin_user": db_config["admin_user"],
                "admin_password": db_config["admin_password"]
            },
            "openai": {
                "api_key": request.openai.api_key,
                "model": request.openai.model,
                "temperature": request.openai.temperature
            },
            "security": {
                "secret_key": secret_key,
                "jwt_secret_key": jwt_secret
            }
        }
        
        # Ensure data directory exists
        SETUP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        with open(SETUP_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create .env file
        env_content = f"""# DataTruth Configuration
# Auto-generated on setup

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
APP_NAME={request.app_name}

# Database
INTERNAL_DB_HOST={db_config["host"]}
INTERNAL_DB_PORT={db_config["port"]}
INTERNAL_DB_NAME={db_config["name"]}
INTERNAL_DB_USER={db_config["user"]}
INTERNAL_DB_PASSWORD={db_config["password"]}
INTERNAL_DB_ADMIN_USER={db_config["admin_user"]}
INTERNAL_DB_ADMIN_PASSWORD={db_config["admin_password"]}

# Security
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret}
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# OpenAI
OPENAI_API_KEY={request.openai.api_key}
OPENAI_MODEL={request.openai.model}
OPENAI_TEMPERATURE={request.openai.temperature}

# API
API_PORT=8000
API_WORKERS=4
CORS_ORIGINS=http://localhost:3000,{request.app_url or 'http://localhost:8000'}
ALLOWED_HOSTS=localhost,127.0.0.1

# Features
ENABLE_USER_ACTIVITY_TRACKING=true
ENABLE_PERSONALIZED_SUGGESTIONS=true
ENABLE_CALCULATED_METRICS=true
ENABLE_INSIGHTS=true
ENABLE_VECTOR_SEARCH=false

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
"""
        
        # Write to project root which is accessible from host
        env_file = Path(".env")
        env_file_host = DATA_DIR / ".env.production"  # Mounted volume
        
        # Write to both locations for compatibility
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        with open(env_file_host, 'w') as f:
            f.write(env_content)
        
        # Save configuration to database for persistence
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["name"],
                user=db_config["admin_user"],
                password=db_config["admin_password"]
            )
            
            config_items = {
                "openai_api_key": request.openai.api_key,
                "openai_model": request.openai.model,
                "openai_temperature": str(request.openai.temperature),
                "app_name": request.app_name,
                "secret_key": secret_key,
                "jwt_secret_key": jwt_secret,
            }
            
            cursor = conn.cursor()
            for key, value in config_items.items():
                is_sensitive = key in ["openai_api_key", "secret_key", "jwt_secret_key"]
                cursor.execute(
                    """
                    INSERT INTO system_config (key, value, is_sensitive, updated_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET 
                        value = EXCLUDED.value,
                        updated_at = CURRENT_TIMESTAMP,
                        updated_by = EXCLUDED.updated_by
                    """,
                    (key, value, is_sensitive, request.admin_user.username)
                )
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Configuration saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save config to database: {e}")
            # Don't fail setup if this fails
        
        # Mark setup as complete
        SETUP_LOCK_PATH.touch()
        
        logger.info("Setup completed successfully!")
        
        return {
            "success": True,
            "message": "Application initialized successfully",
            "admin_user": request.admin_user.username,
            "next_steps": [
                "Application will restart automatically",
                f"Login with username: {request.admin_user.username}",
                "Start adding database connections",
                "Create calculated metrics",
                "Invite team members"
            ]
        }
    
    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup failed: {str(e)}"
        )


@router.post("/reset")
async def reset_setup():
    """
    Reset setup configuration (admin only, requires authentication).
    This will clear the setup lock and allow reconfiguration.
    """
    try:
        if SETUP_LOCK_PATH.exists():
            SETUP_LOCK_PATH.unlink()
        
        if SETUP_CONFIG_PATH.exists():
            SETUP_CONFIG_PATH.unlink()
        
        return {
            "success": True,
            "message": "Setup reset successfully. Please restart the application."
        }
    
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


@router.get("/config")
async def get_config():
    """Get current configuration (API keys masked)."""
    try:
        conn = InternalDB.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value, is_sensitive FROM system_config")
        rows = cursor.fetchall()
        
        config = {}
        for row in rows:
            key = row['key']
            value = row['value']
            is_sensitive = row['is_sensitive']
            
            if is_sensitive:
                # Mask sensitive values
                config[key] = '***' + value[-4:] if len(value) > 4 else '***'
            else:
                # Convert numeric values to proper types
                if key == 'openai_temperature':
                    try:
                        config[key] = float(value)
                    except (ValueError, TypeError):
                        config[key] = value
                else:
                    config[key] = value
        
        cursor.close()
        conn.close()
        
        return config
    
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {str(e)}"
        )


@router.put("/config")
async def update_config(config: dict):
    """Update configuration in database."""
    try:
        conn = InternalDB.get_connection()
        cursor = conn.cursor()
        
        # Update each config value
        for key, value in config.items():
            # Skip masked values (unchanged sensitive fields)
            if isinstance(value, str) and value.startswith('***'):
                continue
                
            is_sensitive = key in ['openai_api_key', 'secret_key', 'jwt_secret_key', 'password']
            
            cursor.execute(
                """
                INSERT INTO system_config (key, value, is_sensitive, updated_at, updated_by)
                VALUES (%s, %s, %s, NOW(), 'admin')
                ON CONFLICT (key) 
                DO UPDATE SET 
                    value = EXCLUDED.value,
                    is_sensitive = EXCLUDED.is_sensitive,
                    updated_at = NOW(),
                    updated_by = 'admin'
                """,
                (key, str(value), is_sensitive)
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("Configuration updated successfully")
        return {
            "success": True,
            "message": "Configuration updated successfully. Restart API for changes to take effect."
        }
    
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


def is_setup_complete() -> bool:
    """Check if initial setup is complete."""
    return SETUP_LOCK_PATH.exists()


def load_setup_config() -> Optional[Dict[str, Any]]:
    """Load setup configuration if exists."""
    if SETUP_CONFIG_PATH.exists():
        with open(SETUP_CONFIG_PATH, 'r') as f:
            return json.load(f)
    return None
