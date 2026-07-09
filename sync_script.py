import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv(override=True)
from data_manager import get_students, get_all_lessons
from notion_sync import push_lesson_to_notion, find_lesson_in_notion

students = get_students()
student_map = {s['id']: s['name'] for s in students}

db_lessons = get_all_lessons()

added = 0
for l in db_lessons:
    s_name = student_map.get(l['student_id'], 'Unknown')
    key = f"{s_name}_{l.get('date')}_{l.get('time')}"
    
    # Check if lesson exists in Notion
    existing = find_lesson_in_notion(os.environ['NOTION_TOKEN'], os.environ['NOTION_DB_ID'], s_name, l.get('date'))
    if not existing:
        print(f'Syncing missing lesson to Notion: {key}')
        try:
            push_lesson_to_notion(
                os.environ['NOTION_TOKEN'], 
                os.environ['NOTION_DB_ID'], 
                s_name, 
                l.get('date'), 
                l.get('time'), 
                l.get('topic', '')
            )
            added += 1
        except Exception as e:
            print(f'Failed {key}: {e}')

print(f'Sync complete. Added {added} lessons to Notion.')
