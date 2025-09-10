# DK_bot

Telegram-бот для Дома культуры «Яуза».

## 🚀 Функционал
- Рассылка анонсов и новостей.
- Запись пользователей на мероприятия.
- Подписка/отписка на рассылки по категориям.
- Получение информации о расписании, контактах и локации.
- Админ-команды для управления мероприятиями и рассылками.

## 📂 Структура проекта
- `app.py` — точка входа.
- `handlers/` — обработчики команд и кнопок.
- `logic/` — логика и парсинг.
- `middlewares/` — промежуточные слои (логирование, проверка админов).
- `database/`, `data/` — хранение данных.
- `replyes/` — шаблоны ответов и клавиатур.
- `Dockerfile`, `docker-compose.yml` — контейнеризация.

## 🔧 Запуск проекта

### Локально
```bash
git clone https://github.com/Mshlebetsky/DK_bot.git
cd DK_bot
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
python app.py
```
Docker
```
git clone https://github.com/Mshlebetsky/DK_bot.git
cd DK_bot
cp .env.example .env
docker compose up --build -d
```
⚙️ Переменные окружения

Структура .env :
```
TOKEN=
DB_LITE=sqlite+aiosqlite:///my_base.db
ADMINS_LIST=
```

📝 Лицензия

Проект для ДК «Яуза». Использование вне организации требует согласования.
