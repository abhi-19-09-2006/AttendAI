# AttendAI

**AI-Powered Automated Student Absence Communication & Faculty Intelligence Platform**

AttendAI automatically calls parents when students are absent, gathers information about the absence using AI voice agents, and provides structured insights to faculty through an intelligent dashboard.

---

## 🎯 Project Status

**Current Phase**: Phase 1 - Foundation & Architecture  
**Status**: In Development  
**Version**: 0.1.0-alpha

---

## 📋 Overview

When a student is marked absent, AttendAI:
1. Automatically creates a parent contact task
2. Places an AI-powered voice call to the parent/guardian
3. Conducts a natural conversation to understand the absence reason
4. Extracts structured information from the conversation
5. Stores the data for faculty review
6. Flags low-confidence responses for human follow-up
7. Generates comprehensive reports and analytics

---

## 🏗️ Architecture

AttendAI is built with a modern, scalable architecture:

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Next.js 14+ with TypeScript
- **Database**: PostgreSQL 15+
- **Cache/Queue**: Redis 7+
- **Voice AI**: Vapi
- **LLM**: OpenAI GPT-4 or Anthropic Claude (configurable)
- **Infrastructure**: Docker & Docker Compose

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- (Optional) Node.js 18+ and Python 3.11+ for local development

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AttendAI
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables**
   Edit `.env` and add your API keys:
   - `VAPI_API_KEY` - Your Vapi API key
   - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM provider key
   - Update database credentials if needed

4. **Start the application**
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

6. **Load seed data (development only)**
   ```bash
   docker-compose exec backend python scripts/seed_data.py
   ```

7. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

---

## 🔧 Development

### Project Structure

```
AttendAI/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routers/endpoints
│   │   ├── core/           # Configuration, security
│   │   ├── models/         # SQLAlchemy models
│   │   ├── repositories/   # Data access layer
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities and API client
│   │   └── types/         # TypeScript types
│   ├── public/            # Static assets
│   └── package.json       # Node dependencies
│
├── docker-compose.yml     # Local development environment
├── .env.example           # Environment template
├── ARCHITECTURE.md        # System architecture documentation
├── DEVELOPMENT_PLAN.md    # Phased development plan
└── README.md             # This file
```

### Running Tests

**Backend tests:**
```bash
docker-compose exec backend pytest
```

**Frontend tests:**
```bash
docker-compose exec frontend npm test
```

### Code Quality

**Backend linting:**
```bash
docker-compose exec backend ruff check .
docker-compose exec backend black --check .
```

**Frontend linting:**
```bash
docker-compose exec frontend npm run lint
```

---

## 📊 Features

### Core Features (Planned)
- ✅ Faculty authentication and authorization
- ✅ Student and parent management
- ✅ Attendance tracking and import
- ✅ Automated absence detection
- ✅ AI voice calling via Vapi
- ✅ Intelligent conversation handling
- ✅ Structured information extraction
- ✅ Confidence scoring and human review
- ✅ Call retry and follow-up management
- ✅ Comprehensive analytics dashboard
- ✅ Report generation and export

### Security Features
- JWT-based authentication
- Role-based access control
- Webhook signature verification
- Input validation and sanitization
- Rate limiting
- Audit logging
- Configurable data retention

---

## 🔐 Security

AttendAI takes security seriously:

- **No secrets in Git**: All sensitive data in environment variables
- **Webhook verification**: Validates all incoming Vapi webhooks
- **Input validation**: Pydantic schemas validate all API inputs
- **Password hashing**: bcrypt with appropriate work factor
- **SQL injection prevention**: SQLAlchemy ORM parameterized queries
- **CORS protection**: Configured allowed origins
- **Rate limiting**: Prevents API abuse
- **Audit logging**: Tracks sensitive operations

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed security architecture.

---

## 📖 API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🧪 Testing

AttendAI includes comprehensive test coverage:

- **Unit tests**: Services, repositories, utilities
- **Integration tests**: API endpoints, database operations
- **End-to-end tests**: Complete workflows

Target coverage: >80%

---

## 🗺️ Roadmap

See [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) for the complete phased development plan.

### Current Phase: Phase 1 - Foundation ✅
- [x] Project structure
- [x] Documentation
- [ ] Docker configuration
- [ ] Backend skeleton
- [ ] Frontend skeleton
- [ ] Health checks

### Next Phase: Phase 2 - Database Layer
- Database schema and migrations
- SQLAlchemy models
- Seed data
- Repository layer

---

## 🤝 Contributing

### Development Workflow

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Ensure tests pass
5. Update documentation
6. Submit pull request

### Commit Message Format

Use conventional commits:
```
feat: add student import from CSV
fix: correct confidence calculation
docs: update API documentation
test: add call orchestration tests
```

---

## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- **Vapi** - Voice AI platform
- **FastAPI** - Modern Python web framework
- **Next.js** - React framework
- **OpenAI/Anthropic** - LLM providers

---

## 📞 Support

For questions or issues:
- Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
- Check [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) for roadmap
- Open an issue in the repository

---

## ⚠️ Important Notes

- **Development Status**: This project is under active development
- **Not Production Ready**: Do not use in production without thorough testing
- **Test Phone Numbers**: Use test numbers for development and testing
- **API Keys**: Never commit API keys to version control
- **Privacy**: Handle student data in compliance with FERPA and applicable regulations
- **Medical Advice**: The system NEVER provides medical diagnoses or advice

---

**Built with ❤️ for better school-parent communication**
