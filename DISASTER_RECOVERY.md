# AttendAI Disaster Recovery Plan

## Overview

This document provides comprehensive disaster recovery procedures for the AttendAI platform. It covers backup strategies, restore procedures, and recovery from common failure scenarios.

**Last Updated**: 2026-09-22  
**Version**: 1.0  
**Applicable To**: Production deployments

---

## Table of Contents

1. [What Must Be Backed Up](#what-must-be-backed-up)
2. [Backup Procedures](#backup-procedures)
3. [Restore Order](#restore-order)
4. [Migration Considerations](#migration-considerations)
5. [Redis/RQ Recovery](#redisrq-recovery)
6. [Secret/Config Recovery](#secretconfig-recovery)
7. [Application Restart Order](#application-restart-order)
8. [Post-Restore Verification](#post-restore-verification)
9. [Common Failure Scenarios](#common-failure-scenarios)
10. [Contact Information](#contact-information)

---

## What Must Be Backed Up

### Critical Data (Must Backup)

1. **PostgreSQL Database**
   - All application data (students, parents, attendance, calls, reports)
   - User accounts and authentication data
   - Audit logs
   - Configuration data
   - **Backup Frequency**: Daily
   - **Retention**: 7 days (daily), 30 days (weekly)

2. **Environment Configuration**
   - `.env.prod` file (production secrets)
   - Vapi API credentials
   - LLM provider API keys
   - JWT secrets
   - **Backup Frequency**: On change
   - **Retention**: Indefinite (encrypted)

3. **Application Code**
   - Git repository (already versioned)
   - **Backup Frequency**: Continuous (Git)
   - **Retention**: Full history

### Optional Data (Nice to Have)

1. **Redis Data**
   - RQ job queues (can be recreated)
   - Rate limiting counters (reset on restart)
   - **Backup Frequency**: Not required
   - **Note**: Redis is used for transient data only

2. **Application Logs**
   - Operational logs (can be regenerated)
   - **Backup Frequency**: Optional (for audit)
   - **Retention**: 30 days

---

## Backup Procedures

### Database Backup

**Automated Backup Script**:
```bash
./scripts/backup/backup_database.sh
```

**Manual Backup**:
```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=attendai_db
export POSTGRES_USER=attendai
export POSTGRES_PASSWORD=your_password

# Create backup
pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER \
  -d $POSTGRES_DB --format=plain | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

**Backup Verification**:
```bash
# List backups
ls -lh backups/

# Verify backup integrity
gunzip -t backups/attendai_backup_20260922_120000.sql.gz
```

### Environment Backup

**Backup `.env.prod`**:
```bash
# Copy to secure location
cp .env.prod /secure/backup/attendai-env-$(date +%Y%m%d).bak

# Encrypt before storing
gpg -c .env.prod
# Store .env.prod.gpg in secure location
```

**Backup Secrets to Vault** (recommended):
```bash
# Store in HashiCorp Vault, AWS Secrets Manager, or similar
vault kv put secret/attendai @.env.prod
```

### Scheduled Backups (Cron)

**Daily backup with 7-day retention**:
```bash
# Edit crontab
crontab -e

# Add line:
0 2 * * * cd /opt/attendai && ./scripts/backup/backup_database.sh --keep-days 7 >> /var/log/attendai-backup.log 2>&1
```

**Weekly backup with 30-day retention**:
```bash
# Add line:
0 3 * * 0 cd /opt/attendai && ./scripts/backup/backup_database.sh --keep-days 30 >> /var/log/attendai-backup.log 2>&1
```

### Offsite Backup

**Sync to S3**:
```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Sync backups
aws s3 sync ./backups/ s3://your-backup-bucket/attendai/
```

**Sync to Remote Server**:
```bash
# Using rsync
rsync -avz ./backups/ user@backup-server:/backups/attendai/

# Using scp
scp backups/*.sql.gz user@backup-server:/backups/attendai/
```

---

## Restore Order

When recovering from a disaster, follow this order:

### 1. Infrastructure Recovery

```bash
# 1. Provision new server (if needed)
# 2. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Clone repository
git clone https://github.com/abhi-19-09-2006/AttendAI.git
cd AttendAI
```

### 2. Configuration Recovery

```bash
# 1. Restore .env.prod from backup
cp /secure/backup/attendai-env-YYYYMMDD.bak .env.prod

# Or decrypt if encrypted
gpg -d .env.prod.gpg > .env.prod

# 2. Verify configuration
cat .env.prod | grep -E "^(SECRET_KEY|DATABASE_URL|VAPI_API_KEY)"
```

### 3. Database Recovery

```bash
# 1. Start PostgreSQL only
docker-compose -f docker-compose.prod.yml up -d postgres

# 2. Wait for PostgreSQL to be ready
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# 3. Restore database from backup
./scripts/backup/restore_database.sh backups/attendai_backup_YYYYMMDD_HHMMSS.sql.gz

# 4. Verify restore
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U attendai -d attendai_db -c "SELECT COUNT(*) FROM students;"
```

### 4. Application Recovery

```bash
# 1. Start Redis
docker-compose -f docker-compose.prod.yml up -d redis

# 2. Start backend (migrations run automatically)
docker-compose -f docker-compose.prod.yml up -d backend

# 3. Start worker
docker-compose -f docker-compose.prod.yml up -d worker

# 4. Start frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

### 5. Verification

```bash
# 1. Check health
curl http://localhost:8000/health/detailed

# 2. Run smoke tests
./scripts/smoke_test.sh

# 3. Verify data integrity
curl http://localhost:8000/api/students \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Migration Considerations

### Before Migration

```bash
# 1. Backup database
./scripts/backup/backup_database.sh

# 2. Check current migration state
alembic current

# 3. Review pending migrations
alembic history --verbose
```

### During Migration

```bash
# 1. Stop application (optional, for safety)
docker-compose -f docker-compose.prod.yml stop backend worker

# 2. Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 3. Verify migration success
docker-compose -f docker-compose.prod.yml run --rm backend alembic current

# 4. Restart application
docker-compose -f docker-compose.prod.yml start backend worker
```

### Migration Failure Recovery

```bash
# 1. Stop application
docker-compose -f docker-compose.prod.yml down

# 2. Restore database from backup
./scripts/backup/restore_database.sh backups/attendai_backup_YYYYMMDD_HHMMSS.sql.gz

# 3. Identify failed migration
alembic history --verbose

# 4. Fix migration issue (if code problem)
# Edit migration file or application code

# 5. Retry migration
alembic upgrade head

# 6. Restart application
docker-compose -f docker-compose.prod.yml up -d
```

---

## Redis/RQ Recovery

### Redis Failure

**Symptoms**:
- Health check shows Redis unhealthy
- Background jobs not processing
- Rate limiting not working

**Recovery**:
```bash
# 1. Restart Redis
docker-compose -f docker-compose.prod.yml restart redis

# 2. Verify Redis health
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 3. Check RQ workers
docker-compose -f docker-compose.prod.yml logs worker
```

**Data Loss Impact**:
- Pending jobs in queue: **Lost** (must be recreated)
- Rate limiting counters: **Reset** (acceptable)
- Cached data: **Lost** (regenerated on demand)

### RQ Worker Failure

**Symptoms**:
- Jobs not processing
- Queue depth increasing
- Worker health check fails

**Recovery**:
```bash
# 1. Check worker logs
docker-compose -f docker-compose.prod.yml logs worker

# 2. Restart worker
docker-compose -f docker-compose.prod.yml restart worker

# 3. Verify worker is active
curl http://localhost:8000/health/detailed | grep rq_workers
```

**Failed Jobs**:
```bash
# View failed jobs (requires RQ dashboard or CLI)
docker-compose -f docker-compose.prod.yml exec worker \
  python -c "from rq import Queue; from redis import Redis; q = Queue('failed', connection=Redis.from_url('redis://redis:6379/0')); print(f'Failed jobs: {len(q)}')"
```

---

## Secret/Config Recovery

### Lost `.env.prod` File

**Recovery Steps**:
1. Retrieve from backup location
2. Decrypt if encrypted
3. Restore to application directory
4. Restart services

```bash
# 1. Copy from backup
cp /secure/backup/attendai-env-YYYYMMDD.bak .env.prod

# 2. Or decrypt
gpg -d /secure/backup/.env.prod.gpg > .env.prod

# 3. Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Compromised Secrets

**If secrets are compromised**:

1. **Generate new secrets**:
```bash
openssl rand -hex 32  # New SECRET_KEY
openssl rand -hex 32  # New JWT_SECRET_KEY
openssl rand -hex 32  # New VAPI_WEBHOOK_SECRET
```

2. **Update `.env.prod`**:
```bash
nano .env.prod
# Replace compromised secrets with new values
```

3. **Restart services**:
```bash
docker-compose -f docker-compose.prod.yml restart
```

4. **Invalidate all tokens**:
- All users must re-authenticate
- All refresh tokens are invalidated
- API keys must be regenerated

5. **Rotate external credentials**:
- Vapi API key (via Vapi dashboard)
- OpenAI API key (via OpenAI dashboard)
- Database password (via PostgreSQL)

---

## Application Restart Order

### Full Restart

```bash
# 1. Stop all services
docker-compose -f docker-compose.prod.yml down

# 2. Start in order
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10  # Wait for PostgreSQL
docker-compose -f docker-compose.prod.yml up -d redis
sleep 5   # Wait for Redis
docker-compose -f docker-compose.prod.yml up -d backend
sleep 10  # Wait for backend
docker-compose -f docker-compose.prod.yml up -d worker
docker-compose -f docker-compose.prod.yml up -d frontend
```

### Partial Restart (Single Service)

```bash
# Restart backend only
docker-compose -f docker-compose.prod.yml restart backend

# Restart worker only
docker-compose -f docker-compose.prod.yml restart worker

# Restart frontend only
docker-compose -f docker-compose.prod.yml restart frontend
```

### Emergency Restart (All Services)

```bash
# Force restart all services
docker-compose -f docker-compose.prod.yml restart
```

---

## Post-Restore Verification

### Health Checks

```bash
# 1. Basic health
curl http://localhost:8000/health

# 2. Detailed health
curl http://localhost:8000/health/detailed

# 3. Verify all services healthy
curl -s http://localhost:8000/health/detailed | jq '.services'
```

### Smoke Tests

```bash
# Run comprehensive smoke tests
./scripts/smoke_test.sh
```

### Data Integrity Checks

```bash
# 1. Verify student count
curl -s http://localhost:8000/api/students \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.length'

# 2. Verify recent calls
curl -s http://localhost:8000/api/calls \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.[0:5]'

# 3. Verify attendance records
curl -s http://localhost:8000/api/attendance \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.length'
```

### Functional Tests

```bash
# 1. Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"your-password"}'

# 2. Test API endpoints
curl http://localhost:8000/api/students \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Test webhook endpoint
curl http://localhost:8000/webhooks/vapi/test
```

---

## Common Failure Scenarios

### Scenario 1: Database Corruption

**Symptoms**:
- Application errors on database queries
- Health check shows database unhealthy
- PostgreSQL logs show corruption errors

**Recovery**:
```bash
# 1. Stop application
docker-compose -f docker-compose.prod.yml down

# 2. Restore from most recent backup
./scripts/backup/restore_database.sh backups/attendai_backup_YYYYMMDD_HHMMSS.sql.gz

# 3. Start application
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify health
curl http://localhost:8000/health/detailed
```

**Data Loss**: All data since last backup

### Scenario 2: Disk Full

**Symptoms**:
- Application crashes
- Database cannot write
- Logs show "No space left on device"

**Recovery**:
```bash
# 1. Check disk usage
df -h

# 2. Clean up old backups
find ./backups -name "*.sql.gz" -mtime +30 -delete

# 3. Clean up Docker images
docker system prune -a

# 4. Clean up logs
docker-compose -f docker-compose.prod.yml logs --tail=1000 > logs.txt
docker-compose -f docker-compose.prod.yml logs --no-log-prefix

# 5. Expand disk (if cloud provider)
# Follow cloud provider documentation
```

### Scenario 3: Out of Memory

**Symptoms**:
- Containers killed by OOM killer
- Application crashes
- Docker logs show "OOMKilled"

**Recovery**:
```bash
# 1. Check memory usage
docker stats

# 2. Restart services
docker-compose -f docker-compose.prod.yml restart

# 3. If persistent, increase memory limits
# Edit docker-compose.prod.yml
# Increase memory limits in deploy.resources

# 4. Restart with new limits
docker-compose -f docker-compose.prod.yml up -d
```

### Scenario 4: Network Connectivity Loss

**Symptoms**:
- Cannot access application
- Health checks fail
- Vapi webhooks not received

**Recovery**:
```bash
# 1. Check network connectivity
ping 8.8.8.8
curl https://api.vapi.ai

# 2. Check firewall rules
sudo ufw status
sudo iptables -L

# 3. Check DNS resolution
nslookup api.vapi.ai

# 4. Restart network services
sudo systemctl restart networking

# 5. If cloud provider, check security groups/firewall rules
```

### Scenario 5: Vapi Integration Failure

**Symptoms**:
- Calls not initiated
- Webhooks not received
- Vapi health check shows "pending"

**Recovery**:
```bash
# 1. Verify Vapi credentials
grep VAPI_API_KEY .env.prod
grep VAPI_WEBHOOK_SECRET .env.prod

# 2. Test Vapi API
curl -H "Authorization: Bearer ${VAPI_API_KEY}" \
  https://api.vapi.ai/call

# 3. Check webhook URL configuration
# Verify webhook URL in Vapi dashboard points to your server

# 4. Check firewall allows incoming webhooks
sudo ufw allow from api.vapi.ai to any port 443

# 5. Restart backend
docker-compose -f docker-compose.prod.yml restart backend
```

### Scenario 6: SSL Certificate Expired

**Symptoms**:
- Browser shows security warning
- API calls fail with SSL errors
- Webhooks rejected

**Recovery**:
```bash
# 1. Renew certificate
# Follow your certificate provider's renewal process

# 2. Update certificate files
cp new-cert.pem /etc/ssl/certs/attendai.crt
cp new-key.pem /etc/ssl/private/attendai.key

# 3. Restart web server/load balancer
sudo systemctl restart nginx
# or
docker-compose -f docker-compose.prod.yml restart frontend
```

---

## Contact Information

### Internal Contacts

**DevOps Team**:
- Name: [DevOps Lead Name]
- Email: [devops@yourcompany.com]
- Phone: [+1-xxx-xxx-xxxx]
- Slack: #devops-alerts

**Database Administrator**:
- Name: [DBA Name]
- Email: [dba@yourcompany.com]
- Phone: [+1-xxx-xxx-xxxx]

**Application Developer**:
- Name: [Lead Developer Name]
- Email: [dev@yourcompany.com]
- Phone: [+1-xxx-xxx-xxxx]

### External Contacts

**Cloud Provider Support**:
- AWS: https://console.aws.amazon.com/support
- GCP: https://cloud.google.com/support
- Azure: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade

**Vapi Support**:
- Email: support@vapi.ai
- Dashboard: https://dashboard.vapi.ai/support
- Documentation: https://docs.vapi.ai

**OpenAI Support**:
- Help Center: https://help.openai.com
- Community: https://community.openai.com

### Escalation Procedures

**Severity 1 (Complete Outage)**:
1. Page DevOps on-call immediately
2. Notify engineering leadership
3. Begin recovery procedures
4. Update status page
5. Communicate with stakeholders

**Severity 2 (Partial Outage)**:
1. Notify DevOps team via Slack
2. Begin diagnosis
3. Implement fix or workaround
4. Monitor for recurrence

**Severity 3 (Degraded Performance)**:
1. Log incident in tracking system
2. Schedule investigation
3. Implement monitoring
4. Plan remediation

---

## Appendix: Quick Reference Card

### Emergency Contacts
- DevOps: [phone]
- DBA: [phone]
- Vapi Support: support@vapi.ai

### Critical Commands
```bash
# Stop everything
docker-compose -f docker-compose.prod.yml down

# Start everything
docker-compose -f docker-compose.prod.yml up -d

# Backup database
./scripts/backup/backup_database.sh

# Restore database
./scripts/backup/restore_database.sh backups/file.sql.gz

# Check health
curl http://localhost:8000/health/detailed

# Run smoke tests
./scripts/smoke_test.sh

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Backup Locations
- Local: `./backups/`
- Offsite: `s3://your-backup-bucket/attendai/`
- Secrets: `/secure/backup/`

### Important URLs
- Health: http://localhost:8000/health/detailed
- Docs: http://localhost:8000/docs
- Vapi Dashboard: https://dashboard.vapi.ai
- OpenAI Dashboard: https://platform.openai.com

---

## Document Maintenance

**Review Schedule**: Quarterly  
**Last Reviewed**: 2026-09-22  
**Next Review**: 2026-12-22

**Change Log**:
- 2026-09-22: Initial version (v1.0)

**Approved By**: [CTO/Engineering Lead Name]
