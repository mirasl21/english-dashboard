import streamlit as st
import os
import requests

def render():
    st.title("💡 Путеводитель и Обратная связь")
    st.markdown("Добро пожаловать в панель преподавателя! Ниже описаны основные возможности платформы.")

    # ─── GUIDE SECTION ──────────────────────────────────────────────
    with st.expander("📖 Как пользоваться сайтом", expanded=True):
        st.markdown("""
        ### 👥 Ученики и Оплаты
        - В боковом меню слева вы можете добавлять новых учеников, указывая их **Имя**, **Уровень** и **Часовой пояс**.
        - Во вкладке **💰 Payments** вы можете отмечать оплаченные абонементы. Баланс уроков будет списываться автоматически после проведения каждого занятия.
        
        ### 🤖 Telegram Бот
        Ваш личный ассистент в Telegram умеет делать две главные вещи:
        1. **Изменять расписание:** Напишите боту «Запиши Мирасу 4 урока каждый вторник в 15:00». Бот поймет часовой пояс ученика и добавит уроки! Также можно переносить и отменять занятия.
        2. **Проверять домашку:** Отправьте боту текст на английском языке (или фото текста) и припишите слово «проверь». Он автоматически найдет ошибки, выставит оценку и покажет правильный вариант.
        
        ### 📚 Умные Вкладки (ИИ)
        - **Grammar & Vocab:** Генерируйте объяснения правил и списки слов под уровень ученика.
        - **Lesson Planner:** Автоматически создавайте подробный план урока по любой теме.
        - **Listening:** Генерируйте аудио-истории и диалоги по текстам.
        - **Materials:** Собирайте всё сгенерированное в единый PDF документ.
        
        ### 📓 Notion
        Если вы подключили ключи в меню слева, сайт будет автоматически дублировать всех учеников и расписание в вашу базу данных Notion.
        """)

    # ─── FEEDBACK SECTION ──────────────────────────────────────────────
    st.divider()
    st.markdown("### 💬 Обратная связь")
    st.info("Нашли баг? Есть идея для новой функции? Напишите разработчику, и он сразу получит это сообщение в Telegram!")
    
    with st.form("feedback_form", clear_on_submit=True):
        fb_type = st.selectbox("Тип сообщения", ["🐞 Сообщить об ошибке (Bug)", "✨ Предложить идею (Feature)", "❓ Вопрос"])
        fb_text = st.text_area("Ваше сообщение", placeholder="Опишите проблему или идею как можно подробнее...", height=150)
        submitted = st.form_submit_button("🚀 Отправить", use_container_width=True)
        
        if submitted:
            if not fb_text.strip():
                st.warning("Пожалуйста, напишите текст сообщения.")
            else:
                token = os.environ.get("TELEGRAM_BOT_TOKEN")
                dev_id = os.environ.get("DEVELOPER_TELEGRAM_ID") or os.environ.get("TEACHER_TELEGRAM_ID")
                
                if token and dev_id:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    message = f"🆕 **ОТЗЫВ С САЙТА**\n\n**Тип:** {fb_type}\n**Сообщение:**\n{fb_text}"
                    try:
                        resp = requests.post(url, json={"chat_id": dev_id, "text": message, "parse_mode": "Markdown"})
                        if resp.status_code == 200:
                            st.success("✅ Спасибо! Ваше сообщение успешно отправлено разработчику.")
                            st.balloons()
                        else:
                            st.error(f"⚠️ Ошибка отправки (Код {resp.status_code}).")
                    except Exception as e:
                        st.error(f"⚠️ Ошибка подключения: {e}")
                else:
                    # Fallback if no telegram bot configured
                    try:
                        with open("feedback.log", "a", encoding="utf-8") as f:
                            f.write(f"[{fb_type}] {fb_text}\n---\n")
                        st.success("✅ Спасибо! Ваше сообщение сохранено (Telegram бот не настроен).")
                    except:
                        st.error("⚠️ Не удалось сохранить сообщение.")
