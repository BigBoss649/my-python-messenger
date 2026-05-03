from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from passlib.context import CryptContext
# Импортируем нашу модель User из предыдущего файла
from init_db import User, engine 

# Настройка безопасности (алгоритм bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создаем сессию для работы с БД
Session = sessionmaker(bind=engine)
session = Session()

def get_password_hash(password):
    """Превращает пароль в защищенный хэш"""
    return pwd_context.hash(password)

def register_user(username, password):
    """Регистрирует нового пользователя"""
    # 1. Проверяем, не занято ли имя
    existing_user = session.query(User).filter(User.username == username).first()
    if existing_user:
        return f"Ошибка: Пользователь {username} уже существует!"

    # 2. Хэшируем пароль
    hashed_password = get_password_hash(password)

    # 3. Создаем запись в базе
    new_user = User(username=username, password_hash=hashed_password)
    
    try:
        session.add(new_user)
        session.commit()
        return f"Успех: Пользователь {username} зарегистрирован!"
    except Exception as e:
        session.rollback()
        return f"Ошибка при сохранении: {e}"

# --- ТЕСТ ---
if __name__ == "__main__":
    print(register_user("ivan_top", "secret123"))
    print(register_user("alex_dev", "qwerty2026"))