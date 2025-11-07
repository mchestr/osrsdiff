# OSRS Diff Frontend

Modern React frontend for the OSRS Diff character progression tracking service.

## Features

- **Modern Stack**: React 18, TypeScript, Vite
- **Styling**: TailwindCSS with custom design system
- **Authentication**: JWT-based auth with automatic token refresh
- **Admin Dashboard**: Full player management and system monitoring
- **Player Stats**: Comprehensive statistics and progress tracking
- **Charts**: Beautiful data visualization with Recharts

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

### Building

Build for production:

```bash
npm run build
```

The built files will be in the `dist` directory.

### Generating API Client

To generate TypeScript types and API client from the OpenAPI spec:

1. Make sure the backend is running
2. Run:

```bash
npm run generate-api
```

This will generate the API client in `src/api/` based on the OpenAPI spec from the backend.

## Project Structure

```
frontend/
├── src/
│   ├── api/              # Generated API client (run generate-api)
│   ├── components/       # Reusable React components
│   ├── contexts/         # React contexts (Auth, etc.)
│   ├── lib/              # Utilities and API setup
│   ├── pages/            # Page components
│   ├── App.tsx           # Main app component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── index.html            # HTML template
└── package.json          # Dependencies
```

## Features

### Authentication

- JWT token-based authentication
- Automatic token refresh
- Protected routes
- Admin role checking

### Admin Dashboard

- System health monitoring
- Database statistics
- Player management (add, delete, activate/deactivate)
- Manual fetch triggers
- Schedule management

### Player Stats Page

- Overall statistics (level, experience, combat level)
- 30-day progress tracking
- Skill breakdown with charts
- Boss kill counts
- Historical data visualization

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Development Notes

- The app uses Vite's proxy to forward API requests to the backend
- Authentication tokens are stored in localStorage
- The app automatically refreshes expired tokens
- Admin routes are protected and only accessible to admin users

