from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi import HTTPException
from app.db.database import database
from app.utils.auth import get_current_user
from app.frontend.templates import templates
from starlette.status import HTTP_303_SEE_OTHER
from app.utils.logger import log_history



router = APIRouter()

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user=Depends(get_current_user)):
    """Страница профиля пользователя."""
    if not user:  # Проверяем, что пользователь авторизован
        return RedirectResponse(url="/login", status_code=303)
    
    # Проверка, является ли пользователь администратором
    if user["is_admin"]:
        # Получаем список всех пользователей
        query_users = "SELECT id, username, balance FROM users"
        all_users = await database.fetch_all(query=query_users)
        all_users = [dict(u) for u in all_users]

    
        # Получаем список всех предметов на продаже
        query_skins = """
        SELECT skin_sales.skin_id, skins.name
        FROM skin_sales
        JOIN skins ON skin_sales.skin_id = skins.id
        WHERE skin_sales.status = 'active'
        """
        skins_for_removal = await database.fetch_all(query=query_skins)
        skins_for_removal = [dict(skin) for skin in skins_for_removal]

        return templates.TemplateResponse(
            "admin_profile.html", 
            {
                "request": request,
                "users": all_users,
                "skins_for_removal": skins_for_removal,
                "user": user
            }
        )

    query_user_skins = """
    SELECT 
        skins.name, 
        COALESCE(skin_sales.price, skins.price) AS price, -- Берём цену из skin_sales, если есть
        skins.id,
        CASE 
            WHEN inventory.status = 'for_sale' THEN TRUE
            ELSE FALSE
        END AS is_for_sale
    FROM inventory
    JOIN skins ON inventory.skin_id = skins.id
    LEFT JOIN skin_sales ON skins.id = skin_sales.skin_id AND skin_sales.status = 'active' -- Подключаем таблицу skin_sales
    WHERE inventory.user_id = :user_id
    """
    user_skins = await database.fetch_all(query=query_user_skins, values={"user_id": user["id"]})
    user_skins = [dict(skin) for skin in user_skins]

    # Получаем баланс текущего пользователя
    query_balance = "SELECT balance FROM users WHERE id = :user_id"
    user_balance = await database.fetch_one(query=query_balance, values={"user_id": user["id"]})

    return templates.TemplateResponse(
        "profile.html", {
            "request": request,
            "user_skins": user_skins,
            "balance": user_balance["balance"],
            "user": user
        }
    )

@router.post("/remove_sale/{skin_id}")
async def remove_skin_from_sale(skin_id: int, request: Request, user=Depends(get_current_user)):
    """Снять скин с продажи"""
    # Начинаем транзакцию
    async with database.transaction():
        # Проверяем, принадлежит ли скин пользователю и активен ли
        query_check_skin = """
        SELECT skin_sales.id 
        FROM skin_sales
        JOIN inventory ON skin_sales.skin_id = inventory.skin_id
        WHERE skin_sales.skin_id = :skin_id 
        AND inventory.user_id = :user_id 
        AND skin_sales.status = 'active'
        """
        skin_sale = await database.fetch_one(query=query_check_skin, values={"skin_id": skin_id, "user_id": user["id"]})

        if not skin_sale:
            raise HTTPException(status_code=404, detail="Скин не найден в активных продажах")

        # Удаляем запись из skin_sales
        query_delete_sale = """
        DELETE FROM skin_sales WHERE skin_id = :skin_id AND status = 'active'
        """
        await database.execute(query=query_delete_sale, values={"skin_id": skin_id})

        # Обновляем статус в таблице inventory
        query_update_inventory = """
        UPDATE inventory
        SET status = NULL
        WHERE skin_id = :skin_id AND user_id = :user_id
        """
        await database.execute(query=query_update_inventory, values={"skin_id": skin_id, "user_id": user["id"]})

        # Логируем событие
        await log_history(user_id=user["id"], action_type="remove_sell", description=f"skin_id: {skin_id}")

    # Определяем откуда пришел запрос и редиректим
    referer = request.headers.get("referer", "/profile")
    return RedirectResponse(url=referer, status_code=HTTP_303_SEE_OTHER)

@router.post("/logout")
async def logout(request: Request):
    """Выход из учетной записи."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="user_id")  # Удаляем куку
    return response

@router.post("/admin/set_balance")
async def set_balance(user_id: int = Form(...), new_balance: float = Form(...), admin=Depends(get_current_user)):
    """Замена баланса пользователя администратором."""
    if not admin or not admin["is_admin"]:
        return RedirectResponse(url="/", status_code=303)

    query = "UPDATE users SET balance = :new_balance WHERE id = :user_id"
    await database.execute(query=query, values={"user_id": user_id, "new_balance": new_balance})

    # Логируем изменение баланса
    await log_history(user_id=user_id, action_type="update_balance", description=f"amount: {new_balance}")

    return RedirectResponse(url="/profile", status_code=303)

@router.post("/admin/remove_sale")
async def admin_remove_sale_form(skin_id: int = Form(...), admin=Depends(get_current_user)):
    """Снятие предмета с продажи администратором через форму."""
    if not admin or not admin["is_admin"]:
        return RedirectResponse(url="/", status_code=303)

    # Получаем user_id владельца скина
    query_get_user_id = "SELECT user_id FROM inventory WHERE skin_id = :skin_id"
    result = await database.fetch_one(query=query_get_user_id, values={"skin_id": skin_id})

    if not result:
        raise HTTPException(status_code=404, detail="Скин не найден в инвентаре")

    user_id = result["user_id"]

    # Удаляем запись из таблицы skin_sales
    query_delete_sale = "DELETE FROM skin_sales WHERE skin_id = :skin_id"
    await database.execute(query=query_delete_sale, values={"skin_id": skin_id})

    # Обновляем статус в таблице inventory
    query_update_inventory = """
    UPDATE inventory
    SET status = NULL
    WHERE skin_id = :skin_id AND user_id = :user_id
    """
    await database.execute(query=query_update_inventory, values={"skin_id": skin_id, "user_id": user_id})

    # Логируем событие
    await log_history(user_id=user_id, action_type="remove_sell", description=f"skin_id: {skin_id}")

    return RedirectResponse(url="/profile", status_code=303)

