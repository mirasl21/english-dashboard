FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости системы (для работы некоторых библиотек, если понадобятся)
RUN apt-get update && apt-get install -y gcc

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы проекта
COPY . .

# Даем права на запуск скрипта
RUN chmod +x start.sh

# Открываем порт для Streamlit
EXPOSE 8501

# Запускаем скрипт, который поднимает и бота, и сайт
CMD ["./start.sh"]
