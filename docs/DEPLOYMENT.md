# Deployment Guide

This guide covers deploying the OSRS Diff application with the TaskIQ scheduler system.

## Overview

The application consists of several services:
- **App**: FastAPI web application
- **Worker**: TaskIQ background task worker
- **Scheduler**: TaskIQ scheduler for managing scheduled tasks
- **PostgreSQL**: Database
- **Redis**: Task queue broker and schedule storage

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for running migration scripts)
- Access to PostgreSQL and Redis instances

## Environment Setup

### Development

1. Copy environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your configuration

3. Start services:
   ```bash
   docker-compose up -d
   ```

### Production

1. Copy production environment file:
   ```bash
   cp .env.production.example .env.production
   ```

2. Update the `.env.production` file with secure values:
   - Generate strong passwords for database and Redis
   - Set a secure JWT secret key (minimum 32 characters)
   - Configure CORS origins and allowed hosts
   - Set appropriate log levels

3. Create external volumes:
   ```bash
   docker volume create osrs-diff-postgres-data
   docker volume create osrs-diff-redis-data
   ```

4. Deploy with production configuration:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
   ```

## Scheduler Migration Deployment

### Automated Deployment

Use the deployment script for a complete migration:

```bash
# Dry run to see what would happen
python scripts/deploy_scheduler.py --dry-run

# Deploy to development
python scripts/deploy_scheduler.py --environment development

# Deploy to production
python scripts/deploy_scheduler.py --environment production
```

### Manual Deployment Steps

If you prefer to run the deployment manually:

1. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

2. **Migrate Existing Players**:
   ```bash
   # Dry run first
   python scripts/migrate_to_taskiq_scheduler.py --dry-run
   
   # Run actual migration
   python scripts/migrate_to_taskiq_scheduler.py
   ```

3. **Update Services**:
   ```bash
   # Stop old services
   docker-compose stop worker app
   
   # Start with scheduler
   docker-compose up -d postgres redis
   docker-compose up -d app worker scheduler
   ```

4. **Verify Deployment**:
   ```bash
   python scripts/migrate_to_taskiq_scheduler.py --verify-only
   ```

## Service Management

### Starting Services

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d
```

### Stopping Services

```bash
docker-compose down
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f scheduler
docker-compose logs -f worker
docker-compose logs -f app
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart scheduler
```

## Health Checks

### Service Health

Check if services are running:
```bash
docker-compose ps
```

### Database Health

```bash
# Check database connection
docker-compose exec postgres pg_isready -U osrs_diff -d osrs_diff

# Connect to database
docker-compose exec postgres psql -U osrs_diff -d osrs_diff
```

### Redis Health

```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# View scheduled tasks
docker-compose exec redis redis-cli keys "osrsdiff:schedules:*"
```

### Application Health

```bash
# Check API health
curl http://localhost:8000/health

# Check scheduled players
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/system/schedules
```

## Monitoring

### TaskIQ Scheduler

Monitor scheduler activity:
```bash
# View scheduler logs
docker-compose logs -f scheduler

# Check Redis for schedules
docker-compose exec redis redis-cli keys "osrsdiff:schedules:*"
```

### Task Execution

Monitor task execution:
```bash
# View worker logs
docker-compose logs -f worker

# Check task results in Redis
docker-compose exec redis redis-cli keys "taskiq:result:*"
```

### Database Monitoring

