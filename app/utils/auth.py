from fastapi import Request
from app.db.database import database

async def get_current_user(request: Request):
    """Пытается получить текущего пользователя из куков, возвращает None, если пользователь не авторизован."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None  # Пользователь не авторизован
    
    query_user = "SELECT * FROM users WHERE id = :user_id"
    user = await database.fetch_one(query=query_user, values={"user_id": int(user_id)})
    if not user:
        return None  # Пользователь не найден
    
    return dict(user)  # Возвращаем пользователя как словарь
