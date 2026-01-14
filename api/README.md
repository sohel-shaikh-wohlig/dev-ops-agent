### 🚀 Quick Start

```
# 1. Clone the repository
git clone <repository-url>
cd gitops-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your configuration

# 5. Run the application
uvicorn main:app --reload

# 6. Access API documentation
# Open http://localhost:8000/api/docs
```

### Docker Development
```
# 1. Build and run with docker-compose
docker-compose -f docker-compose.dev.yml up --build

# 2. Access API
# http://localhost:8000
```

### 📚 API Documentation
Interactive Documentation

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

OpenAPI JSON: http://localhost:8000/openapi.json