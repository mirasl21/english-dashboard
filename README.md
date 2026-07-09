# 📚 English Teacher Dashboard

AI-powered toolkit for online English teachers — grammar checking, quiz generation, vocabulary extraction, textbook scanning, lesson planning, scheduling, payment tracking, homework checking, and more.

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

**Required:** `SUPABASE_URL` and `SUPABASE_KEY`  
**Optional:** `NOTION_TOKEN`, `NOTION_DB_ID`, `OPENAI_API_KEY`

### 3. Set up the database

Run the SQL from `supabase_schema.sql` in your Supabase SQL Editor to create the required tables.

### 4. Run the app

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### 5. (Optional) Run the Telegram bot

```bash
python telegram_bot.py
```

## 🧩 Features

| Tab | Description |
|-----|-------------|
| ✅ Grammar Checker | AI-powered grammar and style analysis of student writing |
| 🧠 Quiz Generator | Generate multiple-choice quizzes on any grammar topic |
| 📖 Vocabulary Builder | Extract complex vocabulary from reading passages |
| 📷 Textbook Scanner | Upload textbook photos → auto-generate exercises |
| 🗓️ Lesson Planner | Plan 60-minute lessons (from image or topic) |
| 📅 Schedule | Manage lesson timetable + AI message parser |
| 💰 Payments | Track paid/conducted lessons per student |
| 📝 Homework Check | AI homework checking (text or photo) |
| 📚 Materials | Book library + material generation |
| 🎧 Listening | Audio file library with comprehension questions |

## 🛠 Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python, Supabase (PostgreSQL)
- **AI:** OpenAI GPT-4o / Google Gemini 1.5 Pro
- **Integrations:** Notion, Telegram (Telethon userbot)

## 📁 Project Structure

```
├── app.py                 # Main Streamlit application
├── data_manager.py        # Database operations (Supabase + local JSON)
├── notion_sync.py         # Notion calendar integration
├── telegram_bot.py        # Telegram userbot for student communication
├── paste_component/       # Custom Streamlit component for clipboard paste
├── .streamlit/config.toml # Streamlit theme configuration
├── supabase_schema.sql    # Database schema
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variables template
├── Dockerfile             # Docker deployment
├── Procfile               # Heroku/Railway deployment
└── start.sh               # Combined startup script
```

## 🐳 Docker Deployment

```bash
docker build -t english-dashboard .
docker run -p 8501:8501 --env-file .env english-dashboard
```
