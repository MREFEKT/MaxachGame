from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import random
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "kolhoz.db"

def get_user(tg_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (tg_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user(tg_id, money, hp, xp, level):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET money = ?, hp = ?, xp = ?, level = ?
        WHERE telegram_id = ?
    """, (money, hp, xp, level, tg_id))
    conn.commit()
    conn.close()

@app.get("/api/user/{tg_id}")
def get_user_data(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    return {
        "nickname": user[1],
        "level": user[3],
        "xp": user[4],
        "money": user[5],
        "strength": user[6],
        "hp": user[8],
        "max_hp": 100 + (user[3] - 1) * 10,
        "village": user[2]
    }

@app.get("/api/fight/{tg_id}")
def fight(tg_id: int):
    user = get_user(tg_id)
    if not user:
        return {"error": "Игрок не найден"}
    
    player_hp = user[8]
    player_strength = user[6]
    player_money = user[5]
    player_xp = user[4]
    player_level = user[3]
    
    enemy_hp = random.randint(25, 40)
    enemy_damage = random.randint(3, 8)
    
    while player_hp > 0 and enemy_hp > 0:
        player_damage = random.randint(5, 12) + player_strength // 3
        enemy_hp -= player_damage
        
        if enemy_hp <= 0:
            break
        
        player_hp -= enemy_damage
    
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
            player_hp = 100 + (player_level - 1) * 10
            level_up = True
        
        update_user(tg_id, player_money, player_hp, player_xp, player_level)
        
        return {
            "win": True,
            "text": f"🏆 ПОБЕДА! +{reward_money} грн, +{reward_xp} XP",
            "money": player_money,
            "hp": player_hp,
            "max_hp": 100 + (player_level - 1) * 10,
            "level": player_level,
            "level_up": level_up,
            "xp": player_xp,
            "xp_needed": player_level * 30
        }
    else:
        player_money = max(0, player_money - 10)
        player_hp = 10
        
        update_user(tg_id, player_money, player_hp, player_xp, player_level)
        
        return {
            "win": False,
            "text": "💀 ПОРАЖЕНИЕ! -10 грн",
            "money": player_money,
            "hp": player_hp,
            "max_hp": 100 + (player_level - 1) * 10,
            "level": player_level,
            "level_up": False
        }

@app.get("/api/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)