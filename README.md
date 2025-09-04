# PyBOG Control Builder

HVAC Control Sequence to Niagara BOG File Generator

## Overview

PyBOG Control Builder is a dockerized application that converts HVAC control sequence documents into Niagara Workbench BOG (Building Object Graph) files using AI-powered analysis.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│     n8n     │
│   (React)   │     │   (FastAPI) │     │  (Workflow) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                    │
       └───────────────────┴────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL  │
                    │   + Redis    │
                    └──────────────┘
```

## Quick Start

1. **Prerequisites**
   - Docker Desktop
   - OpenAI API Key

2. **Environment Setup**
   ```bash
   # Create .env file with:
   OPENAI_API_KEY=your-api-key-here
   ```

3. **Start Application**
   ```bash
   docker-compose up -d
   ```

4. **Access Application**
   - Frontend: http://localhost:3001
   - API: http://localhost:8000/docs
   - n8n: http://localhost:5678

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | React UI with health monitoring |
| API | 8000 | FastAPI backend service |
| n8n | 5678 | Workflow automation engine |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache layer |

## Features

- 📄 **Document Upload** - Process PDF/TXT HVAC control documents
- 🤖 **AI Analysis** - Extract control sequences, I/O points, and logic
- ✅ **Review & Approval** - Interactive review process with feedback
- 🏗️ **BOG Generation** - Generate Niagara-compatible BOG files
- 📊 **Health Monitoring** - Real-time service status
- 🔍 **Debug Console** - Built-in logging and debugging

## Development

### Project Structure
```
pybog/
├── api/               # Backend FastAPI service
├── bog_builder/       # BOG file generation logic
├── frontend/          # React frontend
├── data/             # File storage
├── docker-compose.yml # Service orchestration
└── README.md         # This file
```

### Development Mode
```bash
# Frontend with hot reload
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# View logs
docker-compose logs -f [service-name]
```

## Usage Workflow

1. **Upload Document** - Upload HVAC control sequence PDF or text file
2. **AI Analysis** - System extracts control points and logic
3. **Review** - Review extracted information, request changes if needed
4. **Generate** - Approve to generate BOG file
5. **Download** - Download generated BOG for Niagara Workbench

## Troubleshooting

- **Services not starting**: Check Docker Desktop is running
- **API errors**: Verify OPENAI_API_KEY in .env file
- **Frontend not loading**: Clear browser cache, check port 3001
- **n8n webhook errors**: Ensure workflow is active in n8n interface

## License

Proprietary - All rights reserved
