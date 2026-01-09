# OpenRedact Clinical

Medical document anonymization for German clinical documents - A modern, secure application built with Python 3.11, FastAPI, React 18, and TypeScript.

## 🎯 Overview

OpenRedact Clinical is a production-ready application designed to anonymize sensitive information in German medical documents. This repository represents a complete modernization from legacy technologies to a modern, secure, and maintainable stack.

### Key Features

- 🔒 **Security First**: No known CVEs in dependencies
- 🚀 **Modern Stack**: Python 3.11, FastAPI 0.115, React 18, TypeScript 5.5
- 🏥 **Medical Focus**: Specialized NLP models for German clinical text
- 📄 **PDF Processing**: Complete PDF handling and anonymization
- 🐳 **Containerized**: Docker-based deployment for consistency
- ⚡ **Developer Friendly**: Hot reload, TypeScript, modern tooling

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Python 3.11
- FastAPI 0.115.0 (Web framework)
- Spacy 3.7.5 & Stanza 1.8.2 (NLP)
- PyTorch 2.3.1 (Machine learning)
- Gunicorn + Uvicorn (Production server)

**Frontend:**
- React 18.3.1
- TypeScript 5.5.4
- Vite 5.4.0 (Build tool)
- Blueprint.js 5.12.0 (UI components)
- Nginx (Production server)

**Infrastructure:**
- Docker & Docker Compose
- Multi-stage builds for optimization
- Development and production configurations

## 🚀 Quick Start

### Prerequisites

- Docker 24.0+
- Docker Compose 2.0+
- 8GB RAM minimum (for NLP models)
- 10GB disk space

### Production Deployment

```bash
# Clone the repository
git clone https://github.com/jojospausch-web/openredact-clinical.git
cd openredact-clinical

# Build and start services
docker-compose build
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Access the application
open http://localhost
```

### Development Setup

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up

# Backend runs on: http://localhost:8000
# Frontend runs on: http://localhost:5173
```

The development setup includes:
- ✅ Backend auto-reload on code changes
- ✅ Frontend hot module replacement (HMR)
- ✅ Volume mounts for live editing
- ✅ Detailed logging

## 📁 Project Structure

```
openredact-clinical/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py          # FastAPI application
│   ├── Dockerfile           # Production backend image
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── main.tsx         # Application entry point
│   │   └── ...
│   ├── Dockerfile           # Production frontend image
│   ├── Dockerfile.dev       # Development frontend image
│   ├── package.json         # Node dependencies
│   ├── vite.config.ts       # Vite configuration
│   ├── tsconfig.json        # TypeScript configuration
│   └── nginx.conf           # Nginx production config
├── docker-compose.yml       # Production orchestration
├── docker-compose.dev.yml   # Development orchestration
└── .github/
    └── workflows/
        └── ci.yml           # CI/CD pipeline
```

## 🔧 Development

### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Run tests
pytest

# Format code
black .

# Check code quality
pip install flake8
flake8 app/
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Run linter
npm run lint

# Format code
npm run format

# Build for production
npm run build
```

### Running Tests Locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pytest
```

**Frontend:**
```bash
cd frontend
npm ci
npm run build
```

## 🔐 Security

This project prioritizes security:

- ✅ All dependencies vetted for known CVEs
- ✅ Regular dependency updates
- ✅ Multi-stage Docker builds (minimal attack surface)
- ✅ No secrets in code or containers
- ✅ CORS properly configured
- ✅ Secure defaults

### Dependency Versions (as of January 2026)

All dependencies are on stable, supported versions with 3-5 year expected lifespan.

## 🌐 API Documentation

Once running, visit:
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative API docs)
- **Health Check**: http://localhost:8000/health

## 📊 CI/CD

GitHub Actions automatically:
- ✅ Tests backend on every push/PR
- ✅ Builds frontend on every push/PR
- ✅ Validates Docker builds
- ✅ Runs on Python 3.11 and Node 20

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issue: NLP models not downloaded
docker-compose exec backend python -m spacy download de_core_news_sm
```

### Frontend build fails

```bash
# Clear node_modules and reinstall
docker-compose down
rm -rf frontend/node_modules
docker-compose build --no-cache frontend
```

### Port conflicts

```bash
# Check what's using ports 80 and 8000
lsof -i :80
lsof -i :8000

# Or change ports in docker-compose.yml
```

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style (Black for Python, Prettier for TypeScript)
- Write tests for new features
- Update documentation as needed
- Ensure CI passes before requesting review

## 📝 License

This project is proprietary. All rights reserved.

## 🙏 Acknowledgments

- Built on the foundation of the original openredact-app
- Uses Spacy and Stanza for German NLP
- UI components from Blueprint.js

## 📞 Support

For issues and questions:
- 🐛 Report bugs via GitHub Issues
- 💬 Discussions via GitHub Discussions
- 📧 Email: [your-email]

## 🗺️ Roadmap

This is PR #1 of the modernization project. Future PRs will add:
- Complete anonymization logic migration
- Advanced PDF processing features
- User authentication and authorization
- Batch processing capabilities
- Admin dashboard
- API rate limiting
- Monitoring and logging integration

---

**Status**: ✅ Infrastructure Complete (PR #1)
**Version**: 2.0.0
**Last Updated**: January 2026