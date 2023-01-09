import enum
from sqlalchemy import Integer, Numeric, Enum, Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class OrderType(enum.Enum):
  BUY = 1
  SELL = 2

class Asset(Base):
  __tablename__ = 'assets'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  height = Column(Integer)

class Market(Base):
  __tablename__ = 'markets'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  asset_id = Column(Integer, ForeignKey('assets.id'))
  currency_id = Column(Integer, ForeignKey('assets.id'))

  asset = relationship('Asset', foreign_keys=[asset_id])
  currency = relationship('Asset', foreign_keys=[currency_id])
  orders = relationship('Order')
  trades = relationship('Trade')

class User(Base):
  __tablename__ = 'users'

  id = Column(Integer, primary_key=True)
  api_key = Column(String)

  balances = relationship('Balance')
  orders = relationship('Order')
  deposit_addresses = relationship('DepositAddress')
  trades = relationship('Trade')

class DepositAddress(Base):
  __tablename__ = 'deposit_addresses'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  asset_id = Column(Integer, ForeignKey('assets.id'))
  address = Column(String)

  user = relationship('User', back_populates='deposit_addresses')
  asset = relationship('Asset')

  __table_args__ = (UniqueConstraint('user_id', 'asset_id'),)

class Balance(Base):
  __tablename__ = 'balances'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  asset_id = Column(Integer, ForeignKey('assets.id'))
  amount = Column(Numeric(28, 18))

  asset = relationship('Asset')
  user = relationship('User', back_populates='balances')

  __table_args__ = (UniqueConstraint('user_id', 'asset_id'),)

class Order(Base):
  __tablename__ = 'orders'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  market_id = Column(Integer, ForeignKey('markets.id'))
  order_type = Column(Enum(OrderType))
  amount = Column(Numeric(28, 18))
  executed = Column(Numeric(28, 18))
  price = Column(Numeric(28, 18))

  user = relationship('User', back_populates='orders')
  market = relationship('Market', back_populates='orders')

class Trade(Base):
  __tablename__ = 'trades'

  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, ForeignKey('users.id'))
  market_id = Column(Integer, ForeignKey('markets.id'))
  timestamp = Column(Integer)
  order_type = Column(Enum(OrderType))
  amount = Column(Numeric(28, 18))
  price = Column(Numeric(28, 18))
  fee = Column(Numeric(28, 18))

  user = relationship('User', back_populates='trades')
  market = relationship('Market', back_populates='trades')

class RateLimit(Base):
  __tablename__ = 'ratelimit'

  address = Column(String, primary_key=True)
  timestamps = Column(String)

class AutoOrder(Base):
  __tablename__ = 'autos'

  id = Column(String, primary_key=True)
  market_id = Column(Integer, ForeignKey('markets.id'))
  order_type = Column(Enum(OrderType))
  deposit_address = Column(String, unique=True)
  withdrawal_address = Column(String, unique=True)
  refund_address = Column(String)

  deposits = relationship('AutoDeposit')
  market = relationship('Market')

class AutoDeposit(Base):
  __tablename__ = 'autodeposits'

  id = Column(Integer, primary_key=True)
  auto_id = Column(String, ForeignKey('autos.id'))
  amount = Column(Numeric(28, 18))

class Referrer(Base):
  __tablename__ = 'referrers'

  hostname = Column(String, primary_key=True)
  count = Column(Integer)
