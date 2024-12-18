from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.frontend.templates import templates
from app.db.database import database
from app.utils.auth import get_current_user
from typing import Optional


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request, user: Optional[dict] = Depends(get_current_user)):
    """Главная страница."""
    query_skins_for_sale = """
    SELECT skins.name, skin_sales.price, skin_sales.skin_id, inventory.user_id
    FROM skins
    JOIN skin_sales ON skins.id = skin_sales.skin_id
    JOIN inventory ON skins.id = inventory.skin_id
    WHERE skin_sales.status = 'active'
    """
    skins_for_sale = await database.fetch_all(query=query_skins_for_sale)
    skins_for_sale = [dict(skin) for skin in skins_for_sale]

    # Добавляем информацию о текущем пользователе, если он авторизован
    for skin in skins_for_sale:
        skin["is_owned_by_user"] = user and skin["user_id"] == user["id"]

    # Избранные скины пользователя
    favorite_skins = []
    if user:
        query_favorites = """
        SELECT skins.id AS skin_id, skins.name, skin_sales.price
        FROM skins
        JOIN favorites ON skins.id = favorites.skin_id
        JOIN skin_sales ON skins.id = skin_sales.skin_id
        WHERE favorites.user_id = :user_id AND skin_sales.status = 'active'
        """
        favorite_skins = await database.fetch_all(query=query_favorites, values={"user_id": user["id"]})
        favorite_skins = [dict(skin) for skin in favorite_skins]

        # Добавляем флаг "избранное"
        for skin in skins_for_sale:
            skin["is_favorite"] = any(fav["skin_id"] == skin["skin_id"] for fav in favorite_skins)
            skin["is_owned_by_user"] = skin["user_id"] == user["id"]

    return templates.TemplateResponse(
        "index.html", {
            "request": request,
            "skins": skins_for_sale,
            "favorite_skins": favorite_skins,
            "user": user,
        }
    )

@router.post("/remove_sale/{skin_id}")
async def remove_sale(skin_id: int, user=Depends(get_current_user)):
    """Снятие предмета с продажи."""
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Если пользователь администратор, он может снять любой предмет
    if user["is_admin"]:
        query = "DELETE FROM skin_sales WHERE skin_id = :skin_id"
        await database.execute(query=query, values={"skin_id": skin_id})
        return RedirectResponse(url="/", status_code=303)

    # Владелец может снять только свои предметы
    query_check = """
    SELECT 1 FROM inventory 
    WHERE skin_id = :skin_id AND user_id = :user_id
    """
    result = await database.fetch_one(query=query_check, values={"skin_id": skin_id, "user_id": user["id"]})
    if result:
        query = "DELETE FROM skin_sales WHERE skin_id = :skin_id"
        await database.execute(query=query, values={"skin_id": skin_id})
    return RedirectResponse(url="/", status_code=303)

# Добавление/удаление из избранного
@router.post("/favorites/{skin_id}")
async def toggle_favorite(skin_id: int, user=Depends(get_current_user)):
    """Добавление или удаление предмета из избранного."""
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Проверка: предмет уже в избранном?
    query_check = "SELECT 1 FROM favorites WHERE skin_id = :skin_id AND user_id = :user_id"
    result = await database.fetch_one(query=query_check, values={"skin_id": skin_id, "user_id": user["id"]})

    if result:
        # Удаляем из избранного
        query_delete = "DELETE FROM favorites WHERE skin_id = :skin_id AND user_id = :user_id"
        await database.execute(query_delete, values={"skin_id": skin_id, "user_id": user["id"]})
    else:
        # Добавляем в избранное
        query_insert = "INSERT INTO favorites (skin_id, user_id) VALUES (:skin_id, :user_id)"
        await database.execute(query_insert, values={"skin_id": skin_id, "user_id": user["id"]})

    return RedirectResponse(url="/", status_code=303)