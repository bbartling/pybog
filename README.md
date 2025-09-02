# PyBOG Workbench - Quick Start Guide

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API Key
- 8GB+ RAM recommended

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your OpenAI API key
# OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Start All Services
```bash
# Build and start all containers
docker-compose up --build -d

# Check service status
docker-compose ps
```

### 3. Access Applications
- **PyBOG Workbench**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **N8N Workflow Engine**: http://localhost:5678

### 4. Import N8N Workflow
1. Open N8N at http://localhost:5678
2. Go to Workflows -> Import from file
3. Import: `workflow_data/pybog-enhanced-agent-v3.json`
4. Activate the workflow

### 5. Test the System
```bash
# Run integration tests
python test_integration.py
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React Frontend │    │   FastAPI       │    │  N8N Workflow   │
│  (Port 3000)    │◄──►│   API Server    │◄──►│  Engine         │
│                 │    │  (Port 8000)    │    │  (Port 5678)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌─────────────────────┐
                    │   PostgreSQL DB     │
                    │   (Port 5432)       │
                    └─────────────────────┘
```

## 🎯 Features

### Frontend (Niagara Workbench Style)
- **Industrial Design**: Matches Tridium N4 Workbench appearance
- **Control Point Messages**: Chat bubbles styled like control components
- **Zebra Striping**: Familiar workbench table styling
- **Document Management**: Upload and manage HVAC sequences
- **BOG File Palette**: Download generated control files
- **Real-time Chat**: Interactive AI assistant

### Backend (PyBOG API)
- **BOG Generation**: Create Niagara-compatible control files
- **Schema Validation**: Verify HVAC component definitions
- **Document Processing**: Extract control sequences from PDFs/DOCX
- **RESTful API**: Clean, documented endpoints

### Workflow Engine (N8N)
- **AI Integration**: OpenAI GPT for document analysis
- **Document Processing**: PDF/DOCX text extraction
- **Control Logic**: Intelligent sequence generation
- **Extensible**: Add custom nodes and integrations

## 📁 Project Structure

```
pybog/
├── frontend/              # React Workbench Interface
│   ├── src/
│   │   ├── App.tsx       # Main Workbench component
│   │   ├── App.css       # Niagara styling
│   │   └── services/     # API integration
│   ├── public/           # Static assets
│   └── Dockerfile        # Frontend container
│
├── api/                  # FastAPI Backend
│   └── main.py          # Core API endpoints
│
├── bog_builder/          # PyBOG Core Library
│   ├── builder.py       # BOG file builder
│   ├── models.py        # Pydantic validation
│   └── analyzer.py      # BOG analyzer
│
├── workflow_data/        # N8N Workflows
│   └── pybog-enhanced-agent-v3.json
│
├── data/
│   ├── outputs/         # Generated BOG files
│   └── uploads/         # Document uploads
│
├── docker-compose.yml   # Service orchestration
└── test_integration.py  # System tests
```

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm install
npm start
```

### API Development
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Test API endpoints
python test_integration.py

# Test BOG generation
python test_core_functionality.py
```

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
docker-compose down -v
docker-compose up --build
```

**N8N workflow not working:**
- Check OpenAI API key in environment
- Verify workflow is activated
- Check webhook endpoint is accessible

**Frontend not connecting to API:**
- Verify API is running on port 8000
- Check CORS settings in API
- Verify network configuration

**BOG generation failing:**
- Check input/output definitions
- Verify component names are valid
- Check logs: `docker-compose logs api`

### Logs
```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs frontend
docker-compose logs api
docker-compose logs n8n
```

## 📖 API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints

- `GET /api/health` - System health check
- `POST /api/validate-schema` - Validate HVAC schema
- `POST /api/generate-bog` - Generate BOG file
- `GET /api/download/{session_id}/{filename}` - Download BOG file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test with `test_integration.py`
5. Submit pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🆘 Support

For issues and support:
1. Check troubleshooting section
2. Review logs for errors
3. Create GitHub issue with details