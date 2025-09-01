# TasKvox AI - Conversational AI Dashboard

A powerful web dashboard for managing ElevenLabs Conversational AI agents and bulk calling campaigns.

![TasKvox AI Dashboard](https://img.shields.io/badge/TasKvox-AI%20Dashboard-blue?style=for-the-badge&logo=robot)

## 🚀 Features

- **AI Agent Management**: Create, configure, and test conversational AI agents
- **Bulk Voice Campaigns**: Upload CSV contacts and launch mass calling campaigns
- **Real-time Analytics**: Track call success rates, campaign performance, and costs
- **Call History**: View detailed transcripts and conversation records
- **User Authentication**: Secure login/registration system
- **Responsive UI**: Modern, mobile-friendly interface

## 🛠️ Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: Jinja2 templates + Bootstrap 5 + HTMX
- **Authentication**: JWT tokens with secure password hashing
- **API Integration**: ElevenLabs Conversational AI
- **Deployment**: Docker + Docker Compose

## 📦 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Git
- ElevenLabs API key

### 1. Clone the Repository

```bash
git clone <repository-url>
cd taskvox-ai
```

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb taskvox_db

# Copy environment file
cp .env.example .env

# Edit .env with your database credentials and secret keys
nano .env
```

### 4. Database Migration

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 5. Run the Application

```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Visit `http://localhost:8000` to access the dashboard.

## 🐳 Docker Deployment

### Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f web
```

### Production

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale the application
docker-compose -f docker-compose.prod.yml up -d --scale web=3
```

## 📊 Usage Guide

### 1. Account Setup

1. Visit the registration page
2. Create your account
3. Configure your ElevenLabs API key in settings

### 2. Create AI Agents

1. Go to "AI Agents" section
2. Click "Create Agent"
3. Configure:
   - Agent name
   - Voice selection
   - System prompt (personality/behavior)
4. Test your agent with a phone call

### 3. Launch Voice Campaigns

1. Navigate to "Voice Campaigns"
2. Click "Create Campaign"
3. Upload CSV file with contacts (phone_number column required)
4. Select your AI agent
5. Launch the campaign

### CSV Format Example

```csv
phone_number,name
+1234567890,John Doe
+1987654321,Jane Smith
+1555123456,Bob Johnson
```

### 4. Monitor Results

- View real-time campaign progress
- Check call success rates
- Review conversation transcripts
- Track costs and analytics

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/taskvox_db

# Security
SECRET_KEY=your-very-secure-secret-key
JWT_EXPIRE_MINUTES=720

# ElevenLabs (Optional default)
DEFAULT_ELEVENLABS_API_KEY=your-api-key
```

### ElevenLabs API Setup

1. Sign up at [ElevenLabs](https://elevenlabs.io)
2. Get your API key from the dashboard
3. Configure in TasKvox AI settings
4. Ensure you have sufficient credits for calls

## 📁 Project Structure

```
taskvox-ai/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database connection
│   ├── auth.py              # Authentication logic
│   ├── elevenlabs_client.py # ElevenLabs API client
│   ├── routers/             # API route handlers
│   │   ├── auth.py
│   │   ├── agents.py
│   │   ├── campaigns.py
│   │   └── dashboard.py
│   ├── templates/           # HTML templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── agents.html
│   │   └── campaigns.html
│   └── static/              # CSS, JS, images
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Multi-container setup
└── README.md               # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v tests/
```

## 📈 Performance & Scaling

### Database Optimization

```sql
-- Add indexes for better query performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_agents_user_active ON agents(user_id, is_active);
```

### Caching with Redis

```python
# Enable Redis caching in production
REDIS_URL=redis://localhost:6379/0
```

### Load Balancing

Use the included Nginx configuration for load balancing multiple app instances:

```bash
docker-compose up -d --scale web=3
```

## 🔒 Security Features

- **Password Hashing**: bcrypt with salt rounds
- **JWT Authentication**: Secure token-based auth
- **SQL Injection Protection**: SQLAlchemy ORM
- **XSS Protection**: Jinja2 template escaping
- **CSRF Protection**: Form tokens
- **Rate Limiting**: API endpoint protection
- **Input Validation**: Pydantic schema validation

## 🚦 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/me` - Current user info

### Agents
- `GET /agents/api` - List agents
- `POST /agents/api` - Create agent
- `GET /agents/{id}` - Get agent details
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent
- `POST /agents/{id}/test` - Test agent with phone call

### Campaigns
- `GET /campaigns/api` - List campaigns
- `POST /campaigns/api` - Create campaign
- `GET /campaigns/{id}` - Get campaign details
- `POST /campaigns/{id}/launch` - Launch campaign
- `POST /campaigns/{id}/pause` - Pause campaign
- `POST /campaigns/{id}/resume` - Resume campaign
- `DELETE /campaigns/{id}` - Delete campaign

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/dashboard/charts` - Get chart data
- `GET /api/dashboard/recent-activity` - Get recent activity

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -U taskvox_user -d taskvox_db
```

#### ElevenLabs API Issues
- Verify API key is correct and active
- Check account has sufficient credits
- Ensure phone numbers include country codes (+1, +44, etc.)

#### Port Already in Use
```bash
# Kill process using port 8000
sudo lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --port 8001
```

#### Permission Issues
```bash
# Fix file permissions
chmod +x start.sh
chown -R $USER:$USER uploads/
```

### Debug Mode

Enable detailed error logging:

```bash
# Set in .env file
DEBUG=true
LOG_LEVEL=DEBUG

# View logs in real-time
tail -f taskvox.log
```

## 📝 Development Guidelines

### Code Style

```bash
# Format code with Black
black app/ tests/

# Lint with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/agent-templates

# Make changes and commit
git add .
git commit -m "Add agent template functionality"

# Push and create PR
git push origin feature/agent-templates
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new column"

# Review migration file
nano alembic/versions/xxx_add_new_column.py

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## 🔧 Advanced Configuration

### Custom Voice Models

```python
# app/config.py
CUSTOM_VOICES = {
    "professional_male": "voice_id_1",
    "friendly_female": "voice_id_2",
    "energetic_young": "voice_id_3"
}
```

### Webhook Integration

```python
# Handle ElevenLabs webhook callbacks
@app.post("/webhooks/elevenlabs")
async def handle_webhook(request: Request):
    # Process call completion events
    # Update conversation status
    # Trigger notifications
    pass
```

### Custom Agent Templates

```json
{
  "sales_agent": {
    "name": "Sales Assistant",
    "prompt": "You are a professional sales assistant...",
    "voice_settings": {
      "stability": 0.8,
      "similarity_boost": 0.9
    }
  }
}
```

## 📊 Monitoring & Analytics

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# ElevenLabs API health
curl http://localhost:8000/health/api
```

### Metrics Collection

```python
# Prometheus metrics endpoint
from prometheus_client import Counter, Histogram

call_counter = Counter('taskvox_calls_total', 'Total calls made')
call_duration = Histogram('taskvox_call_duration_seconds', 'Call duration')
```

### Log Analysis

```bash
# View error logs
grep "ERROR" taskvox.log

# Monitor API calls
grep "POST\|PUT\|DELETE" taskvox.log

# Track user activity
grep "user_id" taskvox.log | tail -20
```

## 🚀 Deployment Strategies

### Digital Ocean Droplet

```bash
# Create droplet
doctl compute droplet create taskvox-prod \
  --image ubuntu-20-04-x64 \
  --size s-2vcpu-2gb \
  --region nyc1

# Deploy with Docker
git clone <repo-url>
docker-compose -f docker-compose.prod.yml up -d
```

### AWS EC2 with RDS

```bash
# Use RDS PostgreSQL
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/taskvox

# Deploy with ECS or direct EC2
```

### Heroku Deployment

```bash
# Install Heroku CLI
heroku create taskvox-ai

# Set environment variables
heroku config:set SECRET_KEY=your-key
heroku config:set DATABASE_URL=postgres://...

# Deploy
git push heroku main
```

## 📋 Roadmap

### Phase 1 (MVP) ✅
- [x] User authentication
- [x] Agent management
- [x] Basic campaigns
- [x] Call history
- [x] Dashboard analytics

### Phase 2 (Q1 2026)
- [ ] Advanced agent customization
- [ ] Team collaboration features
- [ ] Webhook integrations
- [ ] Advanced analytics
- [ ] Mobile app

### Phase 3 (Q2 2026)
- [ ] CRM integrations
- [ ] AI-powered insights
- [ ] Multi-language support
- [ ] White-label solution
- [ ] Enterprise features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests before committing
pytest --cov=app tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ElevenLabs](https://elevenlabs.io) for the amazing voice AI technology
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Bootstrap](https://getbootstrap.com/) for the responsive UI components
- [Chart.js](https://www.chartjs.org/) for beautiful data visualizations

## 📞 Support

- 📧 Email: support@taskvox.ai
- 💬 Discord: [Join our community](https://discord.gg/taskvox)
- 📖 Documentation: [docs.taskvox.ai](https://docs.taskvox.ai)
- 🐛 Bug Reports: [GitHub Issues](https://github.com/taskvox/issues)

---

**Built with ❤️ by the TasKvox AI Team**

*Empowering businesses with intelligent voice automation*