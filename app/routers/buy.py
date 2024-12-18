from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.db.database import database
from app.utils.auth import get_current_user
from app.frontend.templates import templates

router = APIRouter()

@router.get("/buy/{skin_id}", response_class=HTMLResponse)
async def buy_skin_page(request: Request, skin_id: int, user=Depends(get_current_user)):
    """Страница покупки скина."""
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    # Получаем информацию о скине и его цене
    query_skin = """
    SELECT skins.name, skin_sales.price, inventory.user_id AS seller_id
    FROM skins
    JOIN skin_sales ON skins.id = skin_sales.skin_id
    JOIN inventory ON skins.id = inventory.skin_id
    WHERE skin_sales.skin_id = :skin_id AND skin_sales.status = 'active'
    """
    skin = await database.fetch_one(query=query_skin, values={"skin_id": skin_id})
    if not skin:
        raise HTTPException(status_code=404, detail="Скин не найден или не доступен для продажи")

    # Получаем баланс текущего пользователя
    query_balance = "SELECT balance FROM users WHERE id = :user_id"
    user_balance = await database.fetch_one(query=query_balance, values={"user_id": user["id"]})

    return templates.TemplateResponse(
        "buy.html",
        {
            "request": request,
            "skin": dict(skin),
            "user_balance": user_balance["balance"],
            "user": user,
            "skin_id": skin_id
        },
    )

@router.post("/buy/{skin_id}")
async def buy_skin(skin_id: int, user=Depends(get_current_user)):
    """Обработка покупки скина."""
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    async with database.transaction():
        # Получаем информацию о скине и продавце
        query_skin = """
        SELECT skin_sales.price, inventory.user_id AS seller_id
        FROM skin_sales
        JOIN inventory ON skin_sales.skin_id = inventory.skin_id
        WHERE skin_sales.skin_id = :skin_id AND skin_sales.status = 'active'
        """
        skin = await database.fetch_one(query=query_skin, values={"skin_id": skin_id})
        if not skin:
            raise HTTPException(status_code=404, detail="Скин не найден или уже куплен")

        # Проверяем баланс покупателя
        query_balance = "SELECT balance FROM users WHERE id = :user_id"
        buyer_balance = await database.fetch_one(query=query_balance, values={"user_id": user["id"]})
        if buyer_balance["balance"] < skin["price"]:
            raise HTTPException(status_code=400, detail="Недостаточно средств")

        # Обновляем баланс покупателя и продавца
        update_buyer_balance = """
        UPDATE users SET balance = balance - :amount WHERE id = :user_id
        """
        update_seller_balance = """
        UPDATE users SET balance = balance + :amount WHERE id = :seller_id
        """
        await database.execute(update_buyer_balance, values={"amount": skin["price"], "user_id": user["id"]})
        await database.execute(update_seller_balance, values={"amount": skin["price"], "seller_id": skin["seller_id"]})

        # Обновляем статус продажи и инвентарь
        update_skin_sale = "DELETE FROM skin_sales WHERE skin_id = :skin_id"
        update_inventory = """
        UPDATE inventory SET user_id = :new_owner_id WHERE skin_id = :skin_id
        """
        update_status = "UPDATE inventory SET status = NULL WHERE skin_id = :skin_id"
        await database.execute(update_skin_sale, values={"skin_id": skin_id})
        await database.execute(update_inventory, values={"new_owner_id": user["id"], "skin_id": skin_id})
        await database.execute(update_status, values={"skin_id": skin_id})

        # Логируем транзакцию в таблицу transactions
        insert_transaction = """
        INSERT INTO transactions (buyer_id, seller_id, skin_id, price, created_at)
        VALUES (:buyer_id, :seller_id, :skin_id, :price, CURRENT_TIMESTAMP)
        """
        await database.execute(insert_transaction, values={
            "buyer_id": user["id"],
            "seller_id": skin["seller_id"],
            "skin_id": skin_id,
            "price": skin["price"]
        })

    # Редирект на главную страницу после успешной покупки
    return RedirectResponse(url="/", status_code=303)