from databases import Database
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL")

# Подключение к базе данных
database = Database(DATABASE_URL)