```bash
# Check active connections
docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "SELECT count(*) FROM pg_stat_activity;"

# Check table sizes
docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## Troubleshooting

### Scheduler Not Starting

1. Check Redis connection:
   ```bash
   docker-compose logs redis
   ```

2. Verify environment variables:
   ```bash
   docker-compose exec scheduler env | grep REDIS
   ```

3. Check scheduler logs:
   ```bash
   docker-compose logs scheduler
   ```

### Tasks Not Executing

1. Check worker status:
   ```bash
   docker-compose logs worker
   ```

2. Verify schedules in Redis:
   ```bash
   docker-compose exec redis redis-cli keys "osrsdiff:schedules:*"
   ```

3. Check player schedule_id values:
   ```bash
   docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "SELECT id, username, schedule_id FROM players WHERE is_active = true LIMIT 10;"
   ```

### Migration Issues

1. Check migration logs:
   ```bash
   ls -la migration_*.log
   tail -f migration_*.log
   ```

2. Verify database schema:
   ```bash
   docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "\d players"
   ```

3. Re-run migration for specific players:
   ```bash
   python scripts/migrate_to_taskiq_scheduler.py --continue-from PLAYER_ID
   ```

### Performance Issues

1. Monitor Redis memory usage:
   ```bash
   docker-compose exec redis redis-cli info memory
   ```

2. Check database performance:
   ```bash
   docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
   ```

3. Adjust worker concurrency:
   ```bash
   # Update TASKIQ_WORKER_CONCURRENCY in environment file
   docker-compose restart worker
   ```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U osrs_diff osrs_diff > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T postgres psql -U osrs_diff osrs_diff < backup_file.sql
```

### Redis Backup

```bash
# Create Redis backup
docker-compose exec redis redis-cli save
docker cp $(docker-compose ps -q redis):/data/dump.rdb redis_backup_$(date +%Y%m%d_%H%M%S).rdb

# Restore Redis backup
docker cp redis_backup_file.rdb $(docker-compose ps -q redis):/data/dump.rdb
docker-compose restart redis
```

## Rollback Procedures

### Rolling Back Scheduler Migration

If you need to rollback to the old scheduler:

1. Stop TaskIQ scheduler:
   ```bash
   docker-compose stop scheduler
   ```

2. Restore old scheduler code (if backed up)

3. Clear schedule_id values (optional):
   ```bash
   docker-compose exec postgres psql -U osrs_diff -d osrs_diff -c "UPDATE players SET schedule_id = NULL;"
   ```

4. Restart services with old configuration

### Database Rollback

```bash
# Rollback to previous migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade REVISION_ID
```

## Security Considerations

### Production Security

1. **Use strong passwords** for all services
2. **Enable Redis authentication** with `requirepass`
3. **Use HTTPS** in production with proper SSL certificates
4. **Restrict network access** using firewalls or security groups
5. **Regular security updates** for base images
6. **Monitor logs** for suspicious activity
7. **Backup encryption** for sensitive data

### Environment Variables

Never commit production environment files to version control. Use secure secret management systems in production environments.

### Network Security

Consider using Docker networks to isolate services and restrict external access to internal services like PostgreSQL and Redis.

## Performance Tuning

### Database Optimization

1. **Connection pooling**: Adjust `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`
2. **Query optimization**: Monitor slow queries and add indexes
3. **Vacuum and analyze**: Regular maintenance for PostgreSQL

### Redis Optimization

1. **Memory management**: Monitor Redis memory usage
2. **Persistence**: Configure appropriate persistence settings
3. **Connection limits**: Adjust `REDIS_MAX_CONNECTIONS`

### TaskIQ Optimization

1. **Worker concurrency**: Adjust `TASKIQ_WORKER_CONCURRENCY` based on CPU cores
2. **Task timeouts**: Configure appropriate `TASKIQ_TASK_TIMEOUT`
3. **Retry settings**: Tune retry counts and delays for reliability

## Maintenance

### Regular Maintenance Tasks

1. **Database maintenance**: Regular VACUUM and ANALYZE
2. **Log rotation**: Prevent log files from growing too large
3. **Backup verification**: Regularly test backup restoration
4. **Security updates**: Keep base images and dependencies updated
5. **Performance monitoring**: Track key metrics over time

### Scheduled Maintenance

Consider scheduling regular maintenance windows for:
- Database optimization
- Redis memory cleanup
- Log file rotation
- Security updates
- Backup verification