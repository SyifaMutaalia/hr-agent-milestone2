FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY app.py ui_contract.py demo_personas.json ./
COPY tests/ ./tests/

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

# FastAPI port
EXPOSE 8000

# Default command for API
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
