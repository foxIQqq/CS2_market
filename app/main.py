from fastapi import FastAPI, Depends, Form, HTTPException, Request
from app.auth import router as steam_router
from app.routers.auth_routes import router as auth_router
from app.routers import main, profile, sell, buy
from app.db.database import database
from fastapi.staticfiles import StaticFiles

# Настраиваем FastAPI и подключаем шаблоны
app = FastAPI()

# Подключение статики
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")

# Подключение маршрутов
app.include_router(steam_router)
app.include_router(profile.router)
app.include_router(main.router)
app.include_router(sell.router)
app.include_router(buy.router)
app.include_router(auth_router)

# Подключение к базе данных при старте приложения
@app.on_event("startup")
async def startup():
    await database.connect()

# Отключение от базы данных при завершении приложения
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()