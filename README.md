# RAG Document Query System

A powerful document analysis system using Retrieval-Augmented Generation (RAG) with a modern web interface.

## Features

- **Document Processing**: Support for PDF, DOC, and other document formats
- **Intelligent Q&A**: AI-powered question answering with context awareness
- **Complex Navigation**: Handle multi-step document navigation and URL scraping
- **Modern Web UI**: Clean, responsive frontend interface
- **Batch Processing**: Handle multiple questions simultaneously
- **Vector Search**: Efficient document retrieval using FAISS

## Project Structure

```
RAG/
├── src/                    # Source code
│   ├── backend.py         # FastAPI backend application
│   └── agent/             # AI agent modules
│       ├── agent.py       # Main agent logic
│       ├── localDatabase.py  # Vector database operations
│       ├── localOCR.py    # OCR and text extraction
│       └── search.py      # Search functionality
├── frontend/              # Web interface
│   ├── index.html         # Main HTML page
│   ├── script.js          # JavaScript functionality
│   ├── styles.css         # Custom styles
│   └── README.md          # Frontend documentation
├── data/                  # Data storage
│   ├── documents/         # Original documents (PDF, DOC, etc.)
│   ├── processed/         # Processed text files
│   └── temp/              # Temporary files
├── vector/                # Vector embeddings storage
├── logs/                  # Application logs
├── requirements.txt       # Python dependencies
├── main.py               # Main entry point
├── start.sh              # Shell startup script
└── README.md             # This file
```

## Quick Start

### Option 1: Using Python directly

```bash
python main.py
```

### Option 2: Using the shell script

```bash
./start.sh
```

### Option 3: Manual setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run from src directory
cd src
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

1. **Access the Web Interface**: Open http://localhost:8000
2. **Enter Document URL**: Provide the URL of the document to analyze
3. **Add Questions**: Enter one or more questions about the document
4. **Authentication**: Provide your API token
5. **Submit**: Click "Analyze Document" to get answers

## API Endpoints

- `GET /` - Web interface
- `GET /hackrx/run` - Health check
- `POST /hackrx/run` - Process documents and questions

## Configuration

Create a `.env` file with your configuration:

```env
TOKEN=your_secret_token_here
GOOGLE_API_KEY=your_google_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

## Dependencies

See `requirements.txt` for the complete list of Python dependencies.

## License

See LICENSE file for details.
