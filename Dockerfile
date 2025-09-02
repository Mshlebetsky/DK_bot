# ==========================
# Базовый образ
# ==========================
FROM python:3.11-slim

LABEL authors="Mihail"

# ==========================
# Переменные окружения
# ==========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ="Europe/Moscow"

# ==========================
# Установка системных зависимостей
# ==========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    wget \
    curl \
    unzip \
    gnupg \
    libnss3 \
    libxi6 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxdamage1 \
    libxrandr2 \
    libgbm-dev \
    libgtk-3-0 \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ==========================
# Установка Google Chrome
# ==========================
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ==========================
# Рабочая директория
# ==========================
WORKDIR /app

# ==========================
# Установка Python-зависимостей
# ==========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================
# Копируем проект
# ==========================
COPY . .

# ==========================
# Создание пользователя
# ==========================
RUN useradd -ms /bin/bash appuser \
    && mkdir -p /app/data /app/logs \
    && chown -R appuser:appuser /app
USER appuser

# ==========================
# Переменные окружения по умолчанию
# ==========================
ENV DB_LITE="sqlite+aiosqlite:///data/bot.sqlite3"

# ==========================
# Запуск
# ==========================
CMD ["python", "app.py"]
