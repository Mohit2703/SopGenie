FROM python:3.11

# Prevent Python from writing pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy project
COPY . .

# Create directories
RUN mkdir -p media static staticfiles vectordb_data logs

# Make entrypoint executable
# COPY entrypoint.sh .
# RUN chmod +x entrypoint.sh

EXPOSE 8000

# ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "sop_rag.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "300"]
