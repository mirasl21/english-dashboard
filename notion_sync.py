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
        new_page = client.pages.create(
            parent={"database_id": database_id},
            properties={
                "Student": {"title": [{"text": {"content": student_name}}]},
                "Date": {"date": {"start": lesson_date}},
                "Time": {"rich_text": [{"text": {"content": lesson_time}}]},
                "Topic": {"rich_text": [{"text": {"content": topic or "—"}}]},
                "Status": {"select": {"name": status}},
            },
        )
        return new_page["id"]
    except Exception:
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
            props["Date"] = {"date": {"start": new_date}}
        if new_time:
            props["Time"] = {"rich_text": [{"text": {"content": new_time}}]}
        client.pages.update(page_id=page_id, properties=props)
        return True
    except Exception:
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
