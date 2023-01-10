from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset, Market, User, LoginCode
from assets import assets
from env import DB

if __name__ == '__main__':
  engine = create_engine(DB)
  LoginCode.metadata.create_all(engine)
