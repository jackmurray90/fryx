from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset, Market
from env import DB

if __name__ == '__main__':
  engine = create_engine(DB)
  Base.metadata.create_all(engine)
  session = Session(engine)
  session.add(Market(asset=Asset(name='XMR', height=2784543), currency=Asset(name='BTC', height=768763)))
  session.commit()
