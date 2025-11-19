# Environment-Based Configuration Management

The ONEX Environment-Based Configuration Management system provides a unified approach to handling environment variables, configuration validation, type conversion, and hierarchical overrides across all ONEX components.

## Overview

The configuration system is built around the `ModelEnvironmentConfig` base class, which extends Pydantic models with powerful environment variable loading capabilities.

### Key Features

- **Environment Variable Auto-Discovery**: Automatically maps environment variables to model fields
- **Type Conversion**: Intelligent conversion from strings to appropriate Python types
- **Validation**: Full Pydantic validation with custom validators
- **Hierarchical Overrides**: Environment variables can be overridden by direct parameters
- **Production Safety**: Built-in production environment detection and security
- **Configuration Registry**: Centralized registry for managing multiple configurations
- **Documentation Generation**: Auto-generated documentation for environment variables

## Quick Start

### Basic Usage

```python
from omnibase_core.models.configuration.model_database_config import ModelDatabaseConfig
from pydantic import Field

class ModelDatabaseConfig(ModelEnvironmentConfig):
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="omnibase", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")

# Set environment variables
import os
os.environ['DB_HOST'] = 'production-db.example.com'
os.environ['DB_PORT'] = '5432'
os.environ['DB_PASSWORD'] = 'secure_password'

# Load configuration from environment
config = ModelDatabaseConfig.from_environment(prefix='DB')

print(f"Connecting to: {config.host}:{config.port}")
```python

## Core Classes

### ModelEnvironmentConfig

The base class for all environment-configurable models.

```python
class ModelEnvironmentConfig(BaseModel):
    @classmethod
    def from_environment(
        cls: Type[T],
        prefix: Optional[str] = None,
        env_file: Optional[Path] = None,
        strict: bool = True,
        **overrides: Any
    ) -> T:
        """Create configuration from environment variables."""
        ...
```text

#### Parameters

- **prefix**: Environment variable prefix (e.g., 'DB' for DB_HOST, DB_PORT)
- **env_file**: Optional .env file to load variables from
- **strict**: Whether to fail on validation errors or use defaults
- **overrides**: Direct parameter overrides that take precedence over environment

### ModelEnvironmentPrefix

Manages environment variable prefix formatting.

```python
prefix = ModelEnvironmentPrefix(prefix="MYAPP", separator="_")
key = prefix.format_key("database_host")  # -> "MYAPP_DATABASE_HOST"
```python

### Configuration Registry

Centralized management for multiple configurations.

```python
from omnibase_core.models.configuration import model_database_config

# Register configurations
db_config = register_config('database', ModelDatabaseConfig, prefix='DB')
api_config = register_config('api', ModelAPIConfig, prefix='API')

# Retrieve from registry
config = config_registry.get('database')

# List all registered configs
configs = config_registry.list_configs()

# Reload all configurations
config_registry.reload_all()
```python

## Environment Variable Mapping

### Automatic Key Generation

The system automatically generates multiple possible environment variable keys for each field:

```python
class ModelConfig(ModelEnvironmentConfig):
    api_key: str = Field(...)
    maxRetries: int = Field(...)  # camelCase
```python

For `api_key` with prefix `APP`:
- `APP_API_KEY` (preferred)
- `API_KEY` (without prefix)

For `maxRetries` with prefix `APP`:
- `APP_MAXRETRIES`
- `APP_MAX_RETRIES` (camelCase converted)
- `MAXRETRIES`
- `MAX_RETRIES`

### Type Conversion

Automatic conversion from environment variable strings to Python types:

#### Boolean Conversion
```bash
# These all convert to True
export ENABLE_DEBUG=true
export ENABLE_DEBUG=True
export ENABLE_DEBUG=1
export ENABLE_DEBUG=yes
export ENABLE_DEBUG=on

# These all convert to False
export ENABLE_DEBUG=false
export ENABLE_DEBUG=0
export ENABLE_DEBUG=no
export ENABLE_DEBUG=off
export ENABLE_DEBUG=anything_else
```bash

