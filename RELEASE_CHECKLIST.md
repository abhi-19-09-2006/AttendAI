# AttendAI Release Checklist

**Version**: 1.0  
**Last Updated**: 2026-09-22  
**Applicable To**: All production and staging releases

---

## Pre-Release Checks

### Code Quality

- [ ] All backend tests pass (152/152)
  ```bash
  cd backend && pytest tests/ -v
  ```

- [ ] All frontend tests pass
  ```bash
  cd frontend && npm run lint && npm run type-check && npm run build
  ```

- [ ] No uncommitted changes
  ```bash
  git status
  ```

- [ ] All changes committed with clear messages
  ```bash
  git log --oneline -10
  ```

- [ ] Branch is up to date with main
  ```bash
  git fetch origin && git log HEAD..origin/main
  ```

### Release Validation

- [ ] Release validation script passes
  ```bash
  ./scripts/release_validation.sh
  ```

- [ ] Production configuration validation works
  ```bash
  # Test with production environment
  APP_ENV=production python -c "from app.core.production_validation import validate_startup; validate_startup()"
  ```

- [ ] No hardcoded secrets in code
  ```bash
  grep -r "password.*=" backend/app --include="*.py" | grep -v test | grep -v example
  ```

- [ ] No .env files committed
  ```bash
  git ls-files | grep "\.env$" | grep -v example
  ```

### Database

- [ ] Migration chain is intact
  ```bash
  cd backend && alembic history --verbose
  ```

- [ ] Current migration state verified
  ```bash
  cd backend && alembic current
  ```

- [ ] Migrations tested on staging database
  ```bash
  cd backend && alembic upgrade head
  ```

### Docker

- [ ] Docker Compose configuration is valid
  ```bash
  docker-compose config
  docker-compose -f docker-compose.prod.yml config
  docker-compose -f docker-compose.staging.yml config
  ```

- [ ] Docker images build successfully
  ```bash
  docker-compose -f docker-compose.prod.yml build
  ```

### Documentation

- [ ] CHANGELOG updated (if applicable)
- [ ] README updated (if applicable)
- [ ] API documentation current
- [ ] Deployment procedures documented

---

## Staging Deployment

### Pre-Deployment

- [ ] Staging environment configured
  ```bash
  cp .env.staging.example .env.staging
  nano .env.staging  # Fill in staging values
  ```

- [ ] Staging database created
  ```bash
  # Via Docker Compose or cloud provider
  ```

- [ ] Staging secrets configured
  - [ ] SECRET_KEY (32+ chars)
  - [ ] JWT_SECRET_KEY (32+ chars)
  - [ ] VAPI_API_KEY (staging credentials)
  - [ ] VAPI_WEBHOOK_SECRET (32+ chars)
  - [ ] OPENAI_API_KEY (staging credentials)
  - [ ] Database password (strong)

### Deployment Steps

- [ ] Build staging images
  ```bash
  docker-compose -f docker-compose.staging.yml build
  ```

- [ ] Start staging services
  ```bash
  docker-compose -f docker-compose.staging.yml up -d
  ```

- [ ] Wait for services to be healthy
  ```bash
  docker-compose -f docker-compose.staging.yml ps
  ```

- [ ] Run migrations (automatic on startup)
  ```bash
  docker-compose -f docker-compose.staging.yml logs backend | grep -i migration
  ```

### Post-Deployment Verification

- [ ] Health endpoint responds
  ```bash
  curl http://localhost:8001/health
  ```

- [ ] Detailed health shows all services healthy
  ```bash
  curl http://localhost:8001/health/detailed
  ```

- [ ] Database connectivity verified
  ```bash
  curl http://localhost:8001/health/detailed | grep database
  ```

- [ ] Redis connectivity verified
  ```bash
  curl http://localhost:8001/health/detailed | grep redis
  ```

- [ ] RQ workers active
  ```bash
  curl http://localhost:8001/health/detailed | grep rq_workers
  ```

- [ ] Smoke tests pass
  ```bash
  ./scripts/smoke_test.sh --base-url http://localhost:8001
  ```

- [ ] Frontend accessible
  ```bash
  curl http://localhost:3001
  ```

### Staging Validation

- [ ] Authentication works
  ```bash
  curl -X POST http://localhost:8001/api/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"staging-password"}'
  ```

- [ ] API endpoints respond
  ```bash
  curl http://localhost:8001/api/students \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```

- [ ] Webhook endpoint accessible
  ```bash
  curl http://localhost:8001/webhooks/vapi/test
  ```

- [ ] Vapi staging test (if credentials available)
  ```bash
  export STAGING_TEST_NUMBER="+1234567890"
  export AUTH_TOKEN="your-staging-token"
  ./scripts/vapi_staging_test.sh --base-url http://localhost:8001
  ```

---

## Production Deployment

### Pre-Deployment

- [ ] Staging validation complete (all checks above)
- [ ] Production backup created
  ```bash
  ./scripts/backup/backup_database.sh
  ```

- [ ] Rollback plan documented
- [ ] Deployment window scheduled
- [ ] Stakeholders notified
- [ ] Monitoring alerts configured

### Production Configuration

- [ ] Production environment configured
  ```bash
  cp .env.prod.example .env.prod
  nano .env.prod  # Fill in production values
  ```

