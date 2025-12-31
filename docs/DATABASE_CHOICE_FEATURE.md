# Database Choice Feature

## Overview

The setup wizard now provides users with two database options:
1. **Create New Database (Recommended)** - Automatically uses Docker-managed PostgreSQL
2. **Use Existing Database** - Connect to your own PostgreSQL instance

This improves the SaaS experience by eliminating unnecessary configuration for users who want a quick start.

## User Experience

### Option 1: Create New Database (Default)
- **Zero Configuration**: Users don't need to provide any database connection details
- **Automatic Setup**: Uses the Docker PostgreSQL container automatically
- **Secure Credentials**: Auto-generates secure passwords
- **Quick Start**: Simply click "Next" to proceed

**What Happens Behind the Scenes:**
- Connects to `postgres` container (host: `postgres`, port: `5432`)
- Uses default Docker postgres user
- Creates database with auto-generated secure credentials
- No manual configuration required

### Option 2: Use Existing Database
- **Full Control**: Users bring their own PostgreSQL database
- **Connection Testing**: Validates connection before proceeding
- **Requirements**:
  - PostgreSQL 12 or higher
  - Database must already exist
  - Admin user must have CREATE DATABASE and CREATE ROLE privileges

**User Provides:**
- Host and port
- Database name
- App user credentials
- Admin user credentials

## Implementation Details

### Frontend Changes (`frontend/src/components/Setup/SetupWizard.tsx`)

1. **Added `use_docker_db` flag** to `DatabaseConfig` interface:
```typescript
interface DatabaseConfig {
  use_docker_db: boolean;  // NEW: Choice flag
  host: string;
  port: number;
  // ... other fields
}
```

2. **Default to Docker database**:
```typescript
database: {
  use_docker_db: true,  // Default choice
  // ... other fields
}
```

3. **Choice UI** - Two option cards:
   - "Create New Database (Recommended)" - Highlighted by default
   - "Use Existing Database" - Alternative option

4. **Conditional Form Rendering**:
   - Connection form only shown when `use_docker_db === false`
   - Helpful info message shown when `use_docker_db === true`

5. **Smart Navigation Logic**:
```typescript
case 1:  // Database step
  return setupData.database.use_docker_db || testResults.database?.success;
```
- Docker DB: Proceed without testing
- Existing DB: Require successful connection test

### Backend Changes (`src/api/setup.py`)

1. **Updated `DatabaseConfig` model**:
```python
class DatabaseConfig(BaseModel):
    use_docker_db: bool = Field(True, description="Use managed Docker database or bring your own")
    host: str = Field("postgres", description="Database host")
    port: int = Field(5432, description="Database port")
    # ... passwords now optional (empty string default)
```

2. **Docker Database Configuration** in `initialize_setup()`:
```python
if request.database.use_docker_db:
    logger.info("Using managed Docker database...")
    db_config = {
        "host": "postgres",
        "port": 5432,
        "name": request.database.name or "datatruth_internal",
        "user": request.database.user or "datatruth_app",
        "password": request.database.password or secrets.token_urlsafe(16),
        "admin_user": "postgres",
        "admin_password": os.getenv("POSTGRES_PASSWORD", "postgres")
    }
```

3. **Validation** - Only validates admin password when using existing database:
```python
if not request.database.use_docker_db:
    if not request.database.admin_password or len(request.database.admin_password) < 8:
        raise HTTPException(...)
```

4. **Configuration Persistence** - Saves `use_docker_db` flag to setup.json

## Benefits

### For Users
✅ **Faster Onboarding** - Skip database configuration for quick start  
✅ **Less Confusion** - No need to understand Docker networking  
✅ **Flexibility** - Can still bring their own database if needed  
✅ **Clear Options** - Visual cards make the choice obvious  

### For Developers
✅ **Better UX** - Follows SaaS best practices  
✅ **Reduced Support** - Fewer configuration questions  
✅ **Secure Defaults** - Auto-generated credentials when using Docker  
✅ **Backwards Compatible** - Still supports existing database connections  

## Testing

### Test Scenario 1: Create New Database
1. Access setup wizard at http://localhost:3000
2. Step 1: Select "Create New Database (Recommended)"
3. Click "Next" (no form to fill)
4. Continue with OpenAI key and admin user
5. Complete setup

**Expected Result:**
- Database created automatically
- No connection errors
- Setup completes successfully

### Test Scenario 2: Use Existing Database
1. Access setup wizard
2. Step 1: Select "Use Existing Database"
3. Fill in connection details
4. Click "Test Database Connection"
5. Wait for successful connection
6. Click "Next"

**Expected Result:**
- Connection test passes
- Form shows all required fields
- Can proceed after successful test

## Docker Compose Reference

The Docker setup uses these environment variables for the PostgreSQL container:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
```

When using Docker database, the setup automatically connects to:
- **Host**: `postgres` (Docker service name)
- **Port**: `5432` (default PostgreSQL port)
- **Admin User**: `postgres` (default superuser)
- **Admin Password**: `postgres` (from POSTGRES_PASSWORD env var)

## Security Considerations

### Docker Database
- Auto-generates secure random passwords using `secrets.token_urlsafe(16)`
- Credentials saved securely in `/app/data/setup.json`
- Environment variables generated for `.env` file
- Internal Docker network (not exposed externally)

### Existing Database
- Requires users to provide secure credentials
- Tests connection before proceeding
- Validates PostgreSQL version compatibility
- Checks admin privileges before schema creation

## Future Enhancements

Potential improvements:
1. **Database Health Monitoring** - Show database status on dashboard
2. **Credential Rotation** - Allow changing auto-generated passwords
3. **Backup Configuration** - Setup automated backups during wizard
4. **Cloud Database Support** - Add templates for AWS RDS, Azure PostgreSQL, etc.
5. **Migration Path** - Allow switching from Docker to external database later

## Troubleshooting

### Issue: "Connection refused" when using Docker database
**Solution**: Ensure Docker Compose is running and `postgres` service is healthy:
```bash
docker-compose -f docker-compose.saas.yml ps
```

### Issue: "Cannot proceed to next step" when Docker database selected
**Solution**: This is expected if `use_docker_db` is not true. Check browser console for any errors.

### Issue: Existing database connection fails
**Solution**: Verify:
- PostgreSQL is running and accessible
- Credentials are correct
- Database already exists
- Admin user has required privileges

## Related Files

- `frontend/src/components/Setup/SetupWizard.tsx` - Frontend UI
- `src/api/setup.py` - Backend setup API
- `docker-compose.saas.yml` - Docker configuration
- `docs/SAAS_DEPLOYMENT.md` - Full SaaS deployment guide
