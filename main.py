import sys
import os
import jwt
import json
from datetime import datetime, timedelta
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session

# Принудительно добавляем текущую папку в пути поиска Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем твои модули
try:
    from init_db import Session as DbSession, User, Group, group_members
    from auth import pwd_context
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедись, что файлы init_db.py и auth.py лежат в той же папке!")

# --- НАСТРОЙКИ ---
SECRET_KEY = "super-secret-key-change-me" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

app = FastAPI()

# --- УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЯМИ ---
class ConnectionManager:
    def __init__(self):
        # Храним активные сессии: {user_id: websocket}
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

@app.post("/login")
async def login(username: str, password: str):
    db = DbSession()
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not pwd_context.verify(password, user.password_hash):
        db.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    token = create_access_token(data={"sub": user.username, "id": user.id})
    db.close()
    return {"access_token": token, "token_type": "bearer"}

# --- WEBSOCKET ЧАТ ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # 1. Проверяем токен
    user_data = verify_token(token)
    if not user_data:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user_data.get("id")
    await manager.connect(user_id, websocket)
    
    db = DbSession()
    try:
        while True:
            # 2. Получаем сообщение от клиента
            data = await websocket.receive_json()
            
            # Логика работы с группами
            if data.get('type') == 'group_msg':
                group_id = data.get('group_id')
                text = data.get('text')
                
                # Ищем участников группы в БД
                members = db.query(group_members).filter_by(group_id=group_id).all()
                
                for member in members:
                    # Рассылаем всем, кроме отправителя
                    if member.user_id != user_id:
                        await manager.send_to_user(member.user_id, {
                            "type": "group_msg",
                            "from_user": user_data.get("sub"),
                            "text": text,
                            "group_id": group_id
                        })
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"Ошибка в WebSocket: {e}")
    finally:
        db.close()