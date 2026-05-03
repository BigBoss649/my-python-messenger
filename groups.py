from sqlalchemy.orm import sessionmaker
from init_db import User, Group, group_members, engine

Session = sessionmaker(bind=engine)
session = Session()

def create_group(group_name, creator_username):
    """Создает группу и добавляет создателя как админа"""
    # 1. Ищем создателя
    creator = session.query(User).filter(User.username == creator_username).first()
    if not creator:
        return "Ошибка: Создатель не найден."

    # 2. Создаем саму группу
    new_group = Group(name=group_name)
    session.add(new_group)
    session.flush() # Получаем ID группы до коммита

    # 3. Добавляем создателя в таблицу связей (через объект группы)
    # Используем базовую вставку в таблицу связей, чтобы указать роль 'admin'
    stmt = group_members.insert().values(
        user_id=creator.id, 
        group_id=new_group.id, 
        role="admin"
    )
    
    try:
        session.execute(stmt)
        session.commit()
        return f"Группа '{group_name}' успешно создана! Админ: {creator_username}"
    except Exception as e:
        session.rollback()
        return f"Ошибка при создании группы: {e}"

def add_user_to_group(group_id, username_to_add):
    """Добавляет пользователя в группу по его имени"""
    user = session.query(User).filter(User.username == username_to_add).first()
    group = session.query(Group).filter(Group.id == group_id).first()

    if not user or not group:
        return "Ошибка: Пользователь или группа не найдены."

    # Проверяем, не состоит ли он уже в этой группе
    is_member = session.query(group_members).filter_by(
        user_id=user.id, group_id=group_id
    ).first()

    if is_member:
        return f"Пользователь {username_to_add} уже в группе."

    # Добавляем в группу
    stmt = group_members.insert().values(
        user_id=user.id, 
        group_id=group_id, 
        role="member"
    )
    
    try:
        session.execute(stmt)
        session.commit()
        return f"Пользователь {username_to_add} добавлен в группу '{group.name}'"
    except Exception as e:
        session.rollback()
        return f"Ошибка: {e}"