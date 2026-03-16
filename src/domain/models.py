from sqlalchemy import create_engine, String, Integer, Date, select, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session, relationship
from datetime import date
from typing import Optional,List



engine = create_engine('sqlite:///bandhub.db')

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__="users"
    id: Mapped[int]= mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50),nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[date] = mapped_column(Date, default=date.today,nullable=False)


class Profile(Base):
    __tablename__="profile"
    id: Mapped[int]= mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id",ondelete="CASCADE"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    user: Mapped[User] = relationship("User", backref="profile", uselist=False)
Base.metadata.create_all(engine)