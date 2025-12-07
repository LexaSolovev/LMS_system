# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Устанавливаем poetry
RUN pip install poetry

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock* /app/

# Настраиваем poetry
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root

# Копируем весь проект
COPY ./app/

# Команда по умолчанию
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]