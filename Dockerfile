
FROM python:3.12-slim

# Dossier de travail dans le conteneur
WORKDIR /app

# Configuration Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY fog ./fog
COPY shared ./shared

# Port utilisé par chaque Fog Node
EXPOSE 8000

# Démarrer l'API FastAPI
CMD ["uvicorn", "fog.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
