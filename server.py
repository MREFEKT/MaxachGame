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
    
    # 1. Создаем таблицу, если ее нет
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
    
    # 2. МИГРАЦИЯ: Безопасно добавляем колонки, если таблица уже существовала без них
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "last_xp_time" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_xp_time INTEGER DEFAULT 0")
    if "teeth" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN teeth INTEGER DEFAULT 0")
    if "authority" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN authority INTEGER DEFAULT 0")
    if "win_streak" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN win_streak INTEGER DEFAULT 0")
        
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

# ====== API ======

@app.get("/")
def root():
    return {"status": "ok", "message": "Сервер работает!"}

@app.get("/api/register/{tg_id}/{nickname}")
def register_user(tg_id: int, nickname: str, village: str = "vediltsi"):
    try:
        init_user(tg_id, nickname, village)
        return {"success": True, "message": "Пользователь создан"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/api/user/{tg_id}")
def get_user_data(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    max_hp = 100
    xp_needed = user["level"] * 3

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
        "teeth": user["teeth"] or 0,
        "authority": user["authority"] or 0,
        "win_streak": user["win_streak"] or 0,
        "samogon": 350
    }

@app.get("/api/fight/{tg_id}")
def fight(tg_id: int, enemy_index: int = 0):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    if user["hp"] <= 15:
        return {"error": "⚠️ Мало ХП! Подлечись в Столовке чебуреком или борщом."}

    p_hp = user["hp"]
    p_money = user["money"]
    p_teeth = user["teeth"] or 0
    p_auth = user["authority"] or 0
    p_streak = user["win_streak"] or 0
    p_xp = user["xp"]
    p_level = user["level"]
    last_xp_time = user["last_xp_time"] or 0
    now = int(time.time())

    enemies = [
        {"name": "Копченый", "bank": 150, "is_bot": True},
        {"name": "Егор", "bank": 200, "is_bot": True},
        {"name": "Васька", "bank": 300, "is_bot": False}
    ]
    
    enemy = enemies[enemy_index % len(enemies)]
    
    my_dmg = round(random.uniform(12.0, 18.0), 1)
    enemy_dmg = round(random.uniform(8.0, 14.0), 1)
    
    is_win = random.random() < 0.85

    p_hp = max(1, p_hp - int(enemy_dmg))
    
    xp_gained = 0
    level_up = False
    max_xp = p_level * 3

    if is_win:
        percent = random.uniform(0.03, 0.05)
        earned_money = max(5, int(enemy["bank"] * percent))
        
        p_money += earned_money
        p_teeth += 1
        p_auth += 1
        p_streak += 1

        # Опыт дается 1 раз в 50 минут (3000 сек)
        if (now - last_xp_time) >= 3000:
            p_xp += 1
            xp_gained = 1
            last_xp_time = now

            if p_xp >= max_xp:
                p_level += 1
                p_xp = 0
                p_hp = 100
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

@app.post("/api/work")
def do_work(tg_id: int, work_type: str):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    work_map = {
        "barn": {"money": 15, "need_strength": 0},
        "potatoes": {"money": 35, "need_strength": 5},
        "tractor": {"money": 70, "need_strength": 15}
    }
    
    work = work_map.get(work_type)
    if not work:
        return {"error": "Неизвестная работа"}
    
    if user["strength"] < work["need_strength"]:
        return {"error": f"Нужно {work['need_strength']} силы!"}
    
    new_money = user["money"] + work["money"]
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET money = ? WHERE telegram_id = ?", (new_money, tg_id))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "money": new_money,
        "text": f"🌾 Ты заработал {work['money']} грн!"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Сервер запущен на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
