from sqlalchemy import create_engine, Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

import time

import json

check_in_seconds = 120

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, unique=True)
    check_at = Column(DateTime, nullable=False, default=datetime.datetime.now() + datetime.timedelta(seconds=check_in_seconds))
    guild = Column(Integer)

# Create an engine and bind the session to it
User_Engine = create_engine('sqlite:///users.db')
Base.metadata.create_all(User_Engine)
User_SessionMaker = sessionmaker(bind=User_Engine)
users_session = User_SessionMaker()

class Server(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True, unique=True)
    role_id = Column(Integer,default=None)
    check_in_seconds = Column(Integer, default=120)

# Create an engine and bind the session to it
server_engine = create_engine('sqlite:///servers.db')
Base.metadata.create_all(server_engine)
Server_SessionMaker = sessionmaker(bind=server_engine)
server_session = Server_SessionMaker()