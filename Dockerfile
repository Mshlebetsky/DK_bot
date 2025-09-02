# Dockerfile
FROM python:3.11-slim
LABEL authors="Mihail"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ТЗ: APScheduler с таймзоной → поставим tzdata
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Слой зависимостей (кэшируется)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY . .

# Подготовка директорий под БД и логи
RUN useradd -ms /bin/bash appuser \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app

USER appuser

# Значения по умолчанию (можно переопределить в compose)
ENV DB_LITE="sqlite+aiosqlite:///data/bot.sqlite3" \
    TZ="Europe/Moscow"

# Портов не открываем — бот инициирует исходящие соединения
CMD ["python", "app.py"]
