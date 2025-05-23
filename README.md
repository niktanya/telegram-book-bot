# Telegram Book Bot

Телеграм-бот для поиска книг по описанию/автору/названию и получения рекомендаций на основе книг, которые понравились пользователю.

## Функциональность
- Поиск книг по описанию, автору или названию через API GPT
- Рекомендации книг на основе введенной пользователем книги через коллаборативную фильтрацию или API GPT

## Установка и запуск
```bash
# Клонирование репозитория
git clone https://github.com/your-username/telegram-book-bot.git
cd telegram-book-bot

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Заполните .env вашими ключами API

# Запуск бота
python src/main.py
```

## Структура проекта
- `src/` - исходный код бота
  - `main.py` - главный файл для запуска бота
  - `bot/` - код для работы с Telegram API
  - `services/` - сервисы для работы с внешними API и рекомендательной системой
  - `models/` - модели данных
  - `utils/` - вспомогательные функции
- `data/` - данные для работы рекомендательной системы
- `tests/` - тесты

## Требуемые API ключи
- Telegram Bot API token
- OpenAI API key (для GPT)
