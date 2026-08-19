FROM python:3.10-slim

WORKDIR /app

# Install dependencies needed for sentence-transformers and compiling C extensions if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose port (Hugging Face uses port 7860 by default for Docker spaces)
EXPOSE 7860

# Command to run the application (Bind to 0.0.0.0 and port 7860)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
