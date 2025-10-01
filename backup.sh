#!/bin/bash

# === Настройки ===
CONTAINER="yauza_bot"                        # имя контейнера из docker-compose.yml
BACKUP_DIR="/home/backup"                    # куда сохраняем бэкапы
DATE=$(date +%F_%H-%M-%S)                    # текущая дата

# === Логика ===
mkdir -p $BACKUP_DIR

# Копируем базу из контейнера
docker cp $CONTAINER:/app/data/bot.sqlite3 $BACKUP_DIR/bot_$DATE.sqlite3

# Убираем старые бэкапы, храним только 7 последних
ls -tp $BACKUP_DIR/bot_*.sqlite3 | grep -v '/$' | tail -n +8 | xargs -r rm --

echo "✅ Бэкап сохранён: $BACKUP_DIR/bot_$DATE.sqlite3"
