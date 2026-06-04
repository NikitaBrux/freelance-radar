FROM python:3.11-slim

WORKDIR /app

# Установить зависимости системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Установить Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать исходный код
COPY . .

CMD ["python", "bot/main.py"]
