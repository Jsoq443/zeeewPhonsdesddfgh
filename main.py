import random
import sqlite3
import logging
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    InputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Конфигурация
ADMIN_ID = 5645655137  # Ваш ID администратора
DROP_COOLDOWN = 1  # Часы между дропами
ITEMS_PER_PAGE = 1  # Количество объявлений на странице Avito

# Инициализация бота
bot = Bot(
    token="8213832904:AAGKuql0qYyoOZLfBl042CUh0HpsybIt6Zs",
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
class AvitoStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_confirmation = State()

class OzonStates(StatesGroup):
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_confirmation = State()

# Подключение к БД
conn = sqlite3.connect("iphone_game.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц (с проверкой существующих)
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                balance INTEGER DEFAULT 0,
                last_drop TIMESTAMP DEFAULT NULL,
                username TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                item_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                rarity TEXT,
                price INTEGER,
                image_path TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS avito (
                item_id INTEGER PRIMARY KEY,
                seller_id INTEGER,
                buyer_id INTEGER DEFAULT NULL,
                price INTEGER,
                name TEXT,
                rarity TEXT,
                original_price INTEGER,
                image_path TEXT,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'moderation',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                item1_id INTEGER,
                item2_id INTEGER,
                status TEXT DEFAULT 'pending')''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ozon (
                item_id INTEGER PRIMARY KEY,
                admin_id INTEGER,
                brand TEXT,
                name TEXT,
                price INTEGER,
                image_path TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS mvideo (
                item_id INTEGER PRIMARY KEY,
                name TEXT,
                price INTEGER,
                image_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

# Проверяем и добавляем отсутствующие столбцы в avito
cursor.execute("PRAGMA table_info(avito)")
columns = [column[1] for column in cursor.fetchall()]

if 'description' not in columns:
    cursor.execute("ALTER TABLE avito ADD COLUMN description TEXT DEFAULT ''")
if 'status' not in columns:
    cursor.execute("ALTER TABLE avito ADD COLUMN status TEXT DEFAULT 'moderation'")

conn.commit()

# Списки телефонов (остаются без изменений)
IPHONES = IPHONES = [
    # Классические модели
    {"name": "iPhone (1st gen)", "rarity": "Легендарный", "price": 25000, "weight": 3, "image": "iphone_1gen.png"},
    {"name": "iPhone 3G", "rarity": "Легендарный", "price": 20000, "weight": 5, "image": "iphone_3g.png"},
    {"name": "iPhone 3GS", "rarity": "Легендарный", "price": 18000, "weight": 5, "image": "iphone_3gs.png"},
    {"name": "iPhone 4", "rarity": "Очень редкий", "price": 15000, "weight": 8, "image": "iphone_4.png"},
    {"name": "iPhone 4s", "rarity": "Очень редкий", "price": 14000, "weight": 8, "image": "iphone_4s.png"},
    
    # Серия 5
    {"name": "iPhone 5", "rarity": "Редкий", "price": 12000, "weight": 12, "image": "iphone_5.png"},
    {"name": "iPhone 5c", "rarity": "Редкий", "price": 11000, "weight": 12, "image": "iphone_5c.png"},
    {"name": "iPhone 5s", "rarity": "Редкий", "price": 13000, "weight": 12, "image": "iphone_5s.png"},
    
    # Серия 6
    {"name": "iPhone 6", "rarity": "Необычный", "price": 10000, "weight": 15, "image": "iphone_6.png"},
    {"name": "iPhone 6 Plus", "rarity": "Необычный", "price": 11000, "weight": 15, "image": "iphone_6plus.png"},
    {"name": "iPhone 6s", "rarity": "Необычный", "price": 12000, "weight": 15, "image": "iphone_6s.png"},
    {"name": "iPhone 6s Plus", "rarity": "Необычный", "price": 13000, "weight": 15, "image": "iphone_6splus.png"},
    {"name": "iPhone SE (1st gen)", "rarity": "Редкий", "price": 9000, "weight": 10, "image": "iphone_se1.png"},
    
    # Серия 7
    {"name": "iPhone 7", "rarity": "Необычный", "price": 14000, "weight": 15, "image": "iphone_7.png"},
    {"name": "iPhone 7 Plus", "rarity": "Необычный", "price": 15000, "weight": 15, "image": "iphone_7plus.png"},
    
    # Серия 8
    {"name": "iPhone 8", "rarity": "Обычный", "price": 16000, "weight": 20, "image": "iphone_8.png"},
    {"name": "iPhone 8 Plus", "rarity": "Обычный", "price": 17000, "weight": 20, "image": "iphone_8plus.png"},
    {"name": "iPhone X", "rarity": "Редкий", "price": 20000, "weight": 12, "image": "iphone_x.png"},
    
    # Серия X
    {"name": "iPhone XR", "rarity": "Обычный", "price": 18000, "weight": 18, "image": "iphone_xr.png"},
    {"name": "iPhone XS", "rarity": "Редкий", "price": 22000, "weight": 12, "image": "iphone_xs.png"},
    {"name": "iPhone XS Max", "rarity": "Редкий", "price": 24000, "weight": 12, "image": "iphone_xsmax.png"},
    
    # Серия 11
    {"name": "iPhone 11", "rarity": "Обычный", "price": 25000, "weight": 18, "image": "iphone_11.png"},
    {"name": "iPhone 11 Pro", "rarity": "Редкий", "price": 30000, "weight": 12, "image": "iphone_11pro.png"},
    {"name": "iPhone 11 Pro Max", "rarity": "Редкий", "price": 32000, "weight": 12, "image": "iphone_11promax.png"},
    
    # Серия 12
    {"name": "iPhone 12 mini", "rarity": "Необычный", "price": 28000, "weight": 15, "image": "iphone_12mini.png"},
    {"name": "iPhone 12", "rarity": "Необычный", "price": 32000, "weight": 15, "image": "iphone_12.png"},
    {"name": "iPhone 12 Pro", "rarity": "Редкий", "price": 38000, "weight": 12, "image": "iphone_12pro.png"},
    {"name": "iPhone 12 Pro Max", "rarity": "Редкий", "price": 42000, "weight": 12, "image": "iphone_12promax.png"},
    
    # Серия 13
    {"name": "iPhone 13 mini", "rarity": "Необычный", "price": 35000, "weight": 15, "image": "iphone_13mini.png"},
    {"name": "iPhone 13", "rarity": "Необычный", "price": 40000, "weight": 15, "image": "iphone_13.png"},
    {"name": "iPhone 13 Pro", "rarity": "Редкий", "price": 45000, "weight": 12, "image": "iphone_13pro.png"},
    {"name": "iPhone 13 Pro Max", "rarity": "Редкий", "price": 50000, "weight": 12, "image": "iphone_13promax.png"},
    {"name": "iPhone SE (2nd gen)", "rarity": "Обычный", "price": 20000, "weight": 18, "image": "iphone_se2.png"},
    {"name": "iPhone SE (3rd gen)", "rarity": "Обычный", "price": 25000, "weight": 18, "image": "iphone_se3.png"},
    
    # Серия 14
    {"name": "iPhone 14", "rarity": "Необычный", "price": 45000, "weight": 15, "image": "iphone_14.png"},
    {"name": "iPhone 14 Plus", "rarity": "Необычный", "price": 50000, "weight": 15, "image": "iphone_14plus.png"},
    {"name": "iPhone 14 Pro", "rarity": "Редкий", "price": 60000, "weight": 12, "image": "iphone_14pro.png"},
    {"name": "iPhone 14 Pro Max", "rarity": "Редкий", "price": 65000, "weight": 12, "image": "iphone_14promax.png"},
    
    # Серия 15
    {"name": "iPhone 15", "rarity": "Необычный", "price": 55000, "weight": 15, "image": "iphone_15.png"},
    {"name": "iPhone 15 Plus", "rarity": "Необычный", "price": 60000, "weight": 15, "image": "iphone_15plus.png"},
    {"name": "iPhone 15 Pro", "rarity": "Редкий", "price": 70000, "weight": 12, "image": "iphone_15pro.png"},
    {"name": "iPhone 15 Pro Max", "rarity": "Эпический", "price": 80000, "weight": 10, "image": "iphone_15promax.png"},
    
    # Специальные и будущие модели
    {"name": "iPhone 16", "rarity": "Необычный", "price": 90000, "weight": 5, "image": "iphone_16.png"},
    {"name": "iPhone 16 Plus", "rarity": "Необычный", "price": 95000, "weight": 5, "image": "iphone_16plus.png"},
    {"name": "iPhone 16 Pro", "rarity": "Редкий", "price": 100000, "weight": 3, "image": "iphone_16pro.png"},
    {"name": "iPhone 16 Pro Max", "rarity": "Мифический", "price": 120000, "weight": 2, "image": "iphone_16promax.png"},
    {"name": "iPhone 16e", "rarity": "Обычный", "price": 150000, "weight": 1, "image": "iphone_16e.png"}
]
XIAOMI_PHONES = XIAOMI_PHONES =[ 
    # Ранние модели
    {"name": "Xiaomi Mi 1", "rarity": "Легендарный", "price": 5000, "weight": 2, "image": "mi1.png"},
    {"name": "Xiaomi Mi 2", "rarity": "Очень редкий", "price": 6000, "weight": 3, "image": "mi2.png"},
    
    # Популярные серии
    {"name": "Xiaomi Redmi Note 3", "rarity": "Редкий", "price": 8000, "weight": 8, "image": "redmi_note3.png"},
    {"name": "Xiaomi Redmi Note 4", "rarity": "Обычный", "price": 9000, "weight": 15, "image": "redmi_note4.png"},
    
    # Флагманы Mi серии
    {"name": "Xiaomi Mi 5", "rarity": "Редкий", "price": 12000, "weight": 10, "image": "mi5.png"},
    {"name": "Xiaomi Mi 6", "rarity": "Необычный", "price": 15000, "weight": 12, "image": "mi6.png"},
    
    # Современные модели
    {"name": "Xiaomi Mi 9", "rarity": "Необычный", "price": 25000, "weight": 15, "image": "mi9.png"},
    {"name": "Xiaomi Mi 10", "rarity": "Редкий", "price": 30000, "weight": 12, "image": "mi10.png"},
    
    # Ultra-флагманы
    {"name": "Xiaomi Mi 10 Ultra", "rarity": "Очень редкий", "price": 45000, "weight": 8, "image": "mi10_ultra.png"},
    {"name": "Xiaomi Mi 11 Ultra", "rarity": "Эпический", "price": 60000, "weight": 5, "image": "mi11_ultra.png"},
    
    # Топовые модели 2023-2024
    {"name": "Xiaomi 13 Pro", "rarity": "Эпический", "price": 70000, "weight": 7, "image": "mi13_pro.png"},
    {"name": "Xiaomi 14 Ultra", "rarity": "Мифический", "price": 90000, "weight": 3, "image": "mi14_ultra.png"},
    
    # Особые версии
    {"name": "Xiaomi Black Shark 1", "rarity": "Редкий", "price": 35000, "weight": 6, "image": "black_shark1.png"},
    {"name": "Xiaomi Mix Fold 3", "rarity": "Мифический", "price": 100000, "weight": 2, "image": "mix_fold3.png"}]

SAMSUNG_PHONES = [
    # Мифические модели (1-5%)
    {"name": "Samsung Galaxy Z Fold 4 (Limited Edition)", "rarity": "Мифический", "price": 10000000, "weight": 2, "image": "samsung_zfold4le.png"},
    {"name": "Samsung Galaxy S23 Ultra ", "rarity": "Мифический", "price": 30000, "weight": 3, "image": "samsung_s23ultra.png"},

    # Легендарные модели (3-5%)
    {"name": "Samsung Galaxy Note 20 Ultra (Bronze Edition)", "rarity": "Легендарный", "price": 300000, "weight": 4, "image": "samsung_note20u_be.png"},
    {"name": "Samsung Galaxy S21 FE (Special Color)", "rarity": "Легендарный", "price": 70000, "weight": 5, "image": "samsung_s21fe_sc.png"},

    # Эпические модели (10%)
    {"name": "Samsung Galaxy Z Flip 3", "rarity": "Эпический", "price": 20000, "weight": 8, "image": "samsung_zflip3.png"},
    {"name": "Samsung Galaxy S22+", "rarity": "Эпический", "price": 19000, "weight": 10, "image": "samsung_s22plus.png"},
    {"name": "Samsung Galaxy A54", "rarity": "Эпический", "price": 18000, "weight": 10, "image": "samsung_a54.png"},

    # Очень редкие модели (8%)
    {"name": "Samsung Galaxy S20 FE", "rarity": "Очень редкий", "price": 16000, "weight": 12, "image": "samsung_s20fe.png"},
    {"name": "Samsung Galaxy Note 10+", "rarity": "Очень редкий", "price": 15000, "weight": 12, "image": "samsung_note10plus.png"},
    {"name": "Samsung Galaxy A73", "rarity": "Очень редкий", "price": 14000, "weight": 12, "image": "samsung_a73.png"},

    # Редкие модели (12%)
    {"name": "Samsung Galaxy S21", "rarity": "Редкий", "price": 13000, "weight": 15, "image": "samsung_s21.png"},
    {"name": "Samsung Galaxy A52", "rarity": "Редкий", "price": 12000, "weight": 15, "image": "samsung_a52.png"},
    {"name": "Samsung Galaxy Z Flip 4", "rarity": "Редкий", "price": 11000, "weight": 15, "image": "samsung_zflip4.png"},

    # Необычные модели (15%)
    {"name": "Samsung Galaxy M32", "rarity": "Необычный", "price": 9000, "weight": 18, "image": "samsung_m32.png"},
    {"name": "Samsung Galaxy A32", "rarity": "Необычный", "price": 8000, "weight": 18, "image": "samsung_a32.png"},
    {"name": "Samsung Galaxy S10e", "rarity": "Необычный", "price": 7000, "weight": 18, "image": "samsung_s10e.png"},

    # Обычные модели (18-20%)
    {"name": "Samsung Galaxy A12", "rarity": "Обычный", "price": 5000, "weight": 20, "image": "samsung_a12.png"},
    {"name": "Samsung Galaxy M12", "rarity": "Обычный", "price": 4500, "weight": 20, "image": "samsung_m12.png"},
    {"name": "Samsung Galaxy S10", "rarity": "Эпический", "price": 16000, "weight": 20, "image": "samsung_s10.png"},
    {"name": "Samsung Galaxy A02s", "rarity": "Обычный", "price": 4000, "weight": 20, "image": "samsung_a02s.png"}]

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_user_info(user_id):
    cursor.execute("SELECT balance, username FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def create_main_keyboard():
    kb = [
        [KeyboardButton(text="🎰 Дроп"), KeyboardButton(text="📦 Инвентарь")],
        [KeyboardButton(text="🏪 КупиПродай"), KeyboardButton(text="💰 Профиль")],
        [KeyboardButton(text="💱 Трейды"), KeyboardButton(text="🏷 Продать магазину")],
        [KeyboardButton(text="🛍 МВидео"), KeyboardButton(text="🛒 Ozon")],
        [KeyboardButton(text="Топ"), KeyboardButton(text="💸 Перевод")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def create_admin_keyboard():
    kb = [
        [KeyboardButton(text="🎰 Дроп"), KeyboardButton(text="📦 Инвентарь")],
        [KeyboardButton(text="🏪 КупиПродай"), KeyboardButton(text="💰 Профиль")],
        [KeyboardButton(text="💱 Трейды"), KeyboardButton(text="🏷 Продать магазину")],
        [KeyboardButton(text="🛍 МВидео"), KeyboardButton(text="🛒 Ozon")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="💸 Перевод")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def create_brands_keyboard():
    kb = [
        [InlineKeyboardButton(text="Apple", callback_data="ozon_brand_apple")],
        [InlineKeyboardButton(text="Samsung", callback_data="ozon_brand_samsung")],
        [InlineKeyboardButton(text="Xiaomi", callback_data="ozon_brand_xiaomi")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="ozon_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Функция для обновления ассортимента МВидео (добавить в раздел вспомогательных функций)
async def update_mvideo_stock():
    while True:
        try:
            # Удаляем старые товары
            cursor.execute("DELETE FROM mvideo")
            
            # Создаем общий список всех доступных телефонов
            all_phones = XIAOMI_PHONES + IPHONES + SAMSUNG_PHONES
            
            # Добавляем случайные товары (от 1 до 5)
            num_items = random.randint(3, 7)
            selected_phones = random.sample(all_phones, num_items)
            
            for phone in selected_phones:
                item_id = random.randint(1000, 9999)
                cursor.execute(
                    "INSERT INTO mvideo (item_id, name, price, image_path) VALUES (?, ?, ?, ?)",
                    (item_id, phone['name'], phone['price'], os.path.join("phonepng", phone['image']))
                )
            
            conn.commit()
            logger.info(f"Обновлен ассортимент МВидео. Добавлено {num_items} товаров.")
        except Exception as e:
            logger.error(f"Ошибка обновления МВидео: {e}")
        
        # Ждем 1 час до следующего обновления
        await asyncio.sleep(180)

# Обработчик для МВидео (добавить в раздел основных команд)
@dp.message(lambda msg: msg.text == "🛍 МВидео")
async def mvideo_shop(message: Message):
    chat_type = message.chat.type  # 'private' или 'group', 'supergroup' и т.д.
    await show_mvideo_page(message.from_user.id, message.chat.id, chat_type, message.message_id)

async def show_mvideo_page(user_id: int, chat_id: int, chat_type: str, message_id: int = None):
    try:
        cursor.execute("SELECT item_id, name, price, image_path FROM mvideo ORDER BY timestamp DESC")
        items = cursor.fetchall()

        if not items:
            response_text = "🛍 В магазине МВидео пока нет товаров! Попробуйте позже."
            if chat_type == 'private':
                await bot.send_message(chat_id, response_text)
            else:
                await bot.send_message(chat_id, response_text, reply_to_message_id=message_id)
            return

        text = "🛍 <b>МВидео - Актуальные предложения</b>\n\n"
        text += "🔹 Ассортимент обновляется каждые 3 минуты!\n\n"

        for item in items:
            item_id, name, price, image_path = item
            text += f"📱 <b>{name}</b>\n💵 Цена: {price} руб\n🆔 ID: {item_id}\n\n"

        text += "\nℹ️ Для покупки используйте /buy_mvideo [ID]"

        try:
            first_item = items[0]
            photo = types.FSInputFile(first_item[3])
            if chat_type == 'private':
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode="HTML",
                    reply_to_message_id=message_id
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            if chat_type == 'private':
                await bot.send_message(
                    chat_id,
                    text + "\n\n⚠️ Фото временно недоступно",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id,
                    text + "\n\n⚠️ Фото временно недоступно",
                    parse_mode="HTML",
                    reply_to_message_id=message_id
                )

    except Exception as e:
        logger.error(f"Ошибка показа МВидео: {e}")
        if chat_type == 'private':
            await bot.send_message(chat_id, "⚠️ Ошибка загрузки магазина МВидео")
        else:
            await bot.send_message(
                chat_id, 
                "⚠️ Ошибка загрузки магазина МВидео",
                reply_to_message_id=message_id
            )

# Обработчик покупки в МВидео
@dp.message(Command("buy_mvideo"))
async def buy_mvideo(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat_type = message.chat.type
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("ℹ️ Формат: /buy_mvideo [ID]")
            return

        item_id = int(args[1])

        # Получаем информацию о товаре
        cursor.execute(
            "SELECT name, price, image_path FROM mvideo WHERE item_id=?",
            (item_id,)
        )
        item = cursor.fetchone()

        if not item:
            await message.answer("❌ Товар не найден в МВидео!")
            return

        name, price, image_path = item

        # Проверяем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            await message.answer("❌ Недостаточно средств на балансе!")
            return

        # Совершаем покупку
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
        
        # Добавляем телефон в инвентарь
        inventory_id = random.randint(1000, 9999)
        cursor.execute(
            "INSERT INTO inventory (item_id, user_id, name, rarity, price, image_path) VALUES (?, ?, ?, ?, ?, ?)",
            (inventory_id, user_id, name, "Обычный", price, image_path)
        )
        
        # Удаляем товар из МВидео
        cursor.execute("DELETE FROM mvideo WHERE item_id=?", (item_id,))
        
        conn.commit()

        try:
            photo = types.FSInputFile(image_path)
            caption = f"🎉 Поздравляем с покупкой в МВидео!\n\n📱 {name}\n💵 Цена: {price} руб"
            
            if chat_type == 'private':
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            text = f"🎉 Поздравляем с покупкой в МВидео!\n\n📱 {name}\n💵 Цена: {price} руб\n⚠️ Фото временно недоступно"
            if chat_type == 'private':
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id
                )

    except ValueError:
        await message.answer("❌ Неверный формат команды. Используйте: /buy_mvideo [ID]")
    except Exception as e:
        logger.error(f"Ошибка покупки в МВидео: {e}")
        await message.answer("⚠️ Ошибка при покупке. Попробуйте позже.")



async def send_iphone_with_photo(chat_id, iphone, item_id):
    image_path = os.path.join("phonepng", iphone["image"])
    try:
        photo = types.FSInputFile(image_path)
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=f"🎉 <b>Вам выпал iPhone!</b>\n\n"
            f"📱 {iphone['name']}\n"
            f"🏷 Редкость: {iphone['rarity']}\n"
            f"💵 Цена: {iphone['price']} руб",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎉 <b>Вам выпал iPhone!</b>\n\n"
            f"📱 {iphone['name']}\n"
            f"🏷 Редкость: {iphone['rarity']}\n"
            f"💵 Цена: {iphone['price']} руб\n"
            f"⚠️ Фото временно недоступно",
        )

# ========== OZON ФУНКЦИИ ==========

@dp.message(lambda msg: msg.text == "🛒 Ozon")
async def ozon_main(message: Message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer(
            "🛒 <b>Панель администратора Ozon</b>\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить товар", callback_data="ozon_add")],
                [InlineKeyboardButton(text="📋 Список товаров", callback_data="ozon_list")],
                [InlineKeyboardButton(text="❌ Удалить товар", callback_data="ozon_remove")],
            ]),
            parse_mode="HTML"
        )
    else:
        await show_ozon_page(user_id)

async def show_ozon_page(user_id: int, page: int = 0, edit_message: bool = False, message: Message = None):
    try:
        cursor.execute("SELECT COUNT(*) FROM ozon WHERE status='active'")
        total_items = cursor.fetchone()[0]

        if total_items == 0:
            if message and edit_message:
                await message.edit_text("📭 В магазине Ozon пока нет товаров!")
            else:
                await bot.send_message(user_id, "📭 В магазине Ozon пока нет товаров!")
            return

        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        page = max(0, min(page, total_pages - 1))

        cursor.execute(
            """
            SELECT item_id, brand, name, price, image_path, description 
            FROM ozon 
            WHERE status='active'
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (ITEMS_PER_PAGE, page * ITEMS_PER_PAGE),
        )
        items = cursor.fetchall()

        if not items:
            if message and edit_message:
                await message.edit_text("📭 В магазине Ozon пока нет товаров!")
            else:
                await bot.send_message(user_id, "📭 В магазине Ozon пока нет товаров!")
            return

        item = items[0]
        item_id, brand, name, price, image_path, description = item

        kb = []
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"ozon_prev_{page-1}"
                )
            )

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="ozon_current")
        )

        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️", callback_data=f"ozon_next_{page+1}"
                )
            )

        if nav_buttons:
            kb.append(nav_buttons)

        kb.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"ozon_buy_{item_id}")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)

        text = (
            f"🛒 <b>Ozon - Товар {page+1} из {total_pages}</b>\n\n"
            f"🏷 <b>{brand} {name}</b>\n"
            f"💵 Цена: <b>{price}</b> руб\n\n"
        )

        if description:
            text += f"📝 Описание:\n{description}\n\n"

        text += f"🆔 ID: {item_id}"

        try:
            photo = types.FSInputFile(image_path)
            if edit_message and message:
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    media=types.InputMediaPhoto(
                        media=photo, caption=text, parse_mode="HTML"
                    ),
                    reply_markup=keyboard,
                )
            else:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            if edit_message and message:
                await message.edit_text(
                    text + "\n\n⚠️ Фото временно недоступно", reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    user_id,
                    text + "\n\n⚠️ Фото временно недоступно",
                    reply_markup=keyboard,
                )

    except Exception as e:
        logger.error(f"Ошибка показа страницы Ozon: {e}")
        await bot.send_message(user_id, "⚠️ Ошибка загрузки товаров")

@dp.callback_query(lambda c: c.data.startswith("ozon_"))
async def process_ozon_callback(callback: CallbackQuery, state: FSMContext):
    try:
        data = callback.data.split("_")
        if len(data) < 2:
            await callback.answer("⚠️ Неверный формат callback")
            return

        action = data[1]

        if action == "prev":
            if len(data) > 2:
                page = int(data[2])
                await show_ozon_page(callback.from_user.id, page, True, callback.message)
        elif action == "next":
            if len(data) > 2:
                page = int(data[2])
                await show_ozon_page(callback.from_user.id, page, True, callback.message)
        elif action == "buy":
            if len(data) > 2:
                item_id = int(data[2])
                await callback.answer()
                await start_ozon_buy_process(callback.from_user.id, item_id, callback.message)
        elif action == "current":
            await callback.answer("Текущий товар")
        elif action == "add":
            await callback.answer()
            await start_ozon_add_process(callback.from_user.id)
        elif action == "list":
            await callback.answer()
            await show_ozon_admin_list(callback.from_user.id)
        elif action == "remove":
            await callback.answer()
            await start_ozon_remove_process(callback.from_user.id)
        elif action == "brand":
            if len(data) > 2:
                await process_ozon_brand_selection(callback)
        elif action == "model":
            if len(data) > 3:
                await process_ozon_model_selection(callback, state)  # Передаем state здесь
        elif action == "confirm":
            await confirm_ozon_item(callback, state)
        elif action == "cancel":
            await callback.message.delete()
            await callback.answer("❌ Действие отменено")
        else:
            await callback.answer("⚠️ Неизвестное действие")

    except Exception as e:
        logger.error(f"Ошибка обработки callback Ozon: {e}")
        await callback.answer("⚠️ Произошла ошибка")

async def start_ozon_add_process(user_id: int):
    await bot.send_message(
        user_id,
        "🛒 <b>Добавление товара в Ozon</b>\n\n"
        "Выберите бренд:",
        reply_markup=create_brands_keyboard(),
        parse_mode="HTML"
    )

async def process_ozon_brand_selection(callback: CallbackQuery, state: FSMContext):
    try:
        data = callback.data.split("_")
        brand = data[2]
        
        # Сохраняем бренд в состоянии
        await state.update_data(
            brand_type=brand,  # "apple", "samsung" или "xiaomi"
            brand_name="Apple" if brand == "apple" else 
                      "Samsung" if brand == "samsung" else "Xiaomi"
        )
        
        phones = []
        if brand == "apple":
            phones = IPHONES
        elif brand == "xiaomi":
            phones = XIAOMI_PHONES
            
        if not phones:
            await callback.answer("⚠️ Нет моделей этого бренда")
            return
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{i}. {phone['name']}",
                callback_data=f"ozon_model_{i}"
            )] for i, phone in enumerate(phones)
        ] + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="ozon_cancel")]
        ])
        
        await callback.message.edit_text(
            f"Выберите модель:",
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Ошибка выбора бренда: {e}")
        await callback.answer("⚠️ Ошибка выбора бренда")

async def process_ozon_brand_selection(callback: CallbackQuery, state: FSMContext):
    try:
        data = callback.data.split("_")
        brand = data[2]
        
        # Сохраняем бренд в состоянии
        await state.update_data(
            brand_type=brand,
            brand_name="Apple" if brand == "apple" else 
                      "Samsung" if brand == "samsung" else "Xiaomi"
        )
        
        phones = IPHONES if brand == "apple" else \
                SAMSUNG_PHONES if brand == "samsung" else XIAOMI_PHONES
            
        if not phones:
            await callback.answer("⚠️ Нет моделей этого бренда")
            return
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{i}. {phone['name']}",
                callback_data=f"ozon_model_{i}"
            )] for i, phone in enumerate(phones)
        ] + [
            [InlineKeyboardButton(text="❌ Отмена", callback_data="ozon_cancel")]
        ])
        
        await callback.message.edit_text(
            f"Выберите модель:",
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Ошибка выбора бренда: {e}")
        await callback.answer("⚠️ Ошибка выбора бренда")

async def process_ozon_model_selection(callback: CallbackQuery, state: FSMContext):
    try:
        # Получаем сохраненный бренд
        state_data = await state.get_data()
        brand_type = state_data['brand_type']
        
        # Определяем список телефонов
        phones = IPHONES if brand_type == "apple" else \
                SAMSUNG_PHONES if brand_type == "samsung" else XIAOMI_PHONES
        
        # Получаем выбранную модель
        model_idx = int(callback.data.split("_")[-1])
        phone = phones[model_idx]
        
        # Обновляем состояние
        await state.update_data(
            model_idx=model_idx,
            phone_name=phone['name'],
            original_price=phone['price'],
            image_path=os.path.join("phonepng", phone['image'])
        )
        
        # Запрашиваем цену
        await callback.message.edit_text(
            f"📱 Модель: {phone['name']}\n"
            f"💰 Рекоменд. цена: {phone['price']} руб\n\n"
            "Введите цену продажи:"
        )
        await state.set_state(OzonStates.waiting_for_price)
        
    except Exception as e:
        logger.error(f"Ошибка выбора модели: {e}")
        await callback.answer("⚠️ Ошибка выбора модели")

@dp.callback_query(lambda c: c.data == "ozon_confirm", OzonStates.waiting_for_confirmation)
async def confirm_ozon_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    item_id = random.randint(1000, 9999)
    
    try:
        cursor.execute(
            """INSERT INTO ozon 
            (item_id, admin_id, brand, name, price, image_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (item_id, callback.from_user.id, data['brand_name'], data['phone_name'], 
             data['price'], data['image_path'], data['description'])
        )
        conn.commit()
        
        await callback.message.delete()
        await callback.answer("✅ Товар успешно добавлен в Ozon!")
        await bot.send_message(
            callback.from_user.id,
            f"🛒 Товар успешно добавлен в Ozon!\n\n"
            f"📱 {data['brand_name']} {data['phone_name']}\n"
            f"💵 Цена: {data['price']} руб\n\n"
            f"🆔 ID товара: {item_id}",
            reply_markup=create_admin_keyboard() if callback.from_user.id == ADMIN_ID else create_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка добавления товара в Ozon: {e}")
        await callback.answer("⚠️ Ошибка при добавлении товара")

@dp.message(OzonStates.waiting_for_price)
async def process_ozon_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError
            
        await state.update_data(price=price)
        
        # Получаем все сохраненные данные
        data = await state.get_data()
        
        await message.answer(
            f"📝 Введите описание товара (до 200 символов):\n\n"
            f"📱 {data['brand_name']} {data['phone_name']}\n"
            f"💰 Цена: {price} руб"
        )
        await state.set_state(OzonStates.waiting_for_description)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (целое число больше 0)")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        await message.answer("⚠️ Произошла ошибка, попробуйте еще раз")

@dp.message(OzonStates.waiting_for_description)
async def process_ozon_description(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "❌ Создание товара отменено",
            reply_markup=create_admin_keyboard()
        )
        return

    description = message.text.strip()
    if len(description) > 200:
        await message.answer("❌ Описание слишком длинное! Максимум 200 символов.")
        return
    
    await state.update_data(description=description)
    data = await state.get_data()
    
    # Проверяем наличие всех необходимых данных
    required_fields = ['brand_name', 'phone_name', 'price', 'image_path']
    for field in required_fields:
        if field not in data:
            logger.error(f"Отсутствует обязательное поле: {field}")
            await message.answer("⚠️ Ошибка: отсутствуют необходимые данные")
            await state.clear()
            return
    
    # Продолжаем обработку...
    
    await message.delete()
    await state.update_data(description=description)
    
    data = await state.get_data()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="ozon_confirm")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="ozon_cancel")]
    ])
    
    try:
        photo = types.FSInputFile(data['image_path'])
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=f"🛒 <b>Подтвердите добавление товара</b>\n\n"
            f"🏷 Бренд: {data['brand']}\n"
            f"📱 Модель: {data['name']}\n"
            f"💵 Цена: {data['price']} руб\n\n"
            f"📝 Описание:\n{description}",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {e}")
        await bot.send_message(
            message.chat.id,
            f"🛒 <b>Подтвердите добавление товара</b>\n\n"
            f"🏷 Бренд: {data['brand']}\n"
            f"📱 Модель: {data['name']}\n"
            f"💵 Цена: {data['price']} руб\n\n"
            f"📝 Описание:\n{description}\n\n"
            f"⚠️ Фото временно недоступно",
            reply_markup=kb,
            parse_mode="HTML"
        )
    
    await state.set_state(OzonStates.waiting_for_confirmation)

@dp.callback_query(lambda c: c.data == "ozon_confirm", OzonStates.waiting_for_confirmation)
async def confirm_ozon_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    item_id = random.randint(1000, 9999)
    
    cursor.execute(
        """INSERT INTO ozon 
        (item_id, admin_id, brand, name, price, image_path, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (item_id, callback.from_user.id, data['brand'], data['name'], 
         data['price'], data['image_path'], data['description'])
    )
    conn.commit()
    
    await callback.message.delete()
    await callback.answer("✅ Товар успешно добавлен в Ozon!")
    await bot.send_message(
        callback.from_user.id,
        f"🛒 Товар успешно добавлен в Ozon!\n\n"
        f"📱 {data['brand']} {data['name']}\n"
        f"💵 Цена: {data['price']} руб\n\n"
        f"🆔 ID товара: {item_id}",
        reply_markup=create_admin_keyboard() if callback.from_user.id == ADMIN_ID else create_main_keyboard()
    )

async def show_ozon_admin_list(user_id: int):
    cursor.execute(
        """SELECT item_id, brand, name, price 
        FROM ozon 
        WHERE admin_id=?
        ORDER BY timestamp DESC""",
        (user_id,)
    )
    items = cursor.fetchall()
    
    if not items:
        await bot.send_message(
            user_id,
            "📭 У вас нет добавленных товаров в Ozon!",
            reply_markup=create_admin_keyboard() if user_id == ADMIN_ID else create_main_keyboard()
        )
        return
    
    text = "📋 <b>Ваши товары в Ozon:</b>\n\n"
    for item in items:
        text += f"🆔 {item[0]} | {item[1]} {item[2]} - {item[3]} руб\n"
    
    await bot.send_message(
        user_id,
        text,
        parse_mode="HTML",
        reply_markup=create_admin_keyboard() if user_id == ADMIN_ID else create_main_keyboard()
    )

async def start_ozon_remove_process(user_id: int):
    await bot.send_message(
        user_id,
        "❌ <b>Удаление товара из Ozon</b>\n\n"
        "Введите ID товара для удаления:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отмена", callback_data="ozon_cancel")]
])
    )

@dp.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.reply_to_message and 
            "Удаление товара из Ozon" in msg.reply_to_message.text)
async def process_ozon_remove(message: Message):
    try:
        item_id = int(message.text.strip())
        
        cursor.execute(
            "DELETE FROM ozon WHERE item_id=? AND admin_id=?",
            (item_id, message.from_user.id)
        )
        
        if cursor.rowcount == 0:
            await message.answer("❌ Товар с таким ID не найден или вам не принадлежит!")
            return
        
        conn.commit()
        await message.answer(
            f"✅ Товар {item_id} успешно удален из Ozon!",
            reply_markup=create_admin_keyboard()
        )
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный ID товара (число)")

async def start_ozon_buy_process(user_id: int, item_id: int, message: Message = None):
    try:
        cursor.execute(
            """
            SELECT price, name, brand, image_path, description 
            FROM ozon 
            WHERE item_id=? AND status='active'
            """,
            (item_id,),
        )
        item = cursor.fetchone()

        if not item:
            if message:
                await message.edit_text("❌ Товар не найден или уже продан!")
            else:
                await bot.send_message(user_id, "❌ Товар не найден или уже продан!")
            return

        price, name, brand, image_path, description = item

        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            if message:
                await message.edit_text("❌ Недостаточно средств на балансе!")
            else:
                await bot.send_message(user_id, "❌ Недостаточно средств на балансе!")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить покупку",
                        callback_data=f"ozon_confirm_buy_{item_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отменить", callback_data=f"ozon_cancel_buy_{item_id}"
                    )
                ],
            ]
        )

        try:
            photo = types.FSInputFile(image_path)
            if message:
                await bot.edit_message_media(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    media=types.InputMediaPhoto(
                        media=photo,
                        caption=(
                            f"⚠️ <b>Подтвердите покупку</b>\n\n"
                            f"🛒 {brand} {name}\n"
                            f"💵 Цена: {price} руб\n\n"
                            f"Ваш баланс: {balance} руб\n"
                            f"После покупки останется: {balance - price} руб\n\n"
                            f"📝 Описание:\n{description}"
                        ),
                        parse_mode="HTML"
                    ),
                    reply_markup=kb,
                )
            else:
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=(
                        f"⚠️ <b>Подтвердите покупку</b>\n\n"
                        f"🛒 {brand} {name}\n"
                        f"💵 Цена: {price} руб\n\n"
                        f"Ваш баланс: {balance} руб\n"
                        f"После покупки останется: {balance - price} руб\n\n"
                        f"📝 Описание:\n{description}"
                    ),
                    reply_markup=kb,
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            if message:
                await message.edit_text(
                    (
                        f"⚠️ <b>Подтвердите покупку</b>\n\n"
                        f"🛒 {brand} {name}\n"
                        f"💵 Цена: {price} руб\n\n"
                        f"Ваш баланс: {balance} руб\n"
                        f"После покупки останется: {balance - price} руб\n\n"
                        f"📝 Описание:\n{description}\n"
                        f"⚠️ Фото временно недоступно"
                    ),
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    user_id,
                    (
                        f"⚠️ <b>Подтвердите покупку</b>\n\n"
                        f"🛒 {brand} {name}\n"
                        f"💵 Цена: {price} руб\n\n"
                        f"Ваш баланс: {balance} руб\n"
                        f"После покупки останется: {balance - price} руб\n\n"
                        f"📝 Описание:\n{description}\n"
                        f"⚠️ Фото временно недоступно"
                    ),
                    reply_markup=kb,
                    parse_mode="HTML",
                )

    except Exception as e:
        logger.error(f"Ошибка начала процесса покупки Ozon: {e}")
        await bot.send_message(user_id, "⚠️ Ошибка при обработке покупки")

@dp.callback_query(lambda c: c.data.startswith("ozon_confirm_buy_"))
async def process_ozon_buy_confirmation(callback: CallbackQuery):
    try:
        item_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        # Проверяем существование товара
        cursor.execute("""
            SELECT price, name, brand, image_path, description, admin_id 
            FROM ozon 
            WHERE item_id=? AND status='active'
            """, (item_id,))
        item = cursor.fetchone()
        
        if not item:
            await callback.answer("❌ Товар не найден или уже продан!")
            return

        price, name, brand, image_path, description, admin_id = item

        # Проверяем баланс покупателя
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            await callback.answer("❌ Недостаточно средств на балансе!")
            return

        # Выполняем транзакцию
        try:
            conn.execute("BEGIN TRANSACTION")
            
            # Списание средств
            cursor.execute("""
                UPDATE users 
                SET balance = balance - ? 
                WHERE user_id=? AND balance >= ?
                """, (price, user_id, price))
            
            if cursor.rowcount == 0:
                raise ValueError("Не удалось списать средства")

            # Зачисление средств продавцу
            cursor.execute("""
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id=?
                """, (price, admin_id))

            # Добавляем товар в инвентарь
            cursor.execute("""
                INSERT INTO inventory 
                (item_id, user_id, name, rarity, price, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """, 
                (item_id, user_id, f"{brand} {name}", "Обычный", price, image_path))

            # Удаляем товар из Ozon
            cursor.execute("DELETE FROM ozon WHERE item_id=?", (item_id,))

            conn.commit()
            
            # Уведомляем пользователей
            await callback.message.delete()
            await callback.answer("✅ Покупка успешно завершена!")
            await bot.send_message(
                user_id,
                f"🎉 Поздравляем с покупкой!\n\n"
                f"🛒 <b>{brand} {name}</b>\n"
                f"💵 Цена: {price} руб\n"
                f"📝 Описание:\n{description}",
                parse_mode="HTML"
            )
            
            await bot.send_message(
                admin_id,
                f"💰 Товар продан!\n\n"
                f"📱 {brand} {name}\n"
                f"💵 Цена: {price} руб\n"
                f"👤 Покупатель: @{callback.from_user.username}",
                parse_mode="HTML"
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка транзакции: {str(e)}")
            await callback.answer("⚠️ Ошибка при обработке платежа")

    except Exception as e:
        logger.error(f"Критическая ошибка при покупке: {str(e)}")
        await callback.answer("⚠️ Произошла критическая ошибка")
# ========== ОСНОВНЫЕ КОМАНДЫ (остаются без изменений) ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без имени"
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        conn.commit()

        # Создаем клавиатуру с кнопкой "Добавить бота в чат"
        add_to_chat_button = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Добавить бота в чат",
                        url="https://t.me/ZewPhoneBot?startgroup=new"
                    )
                ]
            ]
        )

        welcome_message = (
            "Привет! Тут ты можешь собирать уникальные карточки, продавать и т.п. (Проекту 1 день)\n\n"
            "📱 <b>Как получить карточки?</b>\n\n"
            "Отправь команду «🎰 Дроп»"
        )

        await message.answer(
            welcome_message,
            reply_markup=add_to_chat_button,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

@dp.message(Command("top"))
@dp.message(lambda msg: msg.text.lower() == "топ")
async def show_top(message: Message):
    try:
        # Список пользователей, которых нужно скрыть (без @, lowercase)
        HIDDEN_USERS = ["dinamstr", "okak89"]  # Добавьте нужные username
        
        # Топ по деньгам
        cursor.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
        money_leaders = cursor.fetchall()
        
        # Топ по количеству телефонов
        cursor.execute("""
            SELECT u.username, COUNT(i.item_id) as phone_count 
            FROM users u
            LEFT JOIN inventory i ON u.user_id = i.user_id
            GROUP BY u.user_id
            ORDER BY phone_count DESC
            LIMIT 10
        """)
        phone_leaders = cursor.fetchall()
        
        # Формируем сообщение
        text = "🏆 <b>Топ игроков</b>\n\n"
        text += "💰 <b>По балансу:</b>\n"
        
        for i, (username, balance) in enumerate(money_leaders, 1):
            # Проверяем, нужно ли скрыть пользователя
            if username and username.lower() in HIDDEN_USERS:
                display_name = "🚀 Аноним"
            else:
                display_name = f"@{username or 'unknown'}"
            
            text += f"{i}. {display_name} - {balance:,} руб\n"
        
        text += "\n📱 <b>По количеству телефонов:</b>\n"
        for i, (username, count) in enumerate(phone_leaders, 1):
            if username and username.lower() in HIDDEN_USERS:
                display_name = "🚀 Аноним"
            else:
                display_name = f"@{username or 'unknown'}"
            
            text += f"{i}. {display_name} - {count} шт.\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при показе топа: {e}")
        await message.answer("⚠️ Не удалось загрузить таблицу лидеров")

class TransferStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_amount = State()

@dp.message(Command("transfer"))
async def start_transfer(message: Message, state: FSMContext):
    await message.answer(
        "💸 <b>Перевод денег</b>\n\n"
        "Введите @username пользователя, которому хотите перевести деньги:",
        parse_mode="HTML"
    )
    await state.set_state(TransferStates.waiting_for_username)

@dp.message(TransferStates.waiting_for_username)
async def process_recipient(message: Message, state: FSMContext):
    recipient = message.text.strip().replace("@", "")
    if not recipient:
        await message.answer("❌ Введите корректный username")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE username=?", (recipient,))
    recipient_data = cursor.fetchone()
    
    if not recipient_data:
        await message.answer("❌ Пользователь не найден")
        await state.clear()
        return
    
    await state.update_data(recipient_id=recipient_data[0], recipient_username=recipient)
    await message.answer(f"💵 Введите сумму для перевода @{recipient}:")
    await state.set_state(TransferStates.waiting_for_amount)

@dp.message(TransferStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
            
        data = await state.get_data()
        await state.clear()
        
        sender_id = message.from_user.id
        recipient_id = data['recipient_id']
        
        if sender_id == recipient_id:
            await message.answer("❌ Нельзя переводить себе!")
            return
            
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (sender_id,))
        sender_balance = cursor.fetchone()[0]
        
        if sender_balance < amount:
            await message.answer("❌ Недостаточно средств на балансе")
            return
            
        # Выполняем перевод
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, sender_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, recipient_id))
        conn.commit()
        
        await message.answer(
            f"✅ Вы успешно перевели {amount} руб пользователю @{data['recipient_username']}\n"
            f"Ваш новый баланс: {sender_balance - amount} руб"
        )
        
        # Уведомляем получателя
        await bot.send_message(
            recipient_id,
            f"💰 Вы получили перевод {amount} руб от @{message.from_user.username}\n"
            f"Используйте /profile чтобы проверить баланс"
        )
        
    except ValueError:
        await message.answer("❌ Введите корректную сумму (целое число больше 0)")

@dp.message(Command("profile"))
@dp.message(lambda msg: msg.text == "💰 Профиль")
async def profile(message: Message):
    user_id = message.from_user.id
    try:
        cursor.execute("SELECT balance, username FROM users WHERE user_id=?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await message.answer("❌ Профиль не найден! Попробуйте снова.")
            return
            
        balance, username = user_data
        username = username or message.from_user.username or "Без имени"

        cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (user_id,))
        items_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM avito WHERE seller_id=? AND status='active'", (user_id,)
        )
        active_lots = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM trades WHERE (user1_id=? OR user2_id=?) AND status='pending'",
            (user_id, user_id),
        )
        active_trades = cursor.fetchone()[0]

        await message.answer(
            f"👤 <b>Профиль @{username}</b>\n\n"
            f"💵 Баланс: {balance} руб\n"
            f"📱 Телефонов в инвентаре: {items_count}\n"
            f"🏷 Активных лотов: {active_lots}\n"
            f"🔄 Активных трейдов: {active_trades}",
            reply_markup=create_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в профиле: {e}")
        await message.answer("⚠️ Не удалось загрузить профиль")

@dp.message(Command("drop"))
@dp.message(lambda msg: msg.text == "🎰 Дроп")
async def drop_iphone(message: Message):
    user_id = message.from_user.id
    try:
        cursor.execute("SELECT last_drop FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()

        if user_data and user_data[0]:
            last_drop_time = datetime.strptime(user_data[0], "%Y-%m-%d %H:%M:%S")
            time_left = (last_drop_time + timedelta(hours=DROP_COOLDOWN)) - datetime.now()

            if time_left.total_seconds() > 0:
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                await message.answer(
                    f"⏳ Следующий дроп будет доступен через {hours} ч. {minutes} мин.",
                    reply_markup=create_main_keyboard(),
                )
                return

        phone_type = random.choices(["iphone", "xiaomi", "samsung"], weights=[20, 20, 60])[0]

        if phone_type == "iphone":
            phone = random.choices(
                IPHONES, weights=[p["weight"] for p in IPHONES], k=1
            )[0]
            phone_brand = "iPhone"
        elif phone_type == "xiaomi":
            phone = random.choices(
                XIAOMI_PHONES, weights=[p["weight"] for p in XIAOMI_PHONES], k=1
            )[0]
            phone_brand = "Xiaomi"
        else:
            phone = random.choices(
                SAMSUNG_PHONES, weights=[p["weight"] for p in SAMSUNG_PHONES], k=1
            )[0]
            phone_brand = "Samsung"

        item_id = random.randint(1000, 9999)
        image_path = os.path.join("phonepng", phone["image"])

        cursor.execute(
            """INSERT INTO users (user_id, last_drop) 
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET last_drop = ?""",
            (
                user_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        cursor.execute(
            "INSERT INTO inventory (item_id, user_id, name, rarity, price, image_path) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, user_id, phone["name"], phone["rarity"], phone["price"], image_path),
        )

        conn.commit()

        try:
            photo = types.FSInputFile(image_path)
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=f"🎉 Вам выпал {phone_brand}!\n\n"
                f"📱 {phone['name']}\n"
                f"🏷 Редкость: {phone['rarity']}\n"
                f"💵 Цена: {phone['price']} руб",
                reply_markup=create_main_keyboard(),
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await message.answer(
                f"🎉 Вам выпал {phone_brand}!\n\n"
                f"📱 {phone['name']}\n"
                f"🏷 Редкость: {phone['rarity']}\n"
                f"💵 Цена: {phone['price']} руб\n"
                f"⚠️ Фото временно недоступно",
                reply_markup=create_main_keyboard(),
            )

    except Exception as e:
        logger.error(f"Ошибка в /drop: {e}")
        await message.answer(
            "⚠️ Ошибка. Попробуйте позже.", reply_markup=create_main_keyboard()
        )


@dp.message(Command("inventory"))
@dp.message(lambda msg: msg.text == "📦 Инвентарь")
async def show_inventory(message: Message):
    user_id = message.from_user.id
    try:
        cursor.execute("SELECT * FROM inventory WHERE user_id=?", (user_id,))
        items = cursor.fetchall()

        if not items:
            await message.answer(
                "📦 Ваш инвентарь пуст! Используйте /drop чтобы получить iPhone.",
                reply_markup=create_main_keyboard(),
            )
            return

        items_text = "📱 <b>Ваши телефоны:</b>\n(Используйте ID для продажи/трейдов)\n\n"
        for item in items:
            items_text += f"🆔 {item[0]} | {item[2]} ({item[3]}) - {item[4]} руб\n"

        await message.answer(
            items_text + "\nℹ️ Для продажи используйте /sell [ID] [цена]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка в /inventory: {e}")
        await message.answer("⚠️ Не удалось загрузить инвентарь")


@dp.message(Command("avito"))
@dp.message(lambda msg: msg.text == "🏪 КупиПродай")
async def show_avito_command(message: Message):
    chat_type = message.chat.type
    await show_avito_page(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        chat_type=chat_type,
        message_id=message.message_id
    )

async def show_avito_page(
    user_id: int,
    chat_id: int,
    chat_type: str,
    message_id: int = None,
    page: int = 0,
    edit_message: bool = False,
    message: Message = None
):
    try:
        cursor.execute("SELECT COUNT(*) FROM avito WHERE status='active'")
        total_items = cursor.fetchone()[0]

        if total_items == 0:
            response_text = "📭 На КупиПродай пока нет телефонов!"
            if chat_type == 'private':
                if edit_message and message:
                    await message.edit_text(response_text)
                else:
                    await bot.send_message(chat_id, response_text)
            else:
                await bot.send_message(chat_id, response_text, reply_to_message_id=message_id)
            return

        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        page = max(0, min(page, total_pages - 1))

        cursor.execute(
            """
            SELECT item_id, price, name, rarity, image_path, description 
            FROM avito 
            WHERE status='active'
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (ITEMS_PER_PAGE, page * ITEMS_PER_PAGE),
        )
        lots = cursor.fetchall()

        if not lots:
            response_text = "📭 На КупиПродай пока нет телефонов!"
            if chat_type == 'private':
                if edit_message and message:
                    await message.edit_text(response_text)
                else:
                    await bot.send_message(chat_id, response_text)
            else:
                await bot.send_message(chat_id, response_text, reply_to_message_id=message_id)
            return

        lot = lots[0]
        item_id, price, name, rarity, image_path, description = lot

        kb = []
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"avito_prev_{page-1}"
                )
            )

        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="avito_current")
        )

        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперёд ➡️", callback_data=f"avito_next_{page+1}"
                )
            )

        if nav_buttons:
            kb.append(nav_buttons)

        kb.append([InlineKeyboardButton(text="💰 Купить", callback_data=f"avito_buy_{item_id}")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)

        text = (
            f"🏪 <b>КупиПродай - Объявление {page+1} из {total_pages}</b>\n\n"
            f"📱 <b>{name}</b> ({rarity})\n"
            f"💵 Цена: <b>{price}</b> руб\n\n"
        )

        if description:
            text += f"📝 Описание:\n{description}\n\n"

        text += f"🆔 ID: {item_id}"

        try:
            photo = types.FSInputFile(image_path)
            if edit_message and message:
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    media=types.InputMediaPhoto(
                        media=photo, caption=text, parse_mode="HTML"
                    ),
                    reply_markup=keyboard,
                )
            else:
                if chat_type == 'private':
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                        reply_to_message_id=message_id
                    )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            if edit_message and message:
                await message.edit_text(
                    text + "\n\n⚠️ Фото временно недоступно", 
                    reply_markup=keyboard
                )
            else:
                if chat_type == 'private':
                    await bot.send_message(
                        chat_id,
                        text + "\n\n⚠️ Фото временно недоступно",
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        chat_id,
                        text + "\n\n⚠️ Фото временно недоступно",
                        reply_markup=keyboard,
                        parse_mode="HTML",
                        reply_to_message_id=message_id
                    )

    except Exception as e:
        logger.error(f"Ошибка показа страницы КупиПродай: {e}")
        if chat_type == 'private':
            await bot.send_message(chat_id, "⚠️ Ошибка загрузки объявлений")
        else:
            await bot.send_message(
                chat_id, 
                "⚠️ Ошибка загрузки объявлений",
                reply_to_message_id=message_id
            )

