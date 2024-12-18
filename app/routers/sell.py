from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from app.db.database import database
from app.utils.auth import get_current_user
from app.frontend.templates import templates
from app.utils.logger import log_history


router = APIRouter()

@router.get("/sell/{skin_id}")
async def show_sell_form(request: Request, skin_id: int, user=Depends(get_current_user)):
    query = """
    SELECT i.skin_id, s.name, s.price, i.status, i.user_id
    FROM inventory AS i
    JOIN skins AS s ON i.skin_id = s.id
    WHERE i.skin_id = :skin_id AND i.user_id = :user_id
    """
    skin = await database.fetch_one(query=query, values={"skin_id": skin_id, "user_id": user["id"]})
    skin = dict(skin)

    if not skin:
        raise HTTPException(status_code=404, detail="Скин не найден или не принадлежит пользователю")
    
    return templates.TemplateResponse("sell_skin.html", {"request": request, "skin" : skin, "skin_id" : skin_id})


@router.post("/sell/{skin_id}")
async def sell_skin(skin_id: int, price: float = Form(...), user=Depends(get_current_user)):
    query_check_skin = """
    SELECT skin_id, user_id FROM inventory
    WHERE skin_id = :skin_id AND user_id = :user_id
    """
    skin_exists = await database.fetch_one(query=query_check_skin, values={"skin_id": skin_id, "user_id": user["id"]})

    if not skin_exists:
        raise HTTPException(status_code=404, detail="Скин не найден или не принадлежит пользователю")

    # Добавляем запись о продаже в таблицу skin_sales
    query_insert_skin_sale = """
    INSERT INTO skin_sales (seller_id, skin_id, price, status)
    VALUES (:seller_id, :skin_id, :price, 'active')
    """
    await database.execute(query=query_insert_skin_sale, values={
        "seller_id": user["id"], 
        "skin_id": skin_id, 
        "price": price
    })

    # Обновляем статус скина в инвентаре
    query_update_skin = """
    UPDATE inventory
    SET status = 'for_sale'
    WHERE skin_id = :skin_id AND user_id = :user_id
    """
    await database.execute(query=query_update_skin, values={"skin_id": skin_id, "user_id": user["id"]})

    # Логируем событие
    # await log_history(user_id=user["id"], action_type="sell", description=f"skin_id: {skin_id}")

    return RedirectResponse(url="/profile", status_code=HTTP_303_SEE_OTHER)

