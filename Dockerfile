# Image officielle Playwright pour Python (inclut navigateurs + deps système)
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier ton code
COPY . .

# Optionnel mais utile pour logs en temps réel
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Lance l'API
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
