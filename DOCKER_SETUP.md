# Docker Compose Setup - Gold Tier

Complete Docker Compose configuration for AI Employee Gold Tier with Odoo 19+ ERPintegration.

---

## Quick Start

### 1. Prerequisites

- Docker Desktop 4.0+ or Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available for containers
- Git (for cloning)

### 2. Initial Setup

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

### 3. Start All Services

```bash
# Build and start all containers
docker-compose up -d

# Or without building (uses pre-built images)
docker-compose up -d --no-build
```

### 4. Verify Installation

```bash
# Check all containers are running
docker-compose ps

# View logs
docker-compose logs -f

# Check Odoo is ready
curl http://localhost:8069/web/login
```

---

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| Odoo ERP | 8069 | Odoo 19 Community Edition |
| PostgreSQL | 5432 (internal) | Database for Odoo |
| pgAdmin | 5050 | Database management UI |
| AI Employee | 8080 | Core orchestrator |
| Redis | 6379 (internal) | Task queue and caching |

---

## First Time Odoo Setup

### 1. Create Odoo Database

1. Navigate to http://localhost:8069
2. Click "Create Database"
3. Fill in:
   - **Master Password**: (from .env POSTGRES_PASSWORD)
   - **Database Name**: ai_employee_db (from .env ODOO_DB)
   - **Email**: admin (from .env ODOO_USER)
   - **Password**: (from .env ODOO_ADMIN_PASSWORD)
   - **Phone**: (your number)
   - **Language**: English
   - **Country**: Your country
4. Click "Create database"

### 2. Install Accounting Module

1. Log in to Odoo with admin credentials
2. Go to Apps
3. Search for "Accounting"
4. Install "Accounting" module
5. Configure chart of accounts for your country

### 3. Configure API Access

1. Go to Settings → Users & Companies → Users
2. Click on your admin user
3. Enable "Developer Mode" (top right menu)
4. API Key is now available in user preferences

---

## Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data!)
docker-compose down -v

# Restart a specific service
docker-compose restart ai-employee

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f odoo

# Execute command in container
docker-compose exec ai-employee python orchestrator.py status

# Enter container shell
docker-compose exec ai-employee bash

# Scale AI Employee workers (if using Celery)
docker-compose up -d --scale ai-employee=3
```

---

## Development Mode

Use the override file for development:

```bash
# Automatically loads docker-compose.override.yml
docker-compose up -d

# Live code reloading enabled
# Source code mounted from host
```

### Development Features

- Live code reloading
- Source code mounted as volumes
- Debug ports exposed
- Mailpit for email testing
- Higher log verbosity

---

## Health Checks

Each container has health checks:

| Service | Check | Interval |
|---------|-------|----------|
| Database | pg_isready | 10s |
| Odoo | HTTP /web/login | 30s |
| AI Employee | Python script | 30s |
| Redis | redis-cli ping | 10s |

View health status:
```bash
docker-compose ps
```

---

## Backup & Restore

### Backup Database

```bash
# Backup PostgreSQL
docker-compose exec db pg_dump -U odoo ai_employee_db > backup_$(date +%Y%m%d).sql

# Backup Odoo filestore
docker-compose exec odoo tar czf - /var/lib/odoo > odoo_filestore_$(date +%Y%m%d).tar.gz
```

### Restore Database

```bash
# Restore PostgreSQL
docker-compose exec -T db psql -U odoo postgres < backup_YYYYMMDD.sql

# Restore filestore
docker-compose exec -T odoo tar xzf - /var/lib/odoo < odoo_filestore_YYYYMMDD.tar.gz
```

---

## Troubleshooting

### Odoo won't start

```bash
# Check database connection
docker-compose logs db

# Verify network
docker network inspect ai_employee_gold_ai_employee_network

# Reset database (WARNING: deletes data!)
docker-compose down -v
docker-compose up -d db
docker-compose up -d odoo
```

### Permission issues on Windows

```bash
# Fix file permissions in WSL2
sudo chown -R 1000:1000 AI_Employee_Vault/
sudo chmod -R 755 AI_Employee_Vault/
```

### Port conflicts

```bash
# Check what's using port 8069
netstat -ano | findstr 8069

# Change ports in .env
ODOO_PORT=8070
```

---

## Environment Variables

See `.env.example` for all available options.

Key variables:
- `ODOO_ADMIN_PASSWORD` - Odoo admin password
- `POSTGRES_PASSWORD` - Database password
- `FACEBOOK_ACCESS_TOKEN` - Facebook Graph API
- `RALPH_MAX_ITERATIONS` - Autonomous loop limit

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │   Odoo 19    │◄────┤  PostgreSQL  │     │   pgAdmin    │ │
│  │    :8069     │     │    :5432     │     │    :5050     │ │
│  └──────┬───────┘     └──────────────┘     └──────────────┘ │
│         │                                                    │
│         │ JSON-RPC                                           │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  AI Employee Core                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │  Ralph   │  │  Multi   │  │  MCP Registry    │   │   │
│  │  │  Loop    │  │  MCP     │  │  (Odoo/Social)   │   │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │   │
│  │                                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │   │
│  │  │  Audit   │  │  Error   │  │  CEO Briefing    │ │   │
│  │  │  Logger  │  │  Recovery│  │  Generator       │ │   │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │    Redis     │     │   Mailpit    │                     │
│  │    :6379     │     │   :8025      │                     │
│  └──────────────┘     └──────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

After Docker is running:

1. Initialize Odoo database
2. Configure Facebook/Instagram tokens
3. Start implementing Phase 2 (Odoo MCP)
4. Test Ralph Wiggum Loop

See `GOLD_TIER_PLAN.md` for complete implementation guide.

---

## Security Notes

- Change default passwords in .env
- Never commit .env to git
- Use strong secrets for ODOO_ADMIN_PASSWORD
- Enable HTTPS for production (use reverse proxy)
- Regularly update Docker images

---

*Gold Tier Docker Setup - Version 1.0*