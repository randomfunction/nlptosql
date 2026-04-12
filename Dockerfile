FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Run the backend server
EXPOSE 8000
CMD uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8000}
