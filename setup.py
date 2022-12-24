from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from db import Base, Asset, Market

if __name__ == '__main__':
  engine = create_engine('postgresql://:@localhost/tradeapi')
  Base.metadata.create_all(engine)
  session = Session(engine)
  session.add(Market(asset=Asset(name='XMR', height=2139160), currency=Asset(name='BTC', height=2412691)))
  session.commit()
