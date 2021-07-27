from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(120), index=True)
    full_name = Column(String(120))
    email = Column(String(200), unique=True, index=True)
    hashed_password = Column(String(60))
    disabled = Column(Boolean, default=True)
