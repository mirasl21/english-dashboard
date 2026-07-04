#!/bin/bash
# Запускаем бота в фоновом режиме
python telegram_bot.py &

# Запускаем Streamlit на нужном порту
streamlit run app.py --server.port="${PORT:-8501}" --server.address="0.0.0.0"
