<div align="center">

# 🎮 OSRS Diff

### **Track Your Old School RuneScape Progress Like Never Before**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**A modern, full-stack application for tracking Old School RuneScape character progression with intelligent data management, AI-powered insights, and beautiful visualizations.**

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Deployment](#-deployment) • [Development](#-development) • [Documentation](#-documentation)

</div>

---

## ✨ Features

### 🎯 Core Capabilities

- **📊 Real-Time Progress Tracking** - Automatically fetch and track player hiscores every 30 minutes
- **🧠 Smart Data Deduplication** - Only stores records when stats actually change, saving storage and improving performance
- **🤖 AI-Powered Summaries** - Get intelligent insights about your gameplay progress using OpenAI
- **📈 Beautiful Visualizations** - Interactive charts and graphs showing skill progression, XP gains, and boss kills
- **🔐 Secure Authentication** - JWT-based auth system with role-based access control
- **⚡ Async & Performant** - Built with modern async Python and React for blazing-fast performance
- **🔄 Background Processing** - Reliable task queue system for scheduled data fetching
- **👥 Multi-Player Support** - Track multiple characters with organized management

### 🎨 Frontend Highlights

- **Modern React UI** - Clean, responsive design with TailwindCSS
- **Admin Dashboard** - Comprehensive system monitoring and player management
- **Player Statistics** - Detailed skill breakdowns, XP rates, and progress analytics
- **Historical Analysis** - View your progression over time with interactive charts
- **Task Monitoring** - Real-time visibility into background job execution

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern async web framework with automatic API docs |
| **PostgreSQL** | Robust relational database with async SQLAlchemy ORM |
| **Redis** | Task queue broker and caching layer |
| **TaskIQ** | Async task queue for background job processing |
| **Alembic** | Database migration management |
| **uv** | Lightning-fast Python package manager |
| **OpenAI** | AI-powered progress summaries |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18** | Modern UI library with hooks and context |
| **TypeScript** | Type-safe development experience |
| **Vite** | Next-generation build tool and dev server |
| **TailwindCSS** | Utility-first CSS framework |
| **Recharts** | Beautiful, responsive chart library |
| **React Router** | Client-side routing |

### DevOps
- **Docker & Docker Compose** - Containerized development and deployment
- **Alembic Migrations** - Version-controlled database schema changes
- **Structured Logging** - Comprehensive logging with structlog

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **uv** - Fast Python package manager ([Install Guide](https://github.com/astral-sh/uv))
- **Docker & Docker Compose** - Container runtime ([Install Guide](https://docs.docker.com/get-docker/))
- **Node.js 18+** - For frontend development ([Download Node.js](https://nodejs.org/))
- **Git** - Version control

### 🐳 Docker Setup (Recommended)

The easiest way to get started is with Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd osrsdiff

# Start all services
docker-compose up -d

# Or with the app profile to include backend services
docker-compose --profile app up -d
```

**Services will be available at:**
- 🌐 **API**: http://localhost:8000
- 🎨 **Frontend**: http://localhost:3000 (if running separately)
- 📚 **API Docs**: http://localhost:8000/docs
- 🗄️ **PgAdmin**: http://localhost:8080
- 🔴 **Redis Commander**: http://localhost:8081

### 💻 Local Development Setup

#### Backend Setup

1. **Install dependencies:**
```bash
# Using mise (if configured)
mise run dev-install

# Or manually with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start PostgreSQL and Redis:**
```bash
# Using Docker Compose (just the services)
docker-compose up -d postgres redis

# Or use local installations
```

4. **Run database migrations:**
```bash
mise run db:upgrade
# Or: alembic upgrade head
```

5. **Start the API server:**
```bash
mise run dev
# Or: fastapi run app/main.py --reload
```

6. **Start the background worker** (in a separate terminal):
```bash
mise run worker
# Or: taskiq worker app.workers.main:broker
```

7. **Start the scheduler** (in another terminal):
```bash
docker-compose up scheduler
# Or: taskiq scheduler app.workers.main:scheduler
```

#### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

4. **Generate API client** (optional, if backend schema changed):
```bash
npm run generate-api
```

---

## 🚢 Deployment

### Production Deployment with Docker

1. **Build the production image:**
```bash
docker build -t osrsdiff:latest .
```

2. **Set up environment variables:**
Create a `.env` file or set environment variables:
```bash
DATABASE__URL=postgresql+asyncpg://user:password@host:5432/dbname
REDIS__URL=redis://host:6379/0
JWT__SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
OPENAI__API_KEY=your-openai-api-key
```

3. **Run database migrations:**
```bash
docker run --rm --env-file .env osrsdiff:latest alembic upgrade head
```

4. **Start services:**
```bash
# Update docker-compose.yml with production settings
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables

Key environment variables to configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE__URL` | PostgreSQL connection string | ✅ Yes |
| `REDIS__URL` | Redis connection string | ✅ Yes |
| `JWT__SECRET_KEY` | Secret key for JWT tokens | ✅ Yes |
| `ENVIRONMENT` | Environment (development/production) | ✅ Yes |
| `OPENAI__API_KEY` | OpenAI API key for summaries | ❌ Optional |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | ❌ No |

### Production Checklist

- [ ] Set strong `JWT__SECRET_KEY`
- [ ] Configure secure database credentials
- [ ] Set up SSL/TLS for production
- [ ] Configure CORS origins appropriately
- [ ] Set up proper logging and monitoring
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up health checks and monitoring
- [ ] Review and update Docker security settings

---

## 👨‍💻 Development

### Running Tests

```bash
mise run test
# Or: pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

### Code Quality

**Format code:**
```bash
mise run format
# Or: black . && isort .
```

**Type checking:**
```bash
mise run typecheck
# Or: mypy app
```

**Lint frontend:**
```bash
cd frontend
npm run lint
```

### Project Structure

```
osrsdiff/
├── app/                    # Backend application
│   ├── api/               # FastAPI endpoints and routing
│   │   ├── v1/           # API version 1 endpoints
│   │   └── auth.py       # Authentication endpoints
│   ├── models/           # SQLAlchemy database models
│   ├── services/         # Business logic services
│   ├── workers/          # Background task workers
│   ├── utils/            # Utility functions
│   └── main.py           # Application entry point
│
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── api/         # Generated API client
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── contexts/    # React contexts
│   │   └── assets/      # Static assets
│   └── package.json
│
├── migrations/            # Alembic database migrations
├── tests/                 # Test suite
├── templates/            # Jinja2 templates (for AI summaries)
├── docker-compose.yml     # Docker Compose configuration
└── Dockerfile             # Docker image definition
```

### Key Features Explained

#### 🧠 Smart Data Deduplication

The service implements intelligent deduplication to avoid storing redundant hiscore records:

- **Automatic Comparison**: Each fetch compares new data with the most recent record
- **Efficient Storage**: Only saves records when player stats, ranks, or boss kills have changed
- **Timestamp Tracking**: Always updates `last_fetched` regardless of data changes
- **Status Reporting**: Fetch results indicate `unchanged`, `success`, or error statuses

This ensures the database only grows when players actually make progress, significantly reducing storage requirements.

#### ⏰ Task Scheduling

Background tasks are scheduled using cron-like expressions:

- **Cron Expressions**: Easy scheduling like `*/30 * * * *` (every 30 minutes)
- **Redis Coordination**: Uses Redis locks to prevent duplicate execution
- **Manual Triggering**: All scheduled tasks can be triggered via API
- **Task Monitoring**: View task status, last run times, and next scheduled runs

Current scheduled tasks:
- **Hiscore Fetching**: Every 30 minutes (`*/30 * * * *`)

#### 🤖 AI-Powered Summaries

Generate intelligent summaries of player progress using OpenAI:

- **Progress Analysis**: Understand your gameplay patterns
- **Customizable Prompts**: Jinja2 templates for flexible summary generation
- **Historical Context**: Summaries include historical data for better insights

---

## 📚 Documentation

### API Documentation

Once the application is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Available Commands

Run `mise run help` to see all available development tasks, or check `pyproject.toml` for script definitions.

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality checks pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">

**Built with ❤️ for the OSRS community**

[Report Bug](https://github.com/yourusername/osrsdiff/issues) • [Request Feature](https://github.com/yourusername/osrsdiff/issues) • [Documentation](https://github.com/yourusername/osrsdiff/wiki)

</div>
