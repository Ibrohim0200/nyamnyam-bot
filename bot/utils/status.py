def get_status_emoji(status: str) -> str:
    mapping = {
        "pending": "⏳",
        "to‘langan": "✅",
        "paid": "✅",
        "olib ketilgan": "📦",
        "delivered": "📦",
        "bekor qilingan": "❌",
        "cancelled": "❌",
    }
    return mapping.get(status.lower(), "❓")
