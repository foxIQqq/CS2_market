from app.db.database import database

async def log_history(user_id: int, action_type: str, description: str = None):
    """Добавляет запись в таблицу history."""
    query = """
    INSERT INTO history (user_id, action_type, description)
    VALUES (:user_id, :action_type, :description)
    """
    await database.execute(query, values={"user_id": user_id, "action_type": action_type, "description": description})