@dp.callback_query(lambda c: c.data.startswith("avito_"))
async def process_avito_callback(callback: CallbackQuery):
    data = callback.data.split("_")
    action = data[1]

    try:
        if action == "prev":
            page = int(data[2])
            await show_avito_page(callback.from_user.id, page, True, callback.message)
        elif action == "next":
            page = int(data[2])
            await show_avito_page(callback.from_user.id, page, True, callback.message)
        elif action == "buy":
            item_id = int(data[2])
            await callback.answer()
            await start_buy_process(callback.from_user.id, item_id, callback.message)
        elif action == "current":
            await callback.answer("Текущее объявление")

    except Exception as e:
        logger.error(f"Ошибка обработки callback КупиПродай: {e}")
        await callback.answer("⚠️ Произошла ошибка")


async def start_buy_process(user_id: int, item_id: int, message: Message = None):
    try:
        cursor.execute(
            """
            SELECT price, seller_id, name, rarity, original_price, image_path 
            FROM avito 
            WHERE item_id=? AND status='active'
            """,
            (item_id,),
        )
        lot = cursor.fetchone()

        if not lot:
            await bot.send_message(user_id, "❌ Лот не найден или уже продан!")
            return

        price, seller_id, name, rarity, original_price, image_path = lot

        if user_id == seller_id:
            await bot.send_message(user_id, "❌ Нельзя купить свой же телефон!")
            return

        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            await bot.send_message(user_id, "❌ Недостаточно средств на балансе!")
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить покупку",
                        callback_data=f"confirm_buy_{item_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отменить", callback_data=f"cancel_buy_{item_id}"
                    )
                ],
            ]
        )

        try:
            photo = types.FSInputFile(image_path)
            await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=(
                    f"⚠️ <b>Подтвердите покупку</b>\n\n"
                    f"📱 {name} ({rarity})\n"
                    f"💵 Цена: {price} руб\n\n"
                    f"Ваш баланс: {balance} руб\n"
                    f"После покупки останется: {balance - price} руб"
                ),
                reply_markup=kb,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            await bot.send_message(
                user_id,
                (
                    f"⚠️ <b>Подтвердите покупку</b>\n\n"
                    f"📱 {name} ({rarity})\n"
                    f"💵 Цена: {price} руб\n\n"
                    f"Ваш баланс: {balance} руб\n"
                    f"После покупки останется: {balance - price} руб\n"
                    f"⚠️ Фото временно недоступно"
                ),
                reply_markup=kb,
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Ошибка начала процесса покупки: {e}")
        await bot.send_message(user_id, "⚠️ Ошибка при обработке покупки")


@dp.callback_query(
    lambda c: c.data.startswith("confirm_buy_") or c.data.startswith("cancel_buy_")
)
async def process_buy_confirmation(callback: CallbackQuery):
    data = callback.data.split("_")
    action = data[0]
    item_id = int(data[2])
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    chat_type = callback.message.chat.type
    message_id = callback.message.message_id

    try:
        if action == "cancel":
            await callback.message.delete()
            await callback.answer("❌ Покупка отменена")
            return

        cursor.execute(
            """
            SELECT price, seller_id, name, rarity, original_price, image_path 
            FROM avito 
            WHERE item_id=? AND status='active'
            """,
            (item_id,),
        )
        lot = cursor.fetchone()

        if not lot:
            await callback.answer("❌ Лот не найден или уже продан!")
            return

        price, seller_id, name, rarity, original_price, image_path = lot

        if user_id == seller_id:
            await callback.answer("❌ Нельзя купить свой же телефон!")
            return

        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            await callback.answer("❌ Недостаточно средств на балансе!")
            return

        cursor.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id)
        )
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?", (price, seller_id)
        )

        cursor.execute(
            """
            INSERT INTO inventory (item_id, user_id, name, rarity, price, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_id, user_id, name, rarity, original_price, image_path),
        )

        cursor.execute(
            """
            UPDATE avito SET status='sold', buyer_id=?
            WHERE item_id=? AND status='active'
            """,
            (user_id, item_id),
        )

        conn.commit()

        await callback.message.delete()

        try:
            photo = types.FSInputFile(image_path)
            caption = (
                f"🎉 Поздравляем с покупкой!\n\n"
                f"📱 <b>{name}</b>\n"
                f"🏷 Редкость: {rarity}\n"
                f"💵 Цена покупки: {price} руб"
            )
            
            if chat_type == 'private':
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_to_message_id=message_id
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке фото: {e}")
            text = (
                f"🎉 Поздравляем с покупкой!\n\n"
                f"📱 <b>{name}</b>\n"
                f"🏷 Редкость: {rarity}\n"
                f"💵 Цена покупки: {price} руб\n"
                f"⚠️ Фото временно недоступно"
            )
            if chat_type == 'private':
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id,
                    text,
                    parse_mode="HTML",
                    reply_to_message_id=message_id
                )

        await bot.send_message(
            seller_id,
            (
                f"💰 Ваш телефон <b>{name}</b> продан за {price} руб!\n"
                f"💸 На ваш баланс зачислено: {price} руб"
            ),
            parse_mode="HTML",
        )

        await callback.answer("✅ Покупка успешно завершена!")

    except Exception as e:
        logger.error(f"Ошибка подтверждения покупки: {e}")
        await callback.answer("⚠️ Ошибка при покупке")

@dp.message(Command("sell"))
async def sell_iphone(message: Message, state: FSMContext):
    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer(
                "ℹ️ Формат: /sell [ID] [цена]\nПример: /sell 1234 5000",
                reply_markup=create_main_keyboard(),
            )
            return

        item_id = int(args[1])
        price = int(args[2])
        user_id = message.from_user.id

        if price < 1000:
            await message.answer(
                "❌ Минимальная цена продажи - 1000 руб!",
                reply_markup=create_main_keyboard(),
            )
            return

        cursor.execute(
            "SELECT name, rarity, price, image_path FROM inventory WHERE item_id=? AND user_id=?",
            (item_id, user_id),
        )
        phone_data = cursor.fetchone()

        if not phone_data:
            await message.answer(
                "❌ У вас нет такого телефона!", reply_markup=create_main_keyboard()
            )
            return

        name, rarity, original_price, image_path = phone_data

        await state.update_data(
            item_id=item_id,
            price=price,
            name=name,
            rarity=rarity,
            original_price=original_price,
            image_path=image_path,
        )

        await message.answer(
            f"📝 Напишите описание для вашего телефона <b>{name}</b> (максимум 200 символов):\n\n"
            f"ℹ️ Вы можете указать состояние, особенности или другую информацию",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отменить")]], resize_keyboard=True
            ),
        )

        await state.set_state(AvitoStates.waiting_for_description)

    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Используйте: /sell [ID] [цена]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка в /sell: {e}")
        await message.answer(
            "⚠️ Ошибка при продаже", reply_markup=create_main_keyboard()
        )


@dp.message(AvitoStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "❌ Создание объявления отменено",
            reply_markup=create_main_keyboard(),
        )
        return

    description = message.text.strip()

    if len(description) > 200:
        await message.answer("❌ Описание слишком длинное! Максимум 200 символов.")
        return

    data = await state.get_data()
    await state.clear()

    item_id = data["item_id"]
    price = data["price"]
    name = data["name"]
    rarity = data["rarity"]
    original_price = data["original_price"]
    image_path = data["image_path"]
    user_id = message.from_user.id

    try:
        cursor.execute(
            "DELETE FROM inventory WHERE item_id=? AND user_id=?", (item_id, user_id)
        )

        cursor.execute(
            """
            INSERT INTO avito 
            (item_id, seller_id, price, name, rarity, original_price, image_path, description, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'moderation')
            """,
            (item_id, user_id, price, name, rarity, original_price, image_path, description),
        )

        conn.commit()

        await message.answer(
            f"✅ <b>{name}</b> успешно отправлен на модерацию!\n\n"
            f"💵 Ваша цена: {price} руб\n"
            f"📝 Ваше описание:\n{description}\n\n"
            f"ℹ️ Объявление будет проверено администратором в ближайшее время.",
            parse_mode="HTML",
            reply_markup=create_main_keyboard(),
        )

        await bot.send_message(
            ADMIN_ID,
            f"🛎 Новое объявление на модерацию:\n\n"
            f"📱 {name} ({rarity})\n"
            f"💵 Цена: {price} руб\n"
            f"👤 Продавец: @{message.from_user.username}\n"
            f"📝 Описание:\n{description}\n\n"
            f"🆔 ID: {item_id}\n\n"
            f"✅ /approve_{item_id}\n"
            f"❌ /reject_{item_id}",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка при добавлении описания: {e}")
        await message.answer(
            "⚠️ Ошибка при размещении объявления",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("quick_sell"))
@dp.message(lambda msg: msg.text == "🏷 Продать магазину")
async def quick_sell(message: Message):
    user_id = message.from_user.id
    try:
        args = message.text.split()
        if len(args) == 2 and args[0] == "/quick_sell":
            item_id = int(args[1])
        else:
            await message.answer(
                "ℹ️ Выберите телефон из инвентаря командой /quick_sell [ID]\n"
                "Или просмотрите инвентарь: /inventory",
                reply_markup=create_main_keyboard(),
            )
            return

        cursor.execute(
            "SELECT name, rarity, price, image_path FROM inventory WHERE item_id=? AND user_id=?",
            (item_id, user_id),
        )
        item = cursor.fetchone()

        if not item:
            await message.answer(
                "❌ У вас нет такого телефона!", reply_markup=create_main_keyboard()
            )
            return

        name, rarity, price, image_path = item
        sell_price = int(price * 0.7)

        cursor.execute("DELETE FROM inventory WHERE item_id=?", (item_id,))
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?", (sell_price, user_id)
        )
        conn.commit()

        await message.answer(
            f"✅ Вы продали <b>{name}</b> магазину за {sell_price} руб\n"
            f"💸 Оригинальная цена: {price} руб",
            reply_markup=create_main_keyboard(),
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат команды. Используйте: /quick_sell [ID_телефона]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка быстрой продажи: {e}")
        await message.answer(
            "⚠️ Не удалось выполнить продажу. Попробуйте позже.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("trade"))
@dp.message(lambda msg: msg.text == "💱 Трейды")
async def start_trade(message: Message):
    user_id = message.from_user.id
    try:
        args = message.text.split()
        if len(args) == 1:
            cursor.execute(
                """SELECT t.trade_id, t.item1_id, t.item2_id, 
                i1.name as item1_name, i2.name as item2_name,
                u2.username as partner_name
                FROM trades t
                JOIN inventory i1 ON t.item1_id = i1.item_id
                JOIN inventory i2 ON t.item2_id = i2.item_id
                JOIN users u2 ON t.user2_id = u2.user_id
                WHERE t.user1_id=? AND t.status='pending' """,
                (user_id,),
            )
            your_trades = cursor.fetchall()

            cursor.execute(
                """SELECT t.trade_id, t.item1_id, t.item2_id, 
                i1.name as item1_name, i2.name as item2_name,
                u1.username as partner_name
                FROM trades t
                JOIN inventory i1 ON t.item1_id = i1.item_id
                JOIN inventory i2 ON t.item2_id = i2.item_id
                JOIN users u1 ON t.user1_id = u1.user_id
                WHERE t.user2_id=? AND t.status='pending' """,
                (user_id,),
            )
            their_trades = cursor.fetchall()

            if not your_trades and not their_trades:
                await message.answer(
                    "🔄 У вас нет активных трейдов.\n"
                    "ℹ️ Для создания трейда используйте: /trade [ID_вашего_телефона] [ID_телефона_другого_игрока]",
                    reply_markup=create_main_keyboard(),
                )
                return

            trades_text = "🔄 <b>Ваши активные трейды:</b>\n\n"
            if your_trades:
                trades_text += "<u>Исходящие:</u>\n"
                for trade in your_trades:
                    trades_text += (
                        f"🆔 {trade[0]} | Ваш {trade[3]} (ID:{trade[1]}) ↔ "
                        f"{trade[4]} (ID:{trade[2]}) от @{trade[5]}\n"
                    )

            if their_trades:
                trades_text += "\n<u>Входящие:</u>\n"
                for trade in their_trades:
                    trades_text += (
                        f"🆔 {trade[0]} | {trade[3]} (ID:{trade[1]}) от @{trade[5]} ↔ "
                        f"Ваш {trade[4]} (ID:{trade[2]})\n"
                        f"Для подтверждения: /accept_trade {trade[0]}\n"
                        f"Для отказа: /cancel_trade {trade[0]}\n\n"
                    )

            await message.answer(
                trades_text,
                reply_markup=create_main_keyboard(),
            )
            return

        if len(args) != 3:
            await message.answer(
                "ℹ️ Формат: /trade [ID_вашего_телефона] [ID_телефона_другого_игрока]",
                reply_markup=create_main_keyboard(),
            )
            return

        your_item_id = int(args[1])
        their_item_id = int(args[2])

        cursor.execute(
            "SELECT user_id, name FROM inventory WHERE item_id=?", (your_item_id,)
        )
        your_item = cursor.fetchone()

        cursor.execute(
            "SELECT user_id, name FROM inventory WHERE item_id=?", (their_item_id,)
        )
        their_item = cursor.fetchone()

        if not your_item or your_item[0] != user_id:
            await message.answer(
                "❌ У вас нет такого телефона!", reply_markup=create_main_keyboard()
            )
            return

        if not their_item:
            await message.answer(
                "❌ Такого телефона не существует!", reply_markup=create_main_keyboard()
            )
            return

        their_user_id = their_item[0]

        if their_user_id == user_id:
            await message.answer(
                "❌ Нельзя создать трейд с самим собой!",
                reply_markup=create_main_keyboard(),
            )
            return

        cursor.execute(
            "INSERT INTO trades (user1_id, user2_id, item1_id, item2_id) VALUES (?, ?, ?, ?)",
            (user_id, their_user_id, your_item_id, their_item_id),
        )
        conn.commit()

        await message.answer(
            f"🔄 Трейд создан! Ваш {your_item[1]} (ID:{your_item_id}) ↔ "
            f"{their_item[1]} (ID:{their_item_id})\n"
            f"Ожидайте подтверждения от другого игрока.",
            reply_markup=create_main_keyboard(),
        )

        await bot.send_message(
            their_user_id,
            f"🔄 Вам предложен трейд!\n"
            f"Ваш {their_item[1]} (ID:{their_item_id})\n"
            f"На {your_item[1]} (ID:{your_item_id})\n\n"
            f"Для подтверждения нажмите: /accept_trade {your_item_id}\n"
            f"Для отказа: /cancel_trade {your_item_id}",
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат команды. Используйте: /trade [ID_вашего_телефона] [ID_телефона_другого_игрока]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка создания трейда: {e}")
        await message.answer(
            "⚠️ Не удалось создать трейд. Попробуйте позже.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("accept_trade"))
async def accept_trade(message: Message):
    user_id = message.from_user.id
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "ℹ️ Формат: /accept_trade [ID_трейда]",
                reply_markup=create_main_keyboard(),
            )
            return

        trade_id = int(args[1])

        # Получаем информацию о трейде
        cursor.execute(
            """SELECT t.trade_id, t.user1_id, t.user2_id, t.item1_id, t.item2_id,
                  i1.name as item1_name, i2.name as item2_name
               FROM trades t
               JOIN inventory i1 ON t.item1_id = i1.item_id
               JOIN inventory i2 ON t.item2_id = i2.item_id
               WHERE t.trade_id=? AND t.status='pending'""",
            (trade_id,)
        )
        trade = cursor.fetchone()

        if not trade:
            await message.answer(
                "❌ Активного трейда не найдено!",
                reply_markup=create_main_keyboard(),
            )
            return

        trade_id, user1_id, user2_id, item1_id, item2_id, item1_name, item2_name = trade

        # Проверяем, что пользователь является участником трейда
        if user_id not in (user1_id, user2_id):
            await message.answer(
                "❌ Вы не являетесь участником этого трейда!",
                reply_markup=create_main_keyboard(),
            )
            return

        # Проверяем, что пользователь не подтверждает свой же трейд
        if user_id == user1_id:
            await message.answer(
                "❌ Вы не можете подтвердить свой собственный трейд!",
                reply_markup=create_main_keyboard(),
            )
            return

        # Проверяем наличие предметов у участников
        cursor.execute(
            "SELECT 1 FROM inventory WHERE item_id=? AND user_id=?", (item1_id, user1_id)
        )
        item1_exists = cursor.fetchone()

        cursor.execute(
            "SELECT 1 FROM inventory WHERE item_id=? AND user_id=?", (item2_id, user2_id)
        )
        item2_exists = cursor.fetchone()

        if not item1_exists or not item2_exists:
            cursor.execute(
                "UPDATE trades SET status='canceled' WHERE trade_id=?", (trade_id,)
            )
            conn.commit()
            await message.answer(
                "❌ Один из предметов больше не существует. Трейд отменен.",
                reply_markup=create_main_keyboard(),
            )
            return

        try:
            # Начинаем транзакцию
            conn.execute("BEGIN TRANSACTION")
            
            # Обмениваем предметы
            cursor.execute(
                "UPDATE inventory SET user_id=? WHERE item_id=?", (user_id, item1_id)
            )
            cursor.execute(
                "UPDATE inventory SET user_id=? WHERE item_id=?", (user1_id, item2_id)
            )
            
            # Обновляем статус трейда
            cursor.execute(
                "UPDATE trades SET status='completed' WHERE trade_id=?", (trade_id,)
            )
            
            conn.commit()

            # Уведомляем участников
            await message.answer(
                f"✅ Трейд успешно завершен!\n"
                f"Вы получили: {item1_name} (ID:{item1_id})",
                reply_markup=create_main_keyboard(),
            )

            await bot.send_message(
                user1_id,
                f"✅ Ваш трейд подтвержден!\n"
                f"Вы получили: {item2_name} (ID:{item2_id})\n"
                f"В обмен на: {item1_name} (ID:{item1_id})",
                reply_markup=create_main_keyboard(),
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при подтверждении трейда: {e}")
            await message.answer(
                "⚠️ Произошла ошибка при подтверждении трейда.",
                reply_markup=create_main_keyboard(),
            )

    except ValueError:
        await message.answer(
            "❌ Неверный формат команды. Используйте: /accept_trade [ID_трейда]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка подтверждения трейда: {e}")
        await message.answer(
            "⚠️ Не удалось подтвердить трейд. Попробуйте позже.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("cancel_trade"))
async def cancel_trade(message: Message):
    user_id = message.from_user.id
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "ℹ️ Формат: /cancel_trade [ID_трейда]",
                reply_markup=create_main_keyboard(),
            )
            return

        trade_id = int(args[1])

        cursor.execute(
            "SELECT user1_id, item1_id, item2_id FROM trades WHERE trade_id=? AND status='pending'",
            (trade_id,),
        )
        trade = cursor.fetchone()

        if not trade:
            await message.answer(
                "❌ Активного трейда не найдено.",
                reply_markup=create_main_keyboard(),
            )
            return

        user1_id, item1_id, item2_id = trade

        if user_id not in (user1_id, message.from_user.id):
            await message.answer(
                "❌ Вы не можете отменить этот трейд!",
                reply_markup=create_main_keyboard(),
            )
            return

        cursor.execute(
            "UPDATE trades SET status='canceled' WHERE trade_id=?", (trade_id,)
        )
        conn.commit()

        other_user = user1_id if user_id != user1_id else message.from_user.id

        await message.answer(
            "❌ Трейд успешно отменен.", reply_markup=create_main_keyboard()
        )

        await bot.send_message(
            other_user,
            f"❌ Трейд с вашим участием был отменен.",
            reply_markup=create_main_keyboard(),
        )
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат команды. Используйте: /cancel_trade [ID_трейда]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка отмены трейда: {e}")
        await message.answer(
            "⚠️ Не удалось отменить трейд. Попробуйте позже.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("admin_give"))
async def admin_give(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(
            "❌ У вас нет прав администратора!", reply_markup=create_main_keyboard()
        )
        return

    try:
        args = message.text.split()
        if len(args) != 3:
            await message.answer(
                "ℹ️ Формат: /admin_give [ID_пользователя] [ID_модели_из_списка]\n"
                "Для просмотра списка моделей: /admin_models",
                reply_markup=create_main_keyboard(),
            )
            return

        target_user = int(args[1])
        model_id = int(args[2])

        if model_id < 0 or model_id >= len(IPHONES + XIAOMI_PHONES + SAMSUNG_PHONES):
            await message.answer(
                f"❌ Неверный ID модели! Допустимые значения: 0-{len(IPHONES + XIAOMI_PHONES + SAMSUNG_PHONES)-1}",
                reply_markup=create_main_keyboard(),
            )
            return

        if model_id < len(IPHONES):
            phone = IPHONES[model_id]
            phone_brand = "iPhone"
        elif model_id < len(IPHONES) + len(XIAOMI_PHONES):
            phone = XIAOMI_PHONES[model_id - len(IPHONES)]
            phone_brand = "Xiaomi"
        else:
            phone = SAMSUNG_PHONES[model_id - len(IPHONES) - len(XIAOMI_PHONES)]
            phone_brand = "Samsung"

        item_id = random.randint(1000, 9999)
        image_path = os.path.join("phonepng", phone["image"])

        cursor.execute(
            "INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?)",
            (
                item_id,
                target_user,
                phone["name"],
                phone["rarity"],
                phone["price"],
                image_path,
            ),
        )
        conn.commit()

        await message.answer(
            f"✅ {phone_brand} {phone['name']} выдан пользователю {target_user}",
            reply_markup=create_main_keyboard(),
        )

        await bot.send_message(
            target_user,
            f"🎁 Администратор выдал вам:\n"
            f"📱 {phone['name']}\n"
            f"🏷 Редкость: {phone['rarity']}\n"
            f"💵 Цена: {phone['price']} руб",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка выдачи админа: {e}")
        await message.answer(
            "⚠️ Не удалось выдать телефон. Проверьте правильность введенных данных.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("admin_models"))
async def admin_models(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer(
            "❌ У вас нет прав администратора!", reply_markup=create_main_keyboard()
        )
        return

    try:
        models_text = "📱 <b>Список моделей iPhone:</b>\n(Используйте ID для выдачи)\n\n"
        for idx, phone in enumerate(IPHONES):
            models_text += f"{idx}. {phone['name']} ({phone['rarity']})\n"

        models_text += "\n📱 <b>Список моделей Xiaomi:</b>\n\n"
        for idx, phone in enumerate(XIAOMI_PHONES, start=len(IPHONES)):
            models_text += f"{idx}. {phone['name']} ({phone['rarity']})\n"

        models_text += "\n📱 <b>Список моделей Samsung:</b>\n\n"
        for idx, phone in enumerate(SAMSUNG_PHONES, start=len(IPHONES) + len(XIAOMI_PHONES)):
            models_text += f"{idx}. {phone['name']} ({phone['rarity']})\n"

        await message.answer(
            models_text
            + "\nℹ️ Для выдачи используйте: /admin_give [ID_пользователя] [ID_модели]",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка просмотра моделей: {e}")
        await message.answer(
            "⚠️ Не удалось загрузить список моделей.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("moderation"))
async def show_moderation_queue(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "❌ У вас нет прав доступа!", reply_markup=create_main_keyboard()
        )
        return

    try:
        cursor.execute(
            """
            SELECT a.item_id, a.name, a.price, a.description, u.username 
            FROM avito a
            JOIN users u ON a.seller_id = u.user_id
            WHERE a.status='moderation'
            ORDER BY a.timestamp
            """
        )
        items = cursor.fetchall()

        if not items:
            await message.answer(
                "✅ Нет объявлений на модерации!", reply_markup=create_main_keyboard()
            )
            return

        text = "🛎 <b>Объявления на модерации:</b>\n\n"
        for item in items:
            text += (
                f"📱 <b>{item[1]}</b>\n"
                f"💵 Цена: {item[2]} руб\n"
                f"👤 Продавец: @{item[4]}\n"
                f"📝 Описание:\n{item[3]}\n\n"
                f"🆔 ID: {item[0]}\n"
                f"✅ /approve_{item[0]}\n"
                f"❌ /reject_{item[0]}\n\n"
            )

        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка показа очереди модерации: {e}")
        await message.answer(
            "⚠️ Ошибка загрузки очереди модерации.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(lambda msg: msg.text.startswith("/approve_") and msg.from_user.id == ADMIN_ID)
async def approve_item(message: Message):
    try:
        item_id = int(message.text.split("_")[1])

        cursor.execute(
            """
            UPDATE avito SET status='active'
            WHERE item_id=? AND status='moderation'
            """,
            (item_id,),
        )

        if cursor.rowcount == 0:
            await message.answer(
                "❌ Объявление не найдено или уже обработано!",
                reply_markup=create_main_keyboard(),
            )
            return

        conn.commit()

        cursor.execute(
            "SELECT seller_id, name, price FROM avito WHERE item_id=?", (item_id,)
        )
        seller_id, name, price = cursor.fetchone()

        await message.answer(
            f"✅ Объявление {item_id} одобрено и опубликовано!",
            reply_markup=create_main_keyboard(),
        )

        await bot.send_message(
            seller_id,
            f"✅ Ваше объявление одобрено!\n\n"
            f"📱 <b>{name}</b>\n"
            f"💵 Цена: {price} руб\n\n"
            f"Теперь ваш телефон виден всем пользователям в разделе КупиПродай!",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка одобрения объявления: {e}")
        await message.answer(
            "⚠️ Ошибка при одобрении объявления.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(lambda msg: msg.text.startswith("/reject_") and msg.from_user.id == ADMIN_ID)
async def reject_item(message: Message):
    try:
        item_id = int(message.text.split("_")[1])

        cursor.execute(
            """
            SELECT seller_id, name, price FROM avito WHERE item_id=? AND status='moderation'
            """,
            (item_id,),
        )
        item = cursor.fetchone()

        if not item:
            await message.answer(
                "❌ Объявление не найдено или уже обработано!",
                reply_markup=create_main_keyboard(),
            )
            return

        seller_id, name, price = item

        cursor.execute(
            """
            INSERT INTO inventory 
            SELECT item_id, seller_id, name, rarity, original_price, image_path 
            FROM avito 
            WHERE item_id=?
            """,
            (item_id,),
        )

        cursor.execute(
            """
            DELETE FROM avito WHERE item_id=? AND status='moderation'
            """,
            (item_id,),
        )

        conn.commit()

        await message.answer(
            f"❌ Объявление {item_id} отклонено и удалено!",
            reply_markup=create_main_keyboard(),
        )

        await bot.send_message(
            seller_id,
            f"❌ Ваше объявление отклонено модератором!\n\n"
            f"📱 <b>{name}</b>\n"
            f"💵 Ваша цена: {price} руб\n\n"
            f"ℹ️ Телефон возвращен в ваш инвентарь.\n"
            f"Вы можете создать новое объявление с другой ценой или описанием.",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка отклонения объявления: {e}")
        await message.answer(
            "⚠️ Ошибка при отклонении объявления.",
            reply_markup=create_main_keyboard(),
        )


@dp.message(Command("superultramegaultrasecretno"))
async def daily_bonus(message: Message):
    user_id = message.from_user.id
    try:
        bonus = random.randint(1, 1)
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?", (bonus, user_id)
        )
        conn.commit()
        await message.answer(
            f"🎁 Вы получили ежедневный бонус: {bonus} руб!",
            reply_markup=create_main_keyboard(),
        )
    except Exception as e:
        logger.error(f"Ошибка в /daily: {e}")
        await message.answer(
            "⚠️ Не удалось выдать бонус. Попробуйте позже.",
            reply_markup=create_main_keyboard(),
        )

# ========== ЗАПУСК БОТА ==========
async def main():
    asyncio.create_task(update_mvideo_stock())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
