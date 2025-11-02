# OSRS Diff Backend Service

A backend service for tracking Old School RuneScape character progression by periodically fetching hiscores data from the official OSRS API.

## Features

- Track multiple OSRS players' progression over time
- JWT-based authentication for secure API access
- Async background tasks for data fetching
- RESTful API for player management and statistics
- Historical progress analysis and reporting

## Tech Stack

- **FastAPI** - Modern async web framework
- **PostgreSQL** - Primary database with async SQLAlchemy
- **Redis** - Task queue broker and caching
- **TaskIQ** - Async task queue for background jobs
- **Docker** - Containerized development and deployment

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd osrs-diff
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Start the development environment:
```bash
mise run docker:up
```

4. The API will be available at `http://localhost:8000`

### Local Development (without Docker)

1. Install dependencies:
```bash
mise run dev-install
```

2. Start PostgreSQL and Redis services locally

3. Run database migrations:
```bash
mise run db:upgrade
```

4. Start the application:
```bash
mise run dev
```

5. Start the background worker (in another terminal):
```bash
mise run worker
```

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
src/
├── api/          # FastAPI endpoints and routing
├── models/       # SQLAlchemy database models
├── services/     # Business logic services
├── workers/      # Background task workers
└── main.py       # Application entry point

scripts/          # Database and deployment scripts
migrations/       # Alembic database migrations
tests/           # Test suite
```

## Development

### Running Tests

```bash
mise run test
```

### Code Formatting

```bash
mise run format
```

### Type Checking

```bash
mise run typecheck
```

### Available Commands

Run `mise run help` to see all available development tasks.

## License

MIT License