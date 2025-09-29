FROM python:3.9-slim
WORKDIR /app

# Copy project files
COPY . /app

# Prefer pinned requirements if present
RUN pip install --no-cache-dir --upgrade pip
RUN if [ -f requirements_pinned.txt ]; then pip install --no-cache-dir -r requirements_pinned.txt; elif [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Expose FastAPI port
EXPOSE 8000

# By default run the uvicorn server, mounting artifacts externally is recommended for production
CMD ["sh", "-c", "uvicorn serve.app:app --host 0.0.0.0 --port 8000"]