#### List Conversion
```bash
# Converts to ['auth', 'logging', 'metrics']
export FEATURES=auth,logging,metrics
```bash

#### Dictionary Conversion
```bash
# Converts to {'key1': 'value1', 'key2': 'value2'}
export SETTINGS=key1=value1,key2=value2
```python

## Advanced Features

### Nested Configuration

```python
class ModelDatabaseConfig(ModelEnvironmentConfig):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)

class ModelApplicationConfig(ModelEnvironmentConfig):
    app_name: str = Field(...)
    database: ModelDatabaseConfig = Field(default_factory=ModelDatabaseConfig)

# Environment variables for nested config:
# APP_APP_NAME=myapp
# APP_DATABASE_HOST=db.example.com
# APP_DATABASE_PORT=5432

config = ModelApplicationConfig.from_environment(prefix='APP')
```python

### Production Environment Detection

```python
from omnibase_core.models.configuration import model_database_config

# Checks ENVIRONMENT, NODE_ENV, DEBUG, DEV_MODE variables
if is_production_environment():
    # Apply production-specific validation
    pass
```python

### Custom Validation

```python
class ModelAPIConfig(ModelEnvironmentConfig):
    api_key: str = Field(...)

    @field_validator('api_key')
    @classmethod
    def validate_api_key_in_production(cls, v: str) -> str:
        if is_production_environment() and not v:
            raise ValueError("API key is required in production")
        return v
```text

### Configuration Documentation

Generate documentation for all environment variables:

```python
docs = ModelApplicationConfig.get_env_documentation()
for doc in docs:
    print(f"Field: {doc['field']}")
    print(f"Environment Keys: {doc['env_keys']}")
    print(f"Description: {doc['description']}")
    print(f"Type: {doc['type']}")
    print(f"Required: {doc['required']}")
```python

## Utility Functions

### Quick Environment Helpers

```python
from omnibase_core.models.configuration import model_database_config

# Cached environment variable access with type conversion
debug = get_env_bool('DEBUG', False)
port = get_env_int('PORT', 8000)
timeout = get_env_float('TIMEOUT', 30.0)
features = get_env_list('FEATURES', ['default'])
```text

## Best Practices

### 1. Use Descriptive Prefixes

```python
# Good - Clear service identification
database_config = ModelDatabaseConfig.from_environment(prefix='DATABASE')
redis_config = ModelRedisConfig.from_environment(prefix='REDIS')

# Avoid - Generic prefixes that can conflict
config = ModelConfig.from_environment(prefix='APP')
```python

### 2. Provide Sensible Defaults

```python
class ModelServiceConfig(ModelEnvironmentConfig):
    timeout: float = Field(default=30.0, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    # Don't set defaults for sensitive or required configuration
    api_key: str = Field(..., description="API authentication key")
```python

### 3. Use Validation for Critical Settings

```python
class ModelDatabaseConfig(ModelEnvironmentConfig):
    host: str = Field(...)
    port: int = Field(default=5432)
    password: str = Field(default="")

    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator('password')
    @classmethod
    def validate_password_in_production(cls, v: str) -> str:
        if is_production_environment() and not v:
            raise ValueError("Password required in production")
        return v
```python

### 4. Use Registry for Shared Configurations

```python
# In your application initialization
config_registry.register('database', ModelDatabaseConfig.from_environment(prefix='DB'))
config_registry.register('redis', ModelRedisConfig.from_environment(prefix='REDIS'))

# In your service modules
from omnibase_core.models.configuration import model_database_config

def get_database_connection():
    db_config = config_registry.get('database')
    return connect(db_config.connection_string())
```python

### 5. Handle Sensitive Configuration Securely

```python
class ModelSecureConfig(ModelEnvironmentConfig):
    api_key: str = Field(..., description="API key")

    def get_env_summary(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        summary = super().get_env_summary(mask_sensitive)
        # Custom masking logic
        if mask_sensitive:
            summary['api_key'] = '***MASKED***'
        return summary
```python

## Environment File Support

### Loading from .env Files

