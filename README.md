# OSRS Diff Backend Service

A backend service for tracking Old School RuneScape character progression by periodically fetching hiscores data from the official OSRS API.

## Features

- Track multiple OSRS players' progression over time
- JWT-based authentication for secure API access
- Async background tasks for data fetching
- **Smart data deduplication** - only saves hiscore records when data has changed
- RESTful API for player management and statistics
- Historical progress analysis and reporting

## Tech Stack

### Backend
- **FastAPI** - Modern async web framework
- **PostgreSQL** - Primary database with async SQLAlchemy
- **Redis** - Task queue broker and caching
- **TaskIQ** - Async task queue for background jobs
- **uv** - Fast Python package manager and project manager
- **Docker** - Containerized development and deployment

### Frontend
- **React 18** - Modern UI library
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **Recharts** - Data visualization library

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
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
# Or use docker-compose directly:
docker-compose up
```

4. Services will be available at:
   - API: `http://localhost:8000`
   - Frontend: `http://localhost:3000`
   - API Docs: `http://localhost:8000/docs`
   - PgAdmin: `http://localhost:8080`
   - Redis Commander: `http://localhost:8081`

### Local Development (without Docker)

1. Install dependencies with `uv`:
```bash
mise run dev-install
```

This will create a virtual environment and install all dependencies using `uv`.

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

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

See `frontend/README.md` for more details.

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
app/              # Backend application
├── api/          # FastAPI endpoints and routing
├── models/       # SQLAlchemy database models
├── services/     # Business logic services
├── workers/      # Background task workers
└── main.py       # Application entry point

frontend/         # React frontend application
├── src/
│   ├── components/  # React components
│   ├── pages/       # Page components
│   ├── contexts/    # React contexts
│   └── lib/         # Utilities and API client

migrations/       # Alembic database migrations
tests/           # Test suite
```

## Key Features

### Data Deduplication

The service implements intelligent data deduplication to avoid storing redundant hiscore records:

- **Automatic comparison**: Each fetch compares new data with the most recent record
- **Efficient storage**: Only saves records when player stats, ranks, or boss kills have changed
- **Timestamp tracking**: Always updates the player's `last_fetched` timestamp regardless of data changes
- **Status reporting**: Fetch results indicate whether data was `unchanged`, `success` (new record), or other statuses

This ensures the database only grows when players actually make progress, significantly reducing storage requirements and improving query performance.



### Task Scheduling

The service uses a cron-like scheduler for background tasks:

- **Cron expressions**: Easy-to-understand scheduling like `*/30 * * * *` (every 30 minutes) or `0 2 * * *` (daily at 2 AM)
- **Configuration-based**: Tasks are defined in `src/workers/task_config.py` for easy management
- **Redis coordination**: Uses Redis locks to prevent duplicate execution across multiple workers
- **Manual triggering**: All scheduled tasks can be triggered manually via API endpoints
- **Task monitoring**: View task status, last run times, and next scheduled runs

Current scheduled tasks:
- **Hiscore fetching**: Every 30 minutes (`*/30 * * * *`)

### Testing Deduplication

Run the demonstration script to see deduplication in action:

```bash
python scripts/test_deduplication.py
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