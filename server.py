# server.py - ПОЛНАЯ ВЕРСИЯ С БОЕМ И РЕГИСТРАЦИЕЙ
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import random
import uvicorn

app = FastAPI()

# Разрешаем доступ с вашей страницы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "kolhoz.db"

# ====== РАБОТА С БАЗОЙ ======
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_user(tg_id, nickname, village="vediltsi"):
    """Создает нового пользователя если его нет"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("""
            INSERT INTO users (telegram_id, nickname, village, level, xp, money, strength, agility, stamina, hp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tg_id, nickname, village, 1, 0, 100, 10, 10, 10, 100))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_user(tg_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(tg_id, money, hp, xp, level):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET money = ?, hp = ?, xp = ?, level = ?
        WHERE telegram_id = ?
    """, (money, hp, xp, level, tg_id))
    conn.commit()
    conn.close()

# ====== API ЭНДПОИНТЫ ======

# --- РЕГИСТРАЦИЯ ---
@app.get("/api/register/{tg_id}/{nickname}")
def register_user(tg_id: int, nickname: str, village: str = "vediltsi"):
    init_user(tg_id, nickname, village)
    return {"success": True, "message": "Пользователь создан"}

# --- ПОЛУЧИТЬ ДАННЫЕ ИГРОКА ---
@app.get("/api/user/{tg_id}")
def get_user_data(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    return {
        "nickname": user["nickname"],
        "level": user["level"],
        "xp": user["xp"],
        "money": user["money"],
        "strength": user["strength"],
        "hp": user["hp"],
        "max_hp": 100 + (user["level"] - 1) * 10,
        "village": user["village"],
        "teeth": 0,
        "authority": 0,
        "win_streak": 0,
        "samogon": 350
    }

# --- БОЙ ---
@app.get("/api/fight/{tg_id}")
def fight(tg_id: int, enemy_index: int = 0):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден. Нажмите 'ВОРВАТЬСЯ В РАЙОН' сначала."}
    
    player_hp = user["hp"]
    player_strength = user["strength"]
    player_money = user["money"]
    player_xp = user["xp"]
    player_level = user["level"]
    
    enemies = [
        {"name": "Копченый", "hp": 30, "damage": 5, "level": 1},
        {"name": "Егор", "hp": 25, "damage": 4, "level": 1},
        {"name": "Васька", "hp": 40, "damage": 7, "level": 2}
    ]
    
    enemy = enemies[enemy_index % len(enemies)]
    enemy_hp = enemy["hp"]
    enemy_damage = enemy["damage"]
    
    rounds = 0
    while player_hp > 0 and enemy_hp > 0 and rounds < 20:
        player_damage = random.randint(5, 12) + player_strength // 3
        enemy_hp -= player_damage
        
        if enemy_hp <= 0:
            break
        
        player_hp -= enemy_damage
        rounds += 1
    
    max_hp = 100 + (player_level - 1) * 10
    
    if player_hp > 0:
        reward_money = random.randint(15, 35)
        reward_xp = random.randint(5, 15)
        
        player_money += reward_money
        player_xp += reward_xp
        
        xp_needed = player_level * 30
        level_up = False
        if player_xp >= xp_needed:
            player_level += 1
            player_xp = 0
            max_hp = 100 + (player_level - 1) * 10
            player_hp = max_hp
            level_up = True
        
        update_user(tg_id, player_money, player_hp, player_xp, player_level)
        
        return {
            "win": True,
            "text": f"🏆 ПОБЕДА над {enemy['name']}! +{reward_money} грн, +{reward_xp} XP",
            "money": player_money,
            "hp": player_hp,
            "max_hp": max_hp,
            "level": player_level,
            "xp": player_xp,
            "max_xp": xp_needed,
            "level_up": level_up
        }
    else:
        player_money = max(0, player_money - 10)
        player_hp = 10
        
        update_user(tg_id, player_money, player_hp, player_xp, player_level)
        
        return {
            "win": False,
            "text": f"💀 ПОРАЖЕНИЕ от {enemy['name']}! -10 грн",
            "money": player_money,
            "hp": player_hp,
            "max_hp": max_hp,
            "level": player_level
        }

# --- РАБОТА ---
@app.post("/api/work")
def do_work(tg_id: int, work_type: str):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    work_map = {
        "barn": {"money": 15, "fatigue": 30, "need_strength": 0},
        "potatoes": {"money": 35, "fatigue": 50, "need_strength": 5},
        "tractor": {"money": 70, "fatigue": 100, "need_strength": 15}
    }
    
    work = work_map.get(work_type)
    if not work:
        return {"error": "Неизвестная работа"}
    
    if user["strength"] < work["need_strength"]:
        return {"error": f"Нужно {work['need_strength']} силы!"}
    
    new_money = user["money"] + work["money"]
    update_user(tg_id, new_money, user["hp"], user["xp"], user["level"])
    
    return {
        "success": True,
        "money": new_money,
        "text": f"🌾 Ты заработал {work['money']} грн!"
    }

# --- ЗАПУСК ---
if __name__ == "__main__":
    print("🚀 Сервер запущен на http://0.0.0.0:10000")
    uvicorn.run(app, host="0.0.0.0", port=10000)
