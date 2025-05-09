# Безопасное хранение API-ключей

Этот документ описывает порядок безопасного хранения и использования API-ключей в проекте.

## Локальная разработка

1. Создайте файл `.env` в корне проекта на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Заполните `.env` вашими реальными API-ключами:
   ```
   TELEGRAM_BOT_TOKEN=your_real_token_here
   OPENAI_API_KEY=your_real_api_key_here
   ```

3. Файл `.env` добавлен в `.gitignore` и никогда не должен быть закоммичен в репозиторий.

## Настройка GitHub Actions

Для автоматического деплоя с GitHub Actions:

1. Перейдите в настройки репозитория на GitHub: Settings > Secrets and variables > Actions
2. Добавьте следующие секреты:
   - `TELEGRAM_BOT_TOKEN`: Токен вашего бота
   - `OPENAI_API_KEY`: Ключ API OpenAI
   - `ALLOWED_USERS`: Список ID пользователей, если требуется (через запятую)
   - Другие необходимые для деплоя секреты (SSH ключи, данные хостинга и т.д.)

## Разворачивание на сервере

### Вариант 1: Ручное развертывание

1. Клонируйте репозиторий на сервер
2. Установите зависимости: `pip install -r requirements.txt`
3. Создайте файл `.env` с вашими API-ключами
4. Запустите бота: `python src/main.py`

### Вариант 2: Использование Docker

1. Создайте на сервере файл `.env` с API-ключами
2. Запустите контейнер с монтированием файла `.env`:
   ```bash
   docker run -d --name book-bot --restart unless-stopped \
     --env-file .env \
     your-username/telegram-book-bot
   ```

### Вариант 3: Systemd сервис

1. Создайте файл `/etc/systemd/system/telegram-book-bot.service`:
   ```ini
   [Unit]
   Description=Telegram Book Bot
   After=network.target
   
   [Service]
   User=username
   WorkingDirectory=/path/to/bot
   ExecStart=/path/to/venv/bin/python src/main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

2. Создайте файл `.env` в директории `/path/to/bot`
3. Активируйте и запустите сервис:
   ```bash
   sudo systemctl enable telegram-book-bot
   sudo systemctl start telegram-book-bot
   ```

## Управление доступом к боту

В режиме `ENVIRONMENT=production` бот проверяет ID пользователей и разрешает использование только тем, кто указан в `ALLOWED_USERS`.

Чтобы узнать свой Telegram ID, можно использовать бота [@userinfobot](https://t.me/userinfobot).

## Best-practice

1. Используйте разные API-ключи для разработки и продакшена
2. Периодически обновляйте ключи (особенно если они могли быть скомпрометированы)
3. Установите лимиты на использование API, чтобы избежать неожиданных расходов
4. Для OpenAI API настройте бюджет и оповещения о приближении к лимиту 