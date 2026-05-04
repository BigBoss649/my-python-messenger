import sys
import os
import jwt
import json
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Принудительно добавляем текущую папку в пути поиска
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули базы данных
try:
    # Добавляем engine и Base для создания таблиц
    from init_db import Session as DbSession, User, Group, group_members, engine, Base
    from auth import pwd_context
except ImportError as e:
    print(f"Ошибка импорта: {e}")

# --- НАСТРОЙКИ ---
SECRET_KEY = "super-secret-key-change-me" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

app = FastAPI()

# КРИТИЧЕСКИ ВАЖНО: Создаем таблицы при запуске
# Это лечит ошибку "no such table: users"
try:
    Base.metadata.create_all(bind=engine)
    print("Таблицы базы данных успешно проверены/созданы")
except Exception as e:
    print(f"Ошибка при создании таблиц: {e}")

# --- МОДЕЛИ ДАННЫХ ---
class LoginSchema(BaseModel):
    username: str
    password_hash: str

# --- УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЯМИ ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

# --- API ЭНДПОИНТЫ ---

@app.get("/")
def read_root():
    return {"status": "Server is running"}

@app.post("/register")
async def register(data: LoginSchema):
    db = DbSession()
    try:
        existing_user = db.query(User).filter(User.username == data.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        
        new_user = User(
            username=data.username,
            password_hash=pwd_context.hash(data.password_hash)
        )
        db.add(new_user)
        db.commit()
        return {"status": "success", "message": "User registered"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/login")
async def login(data: LoginSchema):
    db = DbSession()
    try:
        user = db.query(User).filter(User.username == data.username).first()
        if not user or not pwd_context.verify(data.password_hash, user.password_hash):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        token = create_access_token(data={"sub": user.username, "id": user.id})
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_data = verify_token(token)
    if not user_data:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user_data.get("id")
    await manager.connect(user_id, websocket)
    
    db = DbSession()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'group_msg':
                group_id = data.get('group_id')
                text = data.get('text')
                members = db.query(group_members).filter_by(group_id=group_id).all()
                for member in members:
                    if member.user_id != user_id:
                        await manager.send_to_user(member.user_id, {
                            "type": "group_msg",
                            "from_user": user_data.get("sub"),
                            "text": text,
                            "group_id": group_id
                        })
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        db.close()