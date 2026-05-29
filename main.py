FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sobrescreva o CMD ao usar este Dockerfile para cada mock:
# docker-compose define o command por serviço
CMD ["python", "mock_antifraude.py"]
