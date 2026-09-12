# AttendAI Quick Start Guide

## First Time Setup

### 1. Prerequisites
- Docker Desktop installed and running
- Git installed
- (Optional) Python 3.11+ and Node.js 18+ for local development

### 2. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

**Important**: Edit `.env` and configure at minimum:
- `SECRET_KEY` - Generate a secure random string
- `JWT_SECRET_KEY` - Generate a different secure random string
- `VAPI_API_KEY` - Your Vapi API key (get from https://vapi.ai)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - Your LLM provider key

### 3. Start the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

### 5. Initialize Database (Coming in Phase 2)

```bash
# Run migrations (not yet implemented)
docker-compose exec backend alembic upgrade head

# Load seed data (not yet implemented)
docker-compose exec backend python scripts/seed_data.py
```

## Development Workflow

### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Run tests
pytest

# Check code quality
ruff check .
black --check .

# Format code
black .
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Run tests
npm test

# Lint code
npm run lint

# Type check
npm run type-check
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v
```

## Common Issues

### Port Already in Use
If ports 3000, 8000, 5432, or 6379 are already in use:
1. Stop conflicting services
2. Or modify ports in `docker-compose.yml`

### Backend Won't Start
1. Check Docker Desktop is running
2. Check `.env` file exists
3. View logs: `docker-compose logs backend`

### Frontend Build Errors
1. Remove node_modules volume: `docker-compose down -v`
2. Rebuild: `docker-compose up --build frontend`

### Database Connection Issues
1. Ensure PostgreSQL container is healthy: `docker-compose ps`
2. Check DATABASE_URL in `.env`
3. Wait a few seconds for PostgreSQL to fully initialize

## Next Steps

Once Phase 1 is complete, proceed to:
- **Phase 2**: Database schema and migrations
- **Phase 3**: Authentication and core APIs
- See [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) for full roadmap
