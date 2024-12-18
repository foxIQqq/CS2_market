import urllib.parse
from fastapi import APIRouter, Request, Depends
from starlette.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import os
import aiohttp
from app.db.database import database  # Подключаем базу данных


# Загружаем настройки из .env
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "C5FAB4ADC5B4752E5A2004EADE282497")
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"

router = APIRouter()

async def get_steam_login_url() -> str:
    """Генерирует URL для авторизации Steam"""
    return_url = f"{BASE_URL}/auth/callback"
    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': return_url,
        'openid.realm': BASE_URL,
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
    }
    return f"{STEAM_OPENID_URL}?{urllib.parse.urlencode(params)}"

@router.get("/auth")
async def login():
    """Перенаправляем пользователя на авторизацию через Steam"""
    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': f"{BASE_URL}/auth/callback",
        'openid.realm': BASE_URL,
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
    }
    steam_login_url = f"{STEAM_OPENID_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=steam_login_url)

@router.get("/auth/callback")
async def steam_return(request: Request):
    """Обрабатываем ответ от Steam после авторизации и сохраняем данные пользователя в базу."""
    params = request.query_params

    data = {
        'openid.ns': params.get('openid.ns'),
        'openid.mode': 'check_authentication',
        'openid.op_endpoint': params.get('openid.op_endpoint'),
        'openid.claimed_id': params.get('openid.claimed_id'),
        'openid.identity': params.get('openid.identity'),
        'openid.return_to': params.get('openid.return_to'),
        'openid.response_nonce': params.get('openid.response_nonce'),
        'openid.assoc_handle': params.get('openid.assoc_handle'),
        'openid.signed': params.get('openid.signed'),
        'openid.sig': params.get('openid.sig'),
    }

    async with aiohttp.ClientSession() as session:
        try:
            # Проверка авторизации через Steam OpenID
            async with session.post(STEAM_OPENID_URL, data=data) as steam_response:
                steam_response_text = await steam_response.text()
                if 'is_valid:true' not in steam_response_text:
                    raise ValueError("Ошибка авторизации через Steam")

                # Получаем SteamID из claimed_id
                steam_id = params.get('openid.claimed_id').split('/')[-1]

                # --- Получение информации о пользователе через Steam Web API ---
                steam_api_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
                params = {
                    "key": STEAM_API_KEY,
                    "steamids": steam_id
                }
                async with session.get(steam_api_url, params=params) as player_response:
                    player_data = await player_response.json()

                    # Извлекаем никнейм пользователя
                    players = player_data.get("response", {}).get("players", [])
                    if not players:
                        raise ValueError("Не удалось получить данные пользователя из Steam API")

                    username = players[0].get("personaname", f"user_{steam_id}")

                # --- Сохранение пользователя в базу данных ---
                user_query = """
                INSERT INTO users (steam_id, username)
                VALUES (:steam_id, :username)
                ON CONFLICT (steam_id) DO NOTHING
                RETURNING id
                """
                user = await database.fetch_one(
                    query=user_query,
                    values={
                        "steam_id": steam_id,
                        "username": username  # Реальный никнейм из Steam API
                    }
                )

                # Получаем ID пользователя из базы данных, если запись уже существует
                if not user:
                    user = await database.fetch_one(
                        query="SELECT id FROM users WHERE steam_id = :steam_id",
                        values={"steam_id": steam_id}
                    )

                user_id = user["id"]

                # Перенаправляем пользователя на страницу профиля
                response = RedirectResponse(url=f"{BASE_URL}/profile")
                response.set_cookie(key="user_id", value=user_id)
                return response

        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)
