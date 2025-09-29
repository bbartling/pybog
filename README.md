# 🏗️ PyBOG HVAC Control Builder

**Neo-Brutalism AI-Powered Wire Sheet Logic Generator for Niagara Workbench**

Transform HVAC control sequences into professional BOG files using AI analysis, React Flow visualization, and a beautiful neo-brutalism interface.

![PyBOG Interface](https://img.shields.io/badge/Interface-Neo--Brutalism-ff6b6b?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI-OpenAI%20GPT--4-00d4aa?style=for-the-badge)
![React Flow](https://img.shields.io/badge/UI-React%20Flow-61dafb?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge)

## ✨ Features

### 🎨 **Neo-Brutalism Interface**
- Bold, geometric design with sharp edges and high contrast
- React Flow-based chat canvas for interactive workflow visualization
- Real-time progress tracking with animated process steps
- File viewer modal for document analysis
- System health monitoring with service status indicators

### 🤖 **AI-Powered Analysis**
- **Document Processing**: Upload PDFs, DOCX, or TXT files with HVAC sequences
- **I/O Point Extraction**: Automatically identifies sensors, actuators, and control points
- **Control Block Identification**: Finds logical control sections (safety, scheduling, temperature, etc.)
- **Pseudocode Generation**: Creates structured wire sheet logic for Niagara Workbench
- **Quality Assessment**: Evaluates text completeness and HVAC terminology coverage

### 🔄 **Interactive Workflow**
- **Human-in-the-Loop**: Review and approve AI analysis before BOG generation
- **Real-time Updates**: WebSocket-powered progress streaming
- **Session Management**: Persistent chat sessions with full conversation history
- **File Storage**: Session-based file organization and retrieval
- **Iterative Design**: Modify analysis results and regenerate BOG files

### 📁 **BOG File Generation**
- **PyBOG Integration**: Full wire sheet logic compilation
- **Niagara Compatible**: Ready-to-import BOG files for Workbench
- **Structured Output**: Organized input/output points and control sequences
- **Download Management**: Secure file serving with session validation

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- OpenAI API Key
- 8GB RAM recommended

### 1. Clone and Setup
```bash
git clone <repository-url>
cd pybog
python start_pybog.py
```

### 2. Configure Environment
Edit `.env` file with your OpenAI API key:
```env
OPENAI_API_KEY=your_actual_openai_key_here
```

### 3. Access the Interface
- **Main App**: http://localhost:3001
- **API Docs**: http://localhost:8000/docs

- **Database UI**: http://localhost:5050

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Neo-Brutalism │────▶│   FastAPI +     │────▶│   PostgreSQL    │
│   React Flow UI │     │   LangChain     │     │   + Redis       │
│   (Port 3001)   │     │   (Port 8000)   │     │   + WebSocket   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                                  │
                           ┌──────▼──────┐
                           │   PyBOG     │
                           │  Generator   │
                           └─────────────┘
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


## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3001 | React UI with health monitoring |
| API | 8000 | FastAPI backend service |

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


## License

Proprietary - All rights reserved
