from sqlalchemy import Column, Integer, String, ForeignKey, Table, Enum, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
import enum

Base = declarative_base()

# 1. СТАТУСЫ ДЛЯ ДРУЗЕЙ
class FriendStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"

# 2. ТАБЛИЦА СВЯЗИ ДРУЗЕЙ
class Friendship(Base):
    __tablename__ = 'friendships'
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    friend_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    status = Column(Enum(FriendStatus), default=FriendStatus.PENDING)

# 3. ТАБЛИЦА СВЯЗИ ГРУПП (Вспомогательная для Many-to-Many)
group_members = Table(
    'group_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('role', String, default="member") # admin или member
)

# 4. МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    
    # Связь с группами через таблицу group_members
    groups = relationship("Group", secondary=group_members, back_populates="members")

# 5. МОДЕЛЬ ГРУППЫ
class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # Обратная связь с пользователями
    members = relationship("User", secondary=group_members, back_populates="groups")

# --- НАСТРОЙКИ БАЗЫ ДАННЫХ ---

# Создаем файл базы данных sqlite
engine = create_engine('sqlite:///messenger.db', connect_args={"check_same_thread": False})

# Создаем фабрику сессий для main.py
Session = sessionmaker(bind=engine)

def init_db():
    """Функция для создания таблиц в базе данных"""
    Base.metadata.create_all(engine)
    print("База данных и таблицы успешно созданы!")

if __name__ == "__main__":
    init_db()