- [ ] Production secrets configured
  - [ ] SECRET_KEY (64+ chars, unique)
  - [ ] JWT_SECRET_KEY (64+ chars, unique)
  - [ ] VAPI_API_KEY (production credentials)
  - [ ] VAPI_WEBHOOK_SECRET (64+ chars, unique)
  - [ ] OPENAI_API_KEY (production credentials)
  - [ ] Database password (strong, unique)
  - [ ] CORS_ORIGINS (production domains only)

- [ ] Production validation passes
  ```bash
  # Test production config
  APP_ENV=production python -c "from app.core.production_validation import validate_startup; validate_startup()"
  ```

### Deployment Steps

- [ ] Stop current production services
  ```bash
  docker-compose -f docker-compose.prod.yml down
  ```

- [ ] Backup production database
  ```bash
  ./scripts/backup/backup_database.sh
  ```

- [ ] Pull latest code
  ```bash
  git pull origin main
  ```

- [ ] Build production images
  ```bash
  docker-compose -f docker-compose.prod.yml build
  ```

- [ ] Start production services
  ```bash
  docker-compose -f docker-compose.prod.yml up -d
  ```

- [ ] Monitor startup logs
  ```bash
  docker-compose -f docker-compose.prod.yml logs -f
  ```

### Post-Deployment Verification

- [ ] All services healthy
  ```bash
  docker-compose -f docker-compose.prod.yml ps
  curl http://localhost:8000/health/detailed
  ```

- [ ] Migrations applied successfully
  ```bash
  docker-compose -f docker-compose.prod.yml logs backend | grep -i migration
  ```

- [ ] Smoke tests pass
  ```bash
  ./scripts/smoke_test.sh --base-url http://localhost:8000
  ```

- [ ] Authentication works
  ```bash
  curl -X POST http://localhost:8000/api/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"production-password"}'
  ```

- [ ] Core API endpoints work
  ```bash
  curl http://localhost:8000/api/students \
    -H "Authorization: Bearer YOUR_TOKEN"
  ```

- [ ] Frontend accessible
  ```bash
  curl http://localhost:3000
  ```

- [ ] Webhook endpoint accessible
  ```bash
  curl http://localhost:8000/webhooks/vapi/test
  ```

- [ ] Background workers processing
  ```bash
  docker-compose -f docker-compose.prod.yml logs worker
  ```

### Monitoring

- [ ] Error rate normal
- [ ] Response times normal
- [ ] Database connections normal
- [ ] Redis memory usage normal
- [ ] RQ queue depth normal
- [ ] No unusual errors in logs
  ```bash
  docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error
  ```

---

## Rollback Procedure

### When to Rollback

- Critical functionality broken
- Data corruption detected
- Security vulnerability exposed
- Performance degradation severe
- User-facing errors widespread

### Rollback Steps

- [ ] Stop current services
  ```bash
  docker-compose -f docker-compose.prod.yml down
  ```

- [ ] Restore database from backup
  ```bash
  ./scripts/backup/restore_database.sh backups/attendai_backup_YYYYMMDD_HHMMSS.sql.gz
  ```

- [ ] Checkout previous version
  ```bash
  git checkout <previous-commit-hash>
  ```

- [ ] Rebuild images
  ```bash
  docker-compose -f docker-compose.prod.yml build
  ```

- [ ] Start services
  ```bash
  docker-compose -f docker-compose.prod.yml up -d
  ```

- [ ] Verify health
  ```bash
  curl http://localhost:8000/health/detailed
  ./scripts/smoke_test.sh
  ```

- [ ] Notify stakeholders
- [ ] Document rollback reason
- [ ] Create incident report

---

## Post-Release

### Verification

- [ ] Monitor for 1 hour post-release
- [ ] Check error logs
  ```bash
  docker-compose -f docker-compose.prod.yml logs --since=1h | grep -i error
  ```

- [ ] Verify user workflows
- [ ] Check analytics/reports
- [ ] Confirm background jobs processing

### Documentation

- [ ] Update release notes
- [ ] Document any issues encountered
- [ ] Update runbook if needed
- [ ] Close release ticket

### Cleanup

- [ ] Remove old Docker images
  ```bash
  docker image prune -f
  ```

- [ ] Archive old logs
- [ ] Update monitoring dashboards

---

## Emergency Contacts

**DevOps Team**: [devops@yourcompany.com]  
**Database Administrator**: [dba@yourcompany.com]  
**Application Developer**: [dev@yourcompany.com]  
**Vapi Support**: support@vapi.ai  

---

## Quick Commands

```bash
# Start production
docker-compose -f docker-compose.prod.yml up -d

# Stop production
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Backup database
./scripts/backup/backup_database.sh

# Restore database
./scripts/backup/restore_database.sh backups/file.sql.gz

# Run smoke tests
./scripts/smoke_test.sh

# Check health
curl http://localhost:8000/health/detailed

# Run release validation
./scripts/release_validation.sh
```

---

## Release Sign-Off

**Release Version**: _______________  
**Release Date**: _______________  
**Released By**: _______________  
**Verified By**: _______________  

**Pre-Release Checks**: ☐ Complete  
**Staging Validation**: ☐ Complete  
**Production Deployment**: ☐ Complete  
**Post-Release Verification**: ☐ Complete  

**Issues Encountered**:  
_________________________________  
_________________________________  

**Notes**:  
_________________________________  
_________________________________  

---

**This checklist must be completed for every production release.**
