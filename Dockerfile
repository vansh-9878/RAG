FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    pip3 install --upgrade pip

# Copy project
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8080"]
