# Production Deployment Guide

**多模输入灵感记录器 (Multimodal Inspiration Recorder) - Backend**

Version: 1.0.0
Last Updated: 2025-10-29

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Deployment Options](#deployment-options)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Database Setup](#database-setup)
7. [Health Checks](#health-checks)
8. [Monitoring & Logging](#monitoring--logging)
9. [Security Hardening](#security-hardening)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### Critical Requirements

Run the deployment readiness script:

```bash
cd backend
python scripts/deployment_checklist.py
```

This script validates:

- ✅ Environment variables are set correctly
- ✅ Configuration files exist
- ✅ Database migrations are ready
- ✅ Tests are in place
- ✅ Security settings are correct
- ✅ Logging is configured
- ✅ Dependencies are pinned

**⚠️ DO NOT DEPLOY if the script shows any FAILED checks!**

### Manual Verification

- [ ] All API keys are set with production values
- [ ] `SECRET_KEY` is at least 32 characters
- [ ] `DEBUG=false` in production config
- [ ] CORS origins are restricted (no `*`)
- [ ] SSL/TLS certificates are installed
- [ ] Database backups are configured
- [ ] Monitoring dashboards are set up
- [ ] Error tracking (Sentry) is configured
- [ ] Log aggregation is working
- [ ] Security headers are enabled

---

## Environment Setup

### 1. Create Production Environment File

```bash
cd backend
cp .env.production.example .env.production
chmod 600 .env.production  # Restrict file permissions
```

### 2. Configure Required Secrets

Edit `.env.production` and set:

```bash
# CRITICAL: Generate secure random values
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# API Keys (required)
OPENAI_API_KEY=sk-your-real-key
DEEPGRAM_API_KEY=your-deepgram-key
NOTION_API_KEY=secret_your-notion-key
NOTION_DATABASE_ID=your-database-id

# Monitoring (recommended)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
```

### 3. Verify Configuration

```bash
python -c "from src.config.production import get_production_config; print(get_production_config())"
```

---

## Deployment Options

### Option A: Docker Compose (Recommended for Simple Deployments)

Best for:
- Single-server deployments
- Development staging environments
- Small to medium traffic

### Option B: Kubernetes (Recommended for Production)

Best for:
- Multi-server deployments
- High availability requirements
- Auto-scaling needs
- Large traffic volumes

### Option C: Manual Deployment

Best for:
- Custom infrastructure
- Specific compliance requirements
- Advanced customization

---

## Docker Deployment

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 2GB RAM minimum
- 10GB disk space

### Step 1: Build and Start Services

```bash
# Set environment variables
export SECRET_KEY="your-secure-secret-key"
export OPENAI_API_KEY="sk-your-key"
export DEEPGRAM_API_KEY="your-key"
export NOTION_API_KEY="secret_your-key"
export NOTION_DATABASE_ID="your-db-id"
export SENTRY_DSN="https://your-dsn@sentry.io/project"
export CORS_ORIGINS="https://yourdomain.com"

# Start services
docker-compose up -d
```

### Step 2: Run Database Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Step 3: Verify Deployment

```bash
# Check service health
curl http://localhost:8000/api/v1/health/readiness

# Check logs
docker-compose logs -f backend
```

### Step 4: Enable Monitoring (Optional)

```bash
# Start Prometheus and Grafana
docker-compose --profile monitoring up -d
```

Access Grafana at: http://localhost:3000 (admin/admin)

### Docker Commands Reference

```bash
# View logs
docker-compose logs -f [service-name]

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and restart
docker-compose pull
docker-compose up -d

# View resource usage
docker stats

# Execute commands in container
docker-compose exec backend python -m scripts.deployment_checklist
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)
- Persistent volume provisioner

### Step 1: Create Namespace

```bash
kubectl create namespace inspiration-recorder
```

### Step 2: Configure Secrets

```bash
kubectl create secret generic app-secrets \
  --from-literal=SECRET_KEY="your-secret-key" \
  --from-literal=OPENAI_API_KEY="sk-your-key" \
  --from-literal=DEEPGRAM_API_KEY="your-key" \
  --from-literal=NOTION_API_KEY="secret_your-key" \
  --from-literal=NOTION_DATABASE_ID="your-db-id" \
  --from-literal=SENTRY_DSN="https://your-dsn@sentry.io/project" \
  -n inspiration-recorder
```

### Step 3: Deploy Application

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inspiration-recorder-backend
  namespace: inspiration-recorder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inspiration-recorder-backend
  template:
    metadata:
      labels:
        app: inspiration-recorder-backend
    spec:
      containers:
      - name: backend
        image: your-registry/inspiration-recorder-backend:1.0.0
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: app-secrets
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DEBUG
          value: "false"
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        livenessProbe:
          httpGet:
            path: /api/v1/health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health/readiness
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /api/v1/health/startup
            port: 8000
          failureThreshold: 30
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

```bash
kubectl apply -f deployment.yaml
```

### Step 4: Create Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: inspiration-recorder-service
  namespace: inspiration-recorder
spec:
  selector:
    app: inspiration-recorder-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

```bash
kubectl apply -f service.yaml
```

### Step 5: Configure Ingress (Optional)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: inspiration-recorder-ingress
  namespace: inspiration-recorder
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: inspiration-recorder-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: inspiration-recorder-service
            port:
              number: 80
```

```bash
kubectl apply -f ingress.yaml
```

---

## Database Setup

### SQLite Configuration (Default)

```bash
# Enable WAL mode for better concurrent access
sqlite3 data/production.db "PRAGMA journal_mode=WAL;"
sqlite3 data/production.db "PRAGMA synchronous=NORMAL;"
sqlite3 data/production.db "PRAGMA cache_size=2000;"

# Run migrations
alembic upgrade head
```

### PostgreSQL Migration (Optional for Scale)

For high-traffic production, consider PostgreSQL:

```bash
# Update DATABASE_URL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/inspiration_recorder

# Run migrations
alembic upgrade head
```

### Database Backup

```bash
# SQLite backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 data/production.db ".backup 'backups/backup_${DATE}.db'"

# Keep last 30 days
find backups/ -name "backup_*.db" -mtime +30 -delete
```

Set up cron job:

```bash
0 2 * * * /path/to/backup-script.sh
```

---

## Health Checks

### Available Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/api/v1/health/` | Basic health | Simple alive check |
| `/api/v1/health/liveness` | Liveness probe | Kubernetes liveness |
| `/api/v1/health/readiness` | Readiness probe | Kubernetes readiness |
| `/api/v1/health/startup` | Startup probe | Kubernetes startup |
| `/api/v1/health/detailed` | Detailed status | Monitoring dashboards |

### Testing Health Checks

```bash
# Basic health
curl http://localhost:8000/api/v1/health/

# Readiness (returns 503 if not ready)
curl -f http://localhost:8000/api/v1/health/readiness

# Detailed health with metrics
curl http://localhost:8000/api/v1/health/detailed | jq
```

### Load Balancer Configuration

Configure health checks:
- **Path**: `/api/v1/health/readiness`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Healthy threshold**: 2 consecutive successes
- **Unhealthy threshold**: 3 consecutive failures

---

## Monitoring & Logging

### Metrics Collection

Prometheus metrics available at: `/metrics`

Key metrics:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `db_connection_pool_size` - Database connections
- `task_queue_length` - Background tasks pending

### Sentry Error Tracking

Configure Sentry DSN in `.env.production`:

```bash
SENTRY_DSN=https://your-key@sentry.io/project
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Log Aggregation

Logs are written in JSON format for easy parsing:

```json
{
  "timestamp": "2025-10-29T12:00:00Z",
  "level": "INFO",
  "logger": "api",
  "message": "Request completed",
  "request_id": "abc-123",
  "duration_ms": 45
}
```

Recommended log aggregation tools:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **CloudWatch Logs** (AWS)
- **Cloud Logging** (GCP)

---

## Security Hardening

### 1. HTTPS Configuration

**Required for production!** Use Let's Encrypt or commercial SSL certificate.

Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Security Headers

Already configured in `security.py` middleware:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### 3. Rate Limiting

Configured in production config:
- 100 requests per minute per IP
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`

### 4. Input Validation

All endpoints use Pydantic models for strict validation.

### 5. SQL Injection Protection

SQLAlchemy ORM protects against SQL injection automatically.

---

## Backup & Recovery

### Backup Strategy

**Daily backups:**
- Database: SQLite backup at 2 AM daily
- Uploads: Sync to S3 or equivalent
- Logs: Aggregate and archive weekly

**Retention policy:**
- Daily backups: 30 days
- Weekly backups: 90 days
- Monthly backups: 1 year

### Disaster Recovery

```bash
# Restore from backup
cp backups/backup_20251029.db data/production.db

# Restart services
docker-compose restart backend

# Verify restoration
curl http://localhost:8000/api/v1/health/detailed
```

**Recovery Time Objective (RTO):** < 1 hour
**Recovery Point Objective (RPO):** < 24 hours

---

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Missing environment variables
# - Invalid SECRET_KEY
# - Database connection failed
# - Redis unavailable
```

#### 2. Health Check Failing

```bash
# Check readiness endpoint
curl -v http://localhost:8000/api/v1/health/readiness

# If database error:
docker-compose exec backend alembic current
docker-compose exec backend alembic upgrade head
```

#### 3. High Memory Usage

```bash
# Check container stats
docker stats

# Reduce worker count
WORKERS=2 docker-compose up -d
```

#### 4. Slow Response Times

```bash
# Check detailed health
curl http://localhost:8000/api/v1/health/detailed | jq

# Enable database query logging
DATABASE_ECHO=true
```

#### 5. Sync Issues

```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Check sync queue
curl http://localhost:8000/api/v1/sync/status
```

### Performance Tuning

**Database optimization:**
```bash
# Optimize SQLite
sqlite3 data/production.db "PRAGMA optimize;"
sqlite3 data/production.db "VACUUM;"
```

**Worker scaling:**
```bash
# Scale ARQ workers
docker-compose up -d --scale worker=3
```

**Connection pooling:**
```bash
# Increase pool size
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=60
```

---

## Support

### Getting Help

- **Issues**: https://github.com/yourusername/inspiration-recorder/issues
- **Documentation**: https://docs.yourdomain.com
- **Email**: support@yourdomain.com

### Emergency Contacts

- On-call engineer: [Contact Info]
- DevOps team: [Contact Info]
- Security team: [Contact Info]

---

## Appendix

### Deployment Checklist Summary

```bash
# Run this before every deployment
python scripts/deployment_checklist.py

# Expected output: "✓ READY FOR DEPLOYMENT"
```

### Environment Variables Reference

See `.env.production.example` for complete list.

### API Documentation

Available at `/docs` (disable in production: `DOCS_ENABLED=false`)

### Version History

- **1.0.0** (2025-10-29) - Initial production release
  - Multimodal input support (voice, image, text)
  - Offline-first architecture
  - Notion synchronization
  - Production-ready configuration

---

**Last Updated**: 2025-10-29
**Maintained By**: DevOps Team
**Review Schedule**: Quarterly
