from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset
from env import DB

if __name__ == '__main__':
  engine = create_engine(DB)
  Base.metadata.create_all(engine)
  session = Session(engine)
  session.add(Asset(name='BTC', height=768763))
  session.add(Asset(name='XMR', height=2784543))
  session.commit()
