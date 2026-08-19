from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    terms_accepted = Column(Boolean, default=False)
    # Patient profile
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)  # "male" | "female" | "other"
    notes = Column(Text, nullable=True)     # Medical notes, allergies, etc.