```python
# .env file content:
# DB_HOST=localhost
# DB_PORT=5432
# DB_PASSWORD=secret

config = ModelDatabaseConfig.from_environment(
    prefix='DB',
    env_file=Path('.env')
)
```text

### Multiple Environment Files

```python
# Load different configs for different environments
if is_production_environment():
    config = ModelConfig.from_environment(env_file=Path('.env.prod'))
else:
    config = ModelConfig.from_environment(env_file=Path('.env.dev'))
```bash

## Error Handling

### Strict vs Non-Strict Mode

```python
# Strict mode (default) - fails on validation errors
try:
    config = ModelConfig.from_environment(strict=True)
except ValidationError as e:
    logger.error(f"Configuration validation failed: {e}")
    sys.exit(1)

# Non-strict mode - uses defaults for missing/invalid values
config = ModelConfig.from_environment(strict=False)
```python

### Common Issues and Solutions

#### Missing Required Fields
```python
# Problem: Required field without default
class ModelConfig(ModelEnvironmentConfig):
    api_key: str = Field(...)  # Required

# Solution: Set environment variable or provide override
config = ModelConfig.from_environment(api_key="fallback-key")
```text

#### Type Conversion Errors
```python
# Problem: Invalid value for numeric field
# PORT=invalid_number

# Solution: The system will log warning and use default
port = get_env_int('PORT', 8000)  # Uses 8000 if PORT is invalid
```python

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from omnibase_core.models.configuration.model_database_config import ModelDatabaseConfig

class ModelAppConfig(ModelEnvironmentConfig):
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

config = ModelAppConfig.from_environment(prefix='APP')
app = FastAPI(debug=config.debug)

@app.get("/health")
async def health():
    return {"status": "healthy", "config": config.get_env_summary()}
```python

### Database Connection

```python
import asyncpg
from omnibase_core.models.configuration.model_database_config import ModelDatabaseConfig

class ModelDatabaseConfig(ModelEnvironmentConfig):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="myapp")
    username: str = Field(default="postgres")
    password: str = Field(default="")

    def get_dsn(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

async def get_db_pool():
    db_config = ModelDatabaseConfig.from_environment(prefix='DB')
    return await asyncpg.create_pool(db_config.get_dsn())
```python

## Migration Guide

### From Direct Environment Access

**Before:**
```python
import os

host = os.getenv('DB_HOST', 'localhost')
port = int(os.getenv('DB_PORT', '5432'))
debug = os.getenv('DEBUG', 'false').lower() == 'true'
```python

**After:**
```python
class ModelConfig(ModelEnvironmentConfig):
    db_host: str = Field(default='localhost')
    db_port: int = Field(default=5432)
    debug: bool = Field(default=False)

config = ModelConfig.from_environment()
```python

### From Existing Configuration Classes

**Before:**
```python
class Config:
    def __init__(self):
        self.host = os.getenv('HOST', 'localhost')
        self.port = int(os.getenv('PORT', '8000'))
```python

**After:**
```python
class ModelConfig(ModelEnvironmentConfig):
    host: str = Field(default='localhost')
    port: int = Field(default=8000)

config = ModelConfig.from_environment()
```python

## Troubleshooting

### Debug Environment Variable Loading

```python
# Enable debug logging
import logging
logging.getLogger('your_module_name').setLevel(logging.DEBUG)  # Replace with actual module

# Check generated environment keys
keys = ModelConfig._generate_env_keys('field_name')
print(f"Looking for environment variables: {keys}")

# Check loaded configuration
config = ModelConfig.from_environment()
print(f"Configuration summary: {config.get_env_summary()}")
```python

### Verify Environment Detection

```python
from omnibase_core.models.configuration import model_database_config

print(f"Production environment: {is_production_environment()}")
print(f"Environment variables checked:")
print(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
print(f"  NODE_ENV: {os.getenv('NODE_ENV')}")
print(f"  DEBUG: {os.getenv('DEBUG')}")
```text

This comprehensive configuration management system provides robust, type-safe, and flexible environment variable handling for all ONEX components while maintaining security and ease of use.
