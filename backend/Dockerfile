# 1. Використовуєте легкий образ Python
FROM python:3.12-slim

# 2. Встановлюєте робочу директорію всередині контейнера
WORKDIR /app

# 3. Запобігаємо створенню pycache (сміття)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. Копіюєте файл залежностей і встановлюємо їх
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копіюєте весь код бекенду в контейнер
COPY . .

# 6. Відкриваєте порт 5000
EXPOSE 5000

# 7. Команда запуску
CMD ["python", "app.py"]