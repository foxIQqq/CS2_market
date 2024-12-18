from fastapi import APIRouter, Form, Request, HTTPException
from starlette.responses import RedirectResponse, HTMLResponse
from passlib.context import CryptContext
from app.db.database import database
from app.frontend.templates import templates

router = APIRouter()

# Хэширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTML: Страница входа
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# HTML: Страница регистрации
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Обработка логина
@router.post("/login")
async def login_process(request: Request, username: str = Form(...), password: str = Form(...)):
    query = "SELECT id, password FROM users WHERE username = :username"
    user = await database.fetch_one(query=query, values={"username": username})
    if not user or not pwd_context.verify(password, user["password"]):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})
    
    response = RedirectResponse(url="/profile", status_code=303)
    response.set_cookie(key="user_id", value=user["id"])
    return response

# Обработка регистрации
@router.post("/register")
async def register_process(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(password) < 8:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Пароль должен содержать минимум 8 символов"})
    
    # Проверка существования пользователя
    query_check = "SELECT id FROM users WHERE username = :username"
    existing_user = await database.fetch_one(query=query_check, values={"username": username})
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Пользователь уже существует"})
    
    # Добавление нового пользователя
    hashed_password = pwd_context.hash(password)
    query_insert = "INSERT INTO users (username, password) VALUES (:username, :password)"
    await database.execute(query=query_insert, values={"username": username, "password": hashed_password})
    
    return RedirectResponse(url="/login", status_code=303)
