from sqlalchemy.orm import sessionmaker
from init_db import User, Friendship, FriendStatus, engine

Session = sessionmaker(bind=engine)
session = Session()

def send_friend_request(from_username, to_username):
    """Отправляет запрос в друзья от одного пользователя другому"""
    # 1. Находим обоих пользователей
    user_a = session.query(User).filter(User.username == from_username).first()
    user_b = session.query(User).filter(User.username == to_username).first()

    if not user_a or not user_b:
        return "Ошибка: Один из пользователей не найден."

    if user_a == user_b:
        return "Ошибка: Нельзя добавить самого себя в друзья."

    # 2. Проверяем, нет ли уже такой связи
    existing = session.query(Friendship).filter(
        (Friendship.user_id == user_a.id) & (Friendship.friend_id == user_b.id)
    ).first()

    if existing:
        return f"Запрос уже был отправлен или вы уже друзья (Статус: {existing.status.value})"

    # 3. Создаем запрос
    new_request = Friendship(user_id=user_a.id, friend_id=user_b.id, status=FriendStatus.PENDING)
    session.add(new_request)
    session.commit()
    return f"Запрос от {from_username} к {to_username} отправлен!"

def accept_friend_request(user_who_accepts_name, user_who_sent_name):
    """Принимает входящий запрос в друзья"""
    user_accepting = session.query(User).filter(User.username == user_who_accepts_name).first()
    user_sent = session.query(User).filter(User.username == user_who_sent_name).first()

    # Ищем запись, где user_sent был инициатором (user_id), а user_accepting — целью (friend_id)
    request = session.query(Friendship).filter(
        (Friendship.user_id == user_sent.id) & 
        (Friendship.friend_id == user_accepting.id) & 
        (Friendship.status == FriendStatus.PENDING)
    ).first()

    if not request:
        return "Ошибка: Запрос на дружбу не найден."

    request.status = FriendStatus.ACCEPTED
    session.commit()
    return f"Теперь {user_who_accepts_name} и {user_who_sent_name} — друзья!"