# Database Migrations

This directory contains Alembic database migrations for the OSRS Diff project.

## Quick Start

### Prerequisites

1. Ensure PostgreSQL is running (via Docker Compose or locally)
2. Database credentials are configured in `.env` file or environment variables

### Common Commands

```bash
# Run all pending migrations
mise run db:upgrade

# Rollback the last migration
mise run db:downgrade

# Create a new migration (after modifying models)
MESSAGE="Add new column" mise run db:revision

# Check current migration status
alembic current

# View migration history
alembic history

# Initialize database from scratch (alternative to migrations)
mise run db:init

# Reset database (drop and recreate all tables)
mise run db:reset
```

## Migration Workflow

1. **Modify Models**: Make changes to SQLAlchemy models in `src/models/`
2. **Generate Migration**: Run `mise run db:revision` with a descriptive message
3. **Review Migration**: Check the generated migration file in `migrations/versions/`
4. **Apply Migration**: Run `mise run db:upgrade` to apply changes
5. **Test**: Verify the changes work as expected

## Configuration

The migration system is configured to:

- Use async SQLAlchemy with asyncpg driver
- Connect to PostgreSQL database specified in environment variables
- Auto-generate migrations based on model changes
- Use consistent naming conventions for constraints
- Support both upgrade and downgrade operations

## Files

- `alembic.ini` - Alembic configuration file
- `env.py` - Migration environment setup (async SQLAlchemy integration)
- `script.py.mako` - Template for new migration files
- `versions/` - Directory containing all migration files

## Environment Variables

The migration system uses the following environment variables:

- `DATABASE_URL` - PostgreSQL connection string (required)
- `DATABASE_ECHO` - Enable SQLAlchemy query logging (optional)
- `DATABASE_POOL_SIZE` - Connection pool size (optional)

## Troubleshooting

### Connection Issues

If you get database connection errors:

1. Ensure PostgreSQL is running: `docker-compose up -d postgres`
2. Check database credentials in `.env` file
3. Verify database exists: `osrs_diff`
4. Test connection manually with `psql` or database client

### Migration Conflicts

If you encounter migration conflicts:

1. Check current status: `alembic current`
2. View migration history: `alembic history`
3. Resolve conflicts by editing migration files
4. Consider creating a merge migration: `alembic merge -m "merge message"`

### Starting Fresh

To start with a clean database:

```bash
# Drop all tables and start over
mise run db:reset

# Or use migrations
alembic downgrade base
alembic upgrade head
```