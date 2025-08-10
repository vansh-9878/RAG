#!/usr/bin/env python3

"""
Main entry point for the RAG application.
This script allows running the backend from the root directory.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Change working directory to src for relative paths to work
os.chdir(src_dir)

# Import and run the backend
from backend import app
import uvicorn

if __name__ == "__main__":
    print("🤖 Starting RAG Document Query System...")
    print("Frontend available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
