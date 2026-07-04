"""
notion_sync.py — Optional Notion integration for schedule synchronisation.

The teacher provides:
  1. A Notion Internal Integration Token  (in sidebar)
  2. A Notion Database ID                (in sidebar)

The module pushes lesson records to a Notion database and can pull changes back.
"""

from typing import Optional


def _get_client(token: str):
    """Lazy-import and return a Notion client."""
    from notion_client import Client
    return Client(auth=token)

def _get_notion_date_dict(date_str: str, time_str: Optional[str]) -> dict:
    """Format the date and time for Notion, including a 1-hour duration and timezone."""
    if not time_str:
        return {"start": date_str}
    
    # Parse time_str and add 1 hour for the end time
    try:
        hours, minutes = map(int, time_str.split(':'))
        end_hours = (hours + 1) % 24
        end_time_str = f"{end_hours:02d}:{minutes:02d}"
        
        # We append +05:00 so Notion doesn't treat it as UTC and shift it by 5 hours.
        return {
            "start": f"{date_str}T{time_str}:00+05:00",
            "end": f"{date_str}T{end_time_str}:00+05:00"
        }
    except Exception:
        # Fallback if time parsing fails
        return {"start": f"{date_str}T{time_str}:00+05:00"}


# ═══════════════════════════════════════════════════════════════════════════════
# PUSH — Send lesson to Notion
# ═══════════════════════════════════════════════════════════════════════════════

def push_lesson_to_notion(
    token: str,
    database_id: str,
    student_name: str,
    lesson_date: str,
    lesson_time: str,
    topic: str,
    status: str = "Scheduled",
) -> Optional[str]:
    """Create or update a page in the Notion database.
    Returns the Notion page ID on success, None on failure."""
    try:
        client = _get_client(token)
        # Combine date and time for Notion calendar block representation
        date_obj = _get_notion_date_dict(lesson_date, lesson_time)
        
        new_page = client.pages.create(
            parent={"database_id": database_id},
            properties={
                "Student": {"title": [{"text": {"content": student_name}}]},
                "Date": {"date": date_obj},
                "Time": {"rich_text": [{"text": {"content": lesson_time}}]},
                "Topic": {"rich_text": [{"text": {"content": topic or "—"}}]},
                "Status": {"select": {"name": status}},
            },
        )
        return new_page["id"]
    except Exception as e:
        print(f"Error pushing lesson to Notion: {e}")
        return None


def find_lesson_in_notion(token: str, database_id: str, student_name: str, lesson_date: str) -> Optional[str]:
    """Find a lesson in Notion by student name and date. Returns page_id if found."""
    import httpx
    try:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        payload = {
            "filter": {
                "and": [
                    {"property": "Student", "title": {"equals": student_name}},
                    {"property": "Date", "date": {"equals": lesson_date}}
                ]
            }
        }
        response = httpx.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            return data["results"][0]["id"]
        return None
    except Exception as e:
        print(f"Error finding lesson in Notion: {e}")
        return None


def update_lesson_in_notion(
    token: str,
    page_id: str,
    status: str,
    new_date: Optional[str] = None,
    new_time: Optional[str] = None,
) -> bool:
    """Update an existing Notion page (e.g. after rescheduling)."""
    try:
        client = _get_client(token)
        props: dict = {
            "Status": {"select": {"name": status}},
        }
        if new_date:
            props["Date"] = {"date": _get_notion_date_dict(new_date, new_time)}
        if new_time:
            props["Time"] = {"rich_text": [{"text": {"content": new_time}}]}
        client.pages.update(page_id=page_id, properties=props)
        return True
    except Exception as e:
        print(f"Error updating lesson in Notion: {e}")
        return False


def test_notion_connection(token: str, database_id: str) -> tuple[bool, str]:
    """Verify that the token + database ID are valid.
    Returns (success: bool, message: str)."""
    try:
        client = _get_client(token)
        db = client.databases.retrieve(database_id=database_id)
        title_parts = db.get("title", [])
        db_name = title_parts[0]["plain_text"] if title_parts else "Untitled"
        return True, f"✅ Connected to Notion database: «{db_name}»"
    except Exception as e:
        return False, f"❌ Connection failed: {e}"
