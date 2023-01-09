from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset, Market, User
from assets import assets
from env import DB

if __name__ == '__main__':
  engine = create_engine(DB)
  Base.metadata.create_all(engine)
  session = Session(engine)
  session.add(Market(name='BTCXMR',
    asset=Asset(name='XMR', height=asset['XMR'].height()),
    currency=Asset(name='BTC', height=asset['BTC'].height())))
  session.add(User(api_key='auto'))
  session.commit()
