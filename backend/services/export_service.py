"""
Transcript export (Markdown) and sharing (unauthenticated read-only link).

Markdown-only for export: it's readable directly, needs no extra system
dependency (a PDF path would mean adding weasyprint + its native libs to
an already dependency-heavy Dockerfile - see backend/Dockerfile - for a
feature that isn't the core product), and downloads cleanly from a browser
either way.
"""
import secrets
from typing import List

from models import ChatMessage, Conversation


def build_markdown_transcript(conversation: Conversation, messages: List[ChatMessage]) -> str:
    lines = [
        f"# {conversation.title or 'Untitled Conversation'}",
        "",
        f"*Exported from Scoratis*",
        "",
        "---",
        "",
    ]
    for msg in messages:
        speaker = "**You**" if msg.sender == "user" else "**Socrates**"
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else ""
        lines.append(f"{speaker} _{timestamp}_")
        lines.append("")
        lines.append(msg.message)
        lines.append("")
    return "\n".join(lines)


def generate_share_token() -> str:
    return secrets.token_urlsafe(24)
