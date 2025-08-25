# Project Summary: RAG Document Query System

This project was developed for the HackRx hackathon as a Retrieval-Augmented Generation (RAG) agent system. It enables users to query insurance, legal, and other structured documents using natural language questions and receive accurate, context-aware answers.

## Key Features

- **Document Processing:** Supports PDF, DOC, and other formats. Documents are uploaded or referenced by URL.
- **Vector Embeddings:** Documents are processed and converted into vector embeddings for efficient retrieval.
- **Batch Question Answering:** Users can submit multiple questions in a single request. Questions are mapped to relevant document chunks.
- **LLM Integration:** Relevant document chunks are sent to a Large Language Model (LLM), which generates precise answers.
- **Complex Navigation:** The system can handle advanced queries, including web scraping and multi-step navigation for answers not directly in the document.
- **Modern Web Interface:** A responsive frontend allows users to submit documents, enter questions, and view results in real time.
- **Authentication:** API endpoints are protected and require an authentication token.

## Workflow

1. **User Submission:** Users provide a document (URL or upload) and a list of questions via the web interface.
2. **Backend Processing:** The backend (FastAPI) processes the document, extracts text, and generates vector embeddings.
3. **Question Mapping:** Each question is mapped to relevant document chunks using vector search.
4. **Answer Generation:** Chunks are sent to the LLM, which returns answers for each question.
5. **Response:** The frontend displays the answers to the user.

## Typical Use Cases

- Insurance policy analysis
- Legal document Q&A
- Automated document review for compliance and information extraction

## Project Structure

- [`src/backend.py`](src/backend.py): FastAPI backend application
- [`src/agent/`](src/agent/): Agent modules for vector storage, OCR, and search
- [`frontend/`](frontend/): Web interface (HTML, JS, CSS)
- [`data/`](data/): Document and processed text storage
- [`vector/`](vector/): Vector embeddings storage
- [`logs/`](logs/): Application logs

## How to Run

1. Install dependencies:  
   `pip install -r requirements.txt`
2. Start backend:  
   `cd src && python backend.py`
3. Access the web UI at:  
   `http://localhost:8000`

See [README.md](README.md) for more details.