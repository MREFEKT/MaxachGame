from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import random
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "kolhoz.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            nickname TEXT,
            village TEXT DEFAULT 'vediltsi',
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            money INTEGER DEFAULT 100,
            strength INTEGER DEFAULT 10,
            agility INTEGER DEFAULT 10,
            stamina INTEGER DEFAULT 100,
            teeth INTEGER DEFAULT 0,
            authority INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0,
            last_xp_time INTEGER DEFAULT 0,
            hp INTEGER DEFAULT 100
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(tg_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def init_user(tg_id, nickname, village="vediltsi"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (telegram_id, nickname, village, level, xp, money, strength, agility, stamina, teeth, authority, win_streak, last_xp_time, hp)
            VALUES (?, ?, ?, 1, 0, 100, 10, 10, 100, 0, 0, 0, 0, 100)
        """, (tg_id, nickname, village))
        conn.commit()
    conn.close()

def update_after_fight(tg_id, money, hp, xp, level, teeth, authority, win_streak, last_xp_time):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET money = ?, hp = ?, xp = ?, level = ?, teeth = ?, authority = ?, win_streak = ?, last_xp_time = ?
        WHERE telegram_id = ?
    """, (money, hp, xp, level, teeth, authority, win_streak, last_xp_time, tg_id))
    conn.commit()
    conn.close()

@app.get("/api/user/{tg_id}")
def get_user_data(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    max_hp = 100
    xp_needed = user["level"] * 3  # Легкая сетка опыта

    return {
        "nickname": user["nickname"],
        "level": user["level"],
        "xp": user["xp"],
        "max_xp": xp_needed,
        "money": user["money"],
        "strength": user["strength"],
        "agility": user["agility"],
        "hp": user["hp"],
        "max_hp": max_hp,
        "village": user["village"],
        "teeth": user["teeth"],
        "authority": user["authority"],
        "win_streak": user["win_streak"],
        "samogon": 350
    }

@app.get("/api/fight/{tg_id}")
def fight(tg_id: int, enemy_index: int = 0):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    # Для боя проверяем только ХП
    if user["hp"] <= 15:
        return {"error": "⚠️ Мало ХП! Подлечись в Столовке чебуреком или борщом."}

    p_hp = user["hp"]
    p_money = user["money"]
    p_teeth = user["teeth"]
    p_auth = user["authority"]
    p_streak = user["win_streak"]
    p_xp = user["xp"]
    p_level = user["level"]
    last_xp_time = user["last_xp_time"] or 0
    now = int(time.time())

    # Список противников
    enemies = [
        {"name": "Копченый", "bank": 150, "is_bot": True},
        {"name": "Егор", "bank": 200, "is_bot": True},
        {"name": "Васька", "bank": 300, "is_bot": False}
    ]
    
    enemy = enemies[enemy_index % len(enemies)]
    
    # Вычисляем урон
    my_dmg = round(random.uniform(12.0, 18.0), 1)
    enemy_dmg = round(random.uniform(8.0, 14.0), 1)
    
    # В 85% случаев побеждаем при нормальном бое
    is_win = random.random() < 0.85

    p_hp = max(1, p_hp - int(enemy_dmg))
    
    xp_gained = 0
    level_up = False
    max_xp = p_level * 3

    if is_win:
        # Берём минимальный процент от банка (3-5%)
        percent = random.uniform(0.03, 0.05)
        earned_money = max(5, int(enemy["bank"] * percent))
        
        p_money += earned_money
        p_teeth += 1
        p_auth += 1
        p_streak += 1

        # Проверка кулдауна на Опыт (1 XP раз в 50 минут = 3000 секунд)
        if (now - last_xp_time) >= 3000:
            p_xp += 1
            xp_gained = 1
            last_xp_time = now

            if p_xp >= max_xp:
                p_level += 1
                p_xp = 0
                p_hp = 100 # Восстановление ХП при лвл-апе
                level_up = True

        result_text = f"🏆 Победа! +{earned_money} грн | 🦷 +1 зуб | 🏆 +1 Авторитет"
        if xp_gained > 0:
            result_text += " | ⭐ +1 XP (раз в 50 мин)"

        update_after_fight(tg_id, p_money, p_hp, p_xp, p_level, p_teeth, p_auth, p_streak, last_xp_time)

        return {
            "win": True,
            "text": result_text,
            "my_dmg": my_dmg,
            "enemy_dmg": enemy_dmg,
            "money": p_money,
            "hp": p_hp,
            "teeth": p_teeth,
            "authority": p_auth,
            "win_streak": p_streak,
            "level": p_level,
            "xp": p_xp,
            "max_xp": p_level * 3,
            "level_up": level_up
        }
    else:
        p_streak = 0
        result_text = "💀 Поражение! Ты потерял ХП и сбросил серию побед."
        update_after_fight(tg_id, p_money, p_hp, p_xp, p_level, p_teeth, p_auth, p_streak, last_xp_time)

        return {
            "win": False,
            "text": result_text,
            "my_dmg": my_dmg,
            "enemy_dmg": enemy_dmg,
            "money": p_money,
            "hp": p_hp,
            "teeth": p_teeth,
            "authority": p_auth,
            "win_streak": 0,
            "level": p_level,
            "xp": p_xp,
            "max_xp": max_xp
        }
