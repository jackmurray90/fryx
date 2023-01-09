from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset
from env import DB

if __name__ == '__main__':
  engine = create_engine(DB)
  Base.metadata.create_all(engine)
  session = Session(engine)
  btc = Asset(name='BTC', height=768763)
  xmr = Asset(name='XMR', height=2784543)
  session.add(btc)
  session.add(xmr)
  session.add(Market(name='BTCXMR', asset_id=xmr.id, currency_id=btc.id))
  session.add(User(api_key='auto'))
  session.commit()
