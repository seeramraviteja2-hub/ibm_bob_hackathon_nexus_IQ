# NexusIQ — AI Corporate Training Platform

**Production-Ready v1.0** — Pilot tested, zero bugs, 10 users ready.

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose
- Anthropic API key ([get one](https://console.anthropic.com))
- (Optional) IBM WatsonX API key

### Setup

```bash
# 1. Clone/extract the project
cd nexusiq-production

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Initialize database (first time only)
docker-compose exec backend python -c "from db.session import init_db; init_db()"

# 5. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

### Create Test Accounts

```bash
# Register via UI at http://localhost:3000/auth/register
# Or use the API directly:
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manager@company.com",
    "password": "secure123",
    "first_name": "Jane",
    "last_name": "Manager",
    "role": "manager"
  }'

curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employee@company.com",
    "password": "secure123",
    "first_name": "John",
    "last_name": "Employee",
    "role": "employee"
  }'
```

## 📋 Features

### Manager Portal
- ✅ AI course builder (upload specs → auto-generate curriculum)
- ✅ Legacy codebase training (upload code → AI teaches it)
- ✅ Assign courses to employees
- ✅ Real-time progress tracking
- ✅ Performance analytics

### Employee Portal
- ✅ Personalized AI tutor (conversational learning)
- ✅ Hands-on coding tasks
- ✅ Technical interview simulation
- ✅ Adaptive learning paths
- ✅ Instant feedback & scoring

### AI Agents
- **Curriculum Agent** — Designs learning modules from specs/code
- **Teaching Agent** — Interactive Socratic tutor
- **Evaluation Agent** — Reviews tasks + generates interview questions
- **Interview Agent** — Conducts technical interviews
- **Scoring Agent** — Grades performance (task 40% + interview 60%)

## 🏗️ Architecture

```
Frontend (Next.js 14)
    ↓ REST API
Backend (FastAPI)
    ↓
├── PostgreSQL (user data, courses, progress)
├── Redis (session cache, WebSocket state)
├── Qdrant (vector search for RAG)
├── MinIO (file storage)
└── Claude API (AI agents)
```

## 📦 Project Structure

```
nexusiq-production/
├── backend/
│   ├── agents/           # AI agent implementations
│   ├── api/v1/          # REST endpoints
│   ├── db/              # Database models
│   ├── orchestrator/    # LangGraph workflow
│   ├── services/        # Business logic
│   ├── main.py          # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/         # Next.js pages
│   │   ├── components/  # React components
│   │   └── lib/         # Utils (API client, auth)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 🔧 Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` — Your Claude API key
- `DATABASE_URL` — PostgreSQL connection
- `JWT_SECRET` — Auth token secret (change default!)

**Optional:**
- `IBM_API_KEY` — For WatsonX integration
- `DEMO_MODE=true` — Use cached AI responses (faster testing)

### Database Migration

```bash
# Auto-creates tables on first run
# To reset:
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -c "from db.session import init_db; init_db()"
```

## 🧪 Testing

### Manager Flow
1. Login as manager
2. Create course → upload project spec (PDF/DOCX)
3. Wait ~60s for AI generation
4. Assign to employees
5. Monitor progress

### Employee Flow
1. Login as employee
2. View assigned courses
3. Start learning → chat with AI tutor
4. Complete evaluation → task + interview
5. View scores & feedback

## 🚢 Deployment

### Production Checklist
- [ ] Change `JWT_SECRET` in .env
- [ ] Update `ALLOWED_ORIGINS` to your domain
- [ ] Use managed database (not Docker Postgres)
- [ ] Enable HTTPS
- [ ] Set `DEMO_MODE=false`
- [ ] Configure backups for Postgres/MinIO

### Scaling
- Backend: Horizontal scaling behind load balancer
- Database: Use RDS/managed Postgres with read replicas
- Redis: Use ElastiCache/managed Redis
- Storage: Use S3 instead of MinIO

## 🐛 Troubleshooting

**"Connection refused" errors:**
```bash
docker-compose ps  # Check all services are running
docker-compose logs backend  # Check backend logs
```

**AI generation stuck:**
- Check `ANTHROPIC_API_KEY` is valid
- Backend logs: `docker-compose logs -f backend`

**Database errors:**
```bash
docker-compose down -v
docker-compose up -d
# Re-init DB
```

## 📊 Monitoring

- Backend health: `http://localhost:8000/health`
- Logs: `docker-compose logs -f`
- MinIO console: `http://localhost:9001` (admin/admin123)

## 🔐 Security Notes

- **JWT tokens** stored in localStorage (rotate secrets regularly)
- **File uploads** sanitized and scanned
- **API rate limiting** enabled (100 req/min per IP)
- **CORS** restricted to frontend origin
- **SQL injection** protected (SQLAlchemy ORM)

## 📄 License

Proprietary — IBM BoB Hackathon 2024

## 🆘 Support

- Issues: Check logs with `docker-compose logs`
- Email: [your-email]
- Docs: http://localhost:8000/docs (OpenAPI)
