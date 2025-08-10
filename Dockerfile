# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port 8080
EXPOSE 8080

# Set working directory to src for running backend.py
WORKDIR /app/src

# Run the backend server with output redirected to logs
CMD cd src && python backend.py > ../logs/test.txt