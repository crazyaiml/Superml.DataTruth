# Security Hardening Guide

This guide provides comprehensive security best practices for deploying DataTruth in production.

## Table of Contents

- [Pre-Production Security Checklist](#pre-production-security-checklist)
- [Authentication and Authorization](#authentication-and-authorization)
- [Database Security](#database-security)
- [API Security](#api-security)
- [Network Security](#network-security)
- [Data Protection](#data-protection)
- [Monitoring and Logging](#monitoring-and-logging)
- [Incident Response](#incident-response)

## Pre-Production Security Checklist

Before deploying to production, ensure all items are completed:

### Critical (Must Do)
- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Restrict CORS origins to your domain only
- [ ] Disable DEBUG mode in production
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable rate limiting
- [ ] Review and restrict file permissions
- [ ] Set secure password policy

### Recommended
- [ ] Enable database encryption at rest
- [ ] Set up WAF (Web Application Firewall)
- [ ] Configure log monitoring and alerts
- [ ] Implement IP whitelisting for admin access
- [ ] Set up VPN for database access
- [ ] Enable MFA for admin accounts
- [ ] Regular security scanning
- [ ] Penetration testing

## Authentication and Authorization

### Password Security

**1. Change Default Passwords**

```bash
# Default users (CHANGE IMMEDIATELY!)
# admin / admin123
# analyst / analyst123

# Login and change passwords via API:
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Change password
curl -X PUT http://localhost:8000/api/v1/users/me/password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "admin123",
    "new_password": "YourStr0ng!P@ssw0rd"
  }'
```

**2. Password Requirements**

Configure in `.env`:
```bash
# Minimum password length
PASSWORD_MIN_LENGTH=12

# Password complexity requirements
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=true

# Password expiration (days)
PASSWORD_EXPIRATION_DAYS=90

# Failed login lockout
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
```

**3. JWT Token Security**

```bash
# Generate strong secret keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Add to .env
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env

# Token expiration
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Role-Based Access Control (RBAC)

**User Roles:**
- **Admin**: Full system access
- **Analyst**: Query and create metrics
- **Viewer**: Read-only access

**Best Practices:**
- Use least privilege principle
- Regularly audit user permissions
- Remove unused accounts
- Implement periodic access reviews

## Database Security

### PostgreSQL Security

**1. Strong Passwords**

```bash
# Generate strong database passwords
INTERNAL_DB_PASSWORD=$(openssl rand -base64 32)
INTERNAL_DB_ADMIN_PASSWORD=$(openssl rand -base64 32)

# Update .env
sed -i "s/INTERNAL_DB_PASSWORD=.*/INTERNAL_DB_PASSWORD=$INTERNAL_DB_PASSWORD/" .env
sed -i "s/INTERNAL_DB_ADMIN_PASSWORD=.*/INTERNAL_DB_ADMIN_PASSWORD=$INTERNAL_DB_ADMIN_PASSWORD/" .env
```

**2. Network Access**

```bash
# Restrict PostgreSQL to local network only
# In docker-compose.prod.yml:
services:
  postgres:
    ports:
      - "127.0.0.1:5432:5432"  # Bind to localhost only
```

**3. Connection Encryption**

Enable SSL for PostgreSQL connections:

```bash
# In .env
INTERNAL_DB_SSL_MODE=require
INTERNAL_DB_SSL_CERT=/path/to/client-cert.pem
INTERNAL_DB_SSL_KEY=/path/to/client-key.pem
INTERNAL_DB_SSL_ROOT_CERT=/path/to/ca-cert.pem
```

**4. Backup Encryption**

Encrypt database backups:

```bash
# Encrypted backup
./bin/backup.sh
openssl enc -aes-256-cbc -salt -pbkdf2 \
  -in backups/datatruth_backup_*.sql.gz \
  -out backups/datatruth_backup_*.sql.gz.enc

# Encrypted restore
openssl enc -aes-256-cbc -d -pbkdf2 \
  -in backups/datatruth_backup_*.sql.gz.enc \
  -out backups/datatruth_backup_*.sql.gz
./bin/restore.sh backups/datatruth_backup_*.sql.gz
```

**5. Audit Logging**

Enable PostgreSQL audit logging:

```sql
-- Enable logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
SELECT pg_reload_conf();
```

## API Security

### HTTPS Configuration

**1. Obtain SSL Certificate**

Using Let's Encrypt:
```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be in:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**2. Configure Nginx for HTTPS**

Update `nginx/nginx.conf`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Strong SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Other security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### CORS Configuration

Restrict CORS to your domain:

```bash
# In .env
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

### Rate Limiting

Enable and configure rate limiting:

```bash
# In .env
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# Stricter limits for auth endpoints
AUTH_RATE_LIMIT_PER_MINUTE=5
AUTH_RATE_LIMIT_PER_HOUR=20
```

### API Key Security

For external integrations:

```bash
# Generate API keys
API_KEY=$(python3 -c "import secrets; print(f'dt_{secrets.token_urlsafe(32)}')")

# Store securely (use secrets manager in production)
# e.g., AWS Secrets Manager, HashiCorp Vault
```

## Network Security

### Firewall Configuration

**Using UFW (Ubuntu):**

```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

**Using iptables:**

```bash
# Flush existing rules
sudo iptables -F

# Default policies
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### VPN Access

For administrative access:

```bash
# Install OpenVPN or WireGuard
# Route admin traffic through VPN only

# Restrict admin endpoints to VPN IP range
# In nginx.conf:
location /admin {
    allow 10.8.0.0/24;  # VPN subnet
    deny all;
    proxy_pass http://api:8000;
}
```

### DDoS Protection

**CloudFlare (Recommended):**
- Enable CloudFlare proxy
- Configure rate limiting rules
- Enable bot protection
- Use page rules for sensitive endpoints

**AWS Shield:**
- Enable AWS Shield Standard (free)
- Consider AWS Shield Advanced for critical apps

## Data Protection

### Sensitive Data Handling

**1. Database Credentials**

Never store database credentials in code:
```python
# ❌ BAD
conn = psycopg2.connect(
    host="localhost",
    password="mypassword"  # Never hardcode!
)

# ✅ GOOD
from src.config import settings
conn = psycopg2.connect(
    host=settings.INTERNAL_DB_HOST,
    password=settings.INTERNAL_DB_PASSWORD
)
```

**2. API Keys**

Protect API keys:
```bash
# Use environment variables
OPENAI_API_KEY=sk-...

# Or use secrets manager
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id datatruth/openai-api-key

# HashiCorp Vault
vault kv get secret/datatruth/openai-api-key
```

**3. Sensitive Data Masking**

Mask sensitive data in logs:
```python
import re

def mask_sensitive_data(text: str) -> str:
    """Mask sensitive data in logs."""
    # Mask API keys
    text = re.sub(r'sk-[a-zA-Z0-9]{48}', 'sk-***', text)
    # Mask passwords
    text = re.sub(r'password["\']:\s*["\'][^"\']+["\']', 'password":"***"', text)
    # Mask tokens
    text = re.sub(r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', 'Bearer ***', text)
    return text
```

### Data Encryption

**1. Encryption at Rest**

Enable disk encryption:
```bash
# Linux: Use LUKS
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup luksOpen /dev/sdX encrypted_volume

# Mount encrypted volume
sudo mount /dev/mapper/encrypted_volume /data
```

**2. Encryption in Transit**

Always use HTTPS for all API calls:
```python
# Force HTTPS
if request.url.scheme != "https" and not settings.DEBUG:
    return RedirectResponse(
        url=request.url.replace(scheme="https")
    )
```

## Monitoring and Logging

### Security Monitoring

**1. Failed Login Attempts**

Monitor and alert on failed logins:
```sql
-- Query failed login attempts
SELECT username, COUNT(*) as failed_attempts, MAX(created_at) as last_attempt
FROM user_activity
WHERE activity_type = 'failed_login'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY username
HAVING COUNT(*) > 5
ORDER BY failed_attempts DESC;
```

**2. Unusual Activity**

Alert on unusual patterns:
- Login from new location/IP
- Bulk data exports
- Multiple failed queries
- Unusual time-of-day access

**3. Log Aggregation**

Use centralized logging:

**ELK Stack:**
```yaml
# docker-compose.prod.yml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
```

**CloudWatch Logs:**
```bash
# Install CloudWatch agent
sudo yum install amazon-cloudwatch-agent

# Configure log streaming
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

### Audit Logging

Log all critical actions:
```python
# Log admin actions
@app.post("/admin/users/{user_id}/delete")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    logger.info(f"Admin {current_user['username']} deleted user {user_id}")
    # ... delete user
```

## Incident Response

### Response Plan

**1. Identify**
- Monitor alerts
- Investigate anomalies
- Confirm incident

**2. Contain**
- Isolate affected systems
- Block malicious IPs
- Revoke compromised credentials

**3. Eradicate**
- Remove malware
- Patch vulnerabilities
- Reset passwords

**4. Recover**
- Restore from backup
- Verify system integrity
- Monitor for recurrence

**5. Learn**
- Document incident
- Update security measures
- Train team

### Emergency Procedures

**Compromised API Key:**
```bash
# 1. Revoke old key
# 2. Generate new key
NEW_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. Update .env
sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$NEW_API_KEY/" .env

# 4. Restart services
docker-compose -f docker-compose.prod.yml restart api

# 5. Notify users if needed
```

**Database Breach:**
```bash
# 1. Immediately change all database passwords
# 2. Rotate encryption keys
# 3. Force password reset for all users
# 4. Review audit logs
# 5. Restore from backup if necessary
```

**DDoS Attack:**
```bash
# 1. Enable CloudFlare "Under Attack" mode
# 2. Implement aggressive rate limiting
# 3. Block attacking IP ranges
sudo ufw deny from 192.168.1.0/24

# 4. Scale up infrastructure if needed
```

### Contact Information

Maintain emergency contacts:
- Security team lead
- System administrator
- Cloud provider support
- Legal/compliance team

---

## Security Checklist

Use this checklist for regular security audits:

### Monthly
- [ ] Review user access and permissions
- [ ] Check for failed login attempts
- [ ] Review audit logs
- [ ] Verify backups are running
- [ ] Update dependencies
- [ ] Scan for vulnerabilities

### Quarterly
- [ ] Rotate passwords
- [ ] Review and update firewall rules
- [ ] Penetration testing
- [ ] Security training for team
- [ ] Review incident response plan
- [ ] Update SSL certificates

### Annually
- [ ] Full security audit
- [ ] Compliance review
- [ ] Disaster recovery drill
- [ ] Review and update security policies
- [ ] Third-party security assessment

---

**Need Help?**

For security concerns or questions:
- Email: security@datatruth.com
- Emergency: +1-XXX-XXX-XXXX
- Bug Bounty: https://datatruth.com/security/bug-bounty
