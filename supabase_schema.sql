-- Удаление таблиц, если они уже существуют (для чистой установки)
DROP TABLE IF EXISTS homework;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS lessons;
DROP TABLE IF EXISTS students;

-- Таблица студентов
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    level TEXT DEFAULT 'B1',
    contact TEXT,
    telegram_username TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица расписания уроков
CREATE TABLE lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    topic TEXT,
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица учета оплат
CREATE TABLE payments (
    student_id UUID PRIMARY KEY REFERENCES students(id) ON DELETE CASCADE,
    paid_lessons INTEGER DEFAULT 0,
    conducted_lessons INTEGER DEFAULT 0
);

-- Таблица домашних заданий
CREATE TABLE homework (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    assignment TEXT NOT NULL,
    status TEXT DEFAULT 'sent',
    check_result TEXT,
    grade TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблицы материалов
CREATE TABLE materials_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE materials_audio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    book_id TEXT,
    topic TEXT,
    level TEXT DEFAULT 'B2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создаем бакет для файлов (аудио, книги)
INSERT INTO storage.buckets (id, name, public) VALUES ('materials', 'materials', true) ON CONFLICT DO NOTHING;
