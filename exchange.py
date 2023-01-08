from db import Asset, DepositAddress, User, Balance, Order, OrderType, Trade, AutoOrder
from time import time
from assets import assets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from hashlib import sha256
from math import floor, ceil
from decimal import Decimal
from secrets import randbits

def hash_api_key(api_key):
  return sha256(api_key.encode('utf-8')).hexdigest()

def round_to_18_decimal_places(amount):
  return floor(amount * 10**18) / Decimal(10**18)

def round_up_to_18_decimal_places(amount):
  return ceil(amount * 10**18) / Decimal(10**18)

def is_valid(amount):
  return amount > 0 and not amount.is_nan() and round_to_18_decimal_places(amount) == amount

class Exchange:
  def __init__(self, db):
    self.engine = create_engine(db)

  def check_user(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
        return True
      except:
        return False

  def random_128_bit_string(self):
    num = randbits(128)
    arr = []
    arr_append = arr.append
    _divmod = divmod
    ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
    base = len(ALPHABET)
    while num:
      num, rem = _divmod(num, base)
      arr_append(ALPHABET[rem])
    return ''.join(arr)

  def get_balance(self, session, user, asset):
    try:
      [balance] = session.query(Balance).where((Balance.user == user) & (Balance.asset == asset))
    except:
      balance = Balance(user_id=user.id, asset_id=asset.id, amount=0)
      session.add(balance)
      session.commit()
    return balance

  # API Methods

  def order_book(self):
    with Session(self.engine) as session:
      orders = session.query(Order).all()
      return {'buy': [{
          'amount': order.amount,
          'executed': order.executed,
          'price': order.price
          } for order in orders if order.order_type == OrderType.BUY],
        'sell': [{
          'amount': order.amount,
          'executed': order.executed,
          'price': order.price
          } for order in orders if order.order_type == OrderType.SELL]}

  def new_user(self):
    api_key = self.random_128_bit_string()
    user = User(api_key=hash_api_key(api_key))
    with Session(self.engine) as session:
      session.add(user)
      session.commit()
      return {'api_key': api_key}

  def deposit(self, api_key, asset_name):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name.upper())
      except:
        return {'error': 'Currency not found'}
      try:
        [deposit_address] = session.query(DepositAddress).where((DepositAddress.user == user) & (DepositAddress.asset == asset))
      except:
        deposit_address = DepositAddress(
            user_id=user.id,
            asset_id=asset.id,
            address=assets[asset.name].get_new_deposit_address()
          )
        session.add(deposit_address)
        session.commit()
      return {'address': deposit_address.address}

  def withdraw(self, api_key, asset_name, address, amount):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name.upper())
      except:
        return {'error': 'Currency not found'}
      if not is_valid(amount) or amount != assets[asset.name].round_down(amount):
        return {'error': 'Invalid amount'}
      amount_to_withdraw = amount - assets[asset.name].withdrawal_fee()
      if amount_to_withdraw < assets[asset.name].minimum_withdrawal():
        return {'error': 'Amount too small'}
      if not assets[asset.name].validate_address(address):
        return {'error': 'Invalid address'}
      balance = self.get_balance(session, user, asset)
      if balance.amount < amount:
        return {'error': 'Not enough funds'}
      assets[asset.name].withdraw(address, amount_to_withdraw)
      balance.amount -= amount
      session.commit()
      return {'success': True}

  def balances(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      return dict([(asset.name, self.get_balance(session, user, asset).amount) for asset in session.query(Asset).all()])

  def orders(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      return [{
          'id': order.id,
          'type': 'buy' if order.order_type == OrderType.BUY else 'sell',
          'amount': order.amount,
          'executed': order.executed,
          'price': order.price
        } for order in user.orders]

  def trades(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      return [{
          'type': 'buy' if trade.order_type == OrderType.BUY else 'sell',
          'amount': trade.amount,
          'price': trade.price
        } for trade in user.trades]

  def buy(self, api_key, amount, price):
    if not is_valid(amount):
      return {'error': 'Invalid amount'}
    if not is_valid(price):
      return {'error': 'Invalid price'}
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      [asset] = session.query(Asset).where(Asset.name == 'XMR')
      [currency] = session.query(Asset).where(Asset.name == 'BTC')
      session.begin_nested()
      session.execute('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;')
      balance = self.get_balance(session, user, currency)
      if round_up_to_18_decimal_places(amount * price) > balance.amount:
        session.commit()
        session.commit()
        return {'error':'Insufficient BTC'}
      balance.amount -= round_up_to_18_decimal_places(amount * price)
      foundStoppingPoint = False
      while not foundStoppingPoint:
        orders = session.query(Order).where(
            Order.order_type == OrderType.SELL
          ).order_by(
            Order.price.asc(),
            Order.id.asc()
          ).limit(1000).all()
        if orders == []:
          foundStoppingPoint = True
        for order in orders:
          if order.price > price:
            foundStoppingPoint = True
            break
          trade_amount = min(amount, order.amount - order.executed)
          session.add(Trade(user_id=order.user_id, order_type=OrderType.SELL, amount=trade_amount, price=order.price, timestamp=int(time())))
          session.add(Trade(user_id=user.id, order_type=OrderType.BUY, amount=trade_amount, price=order.price, timestamp=int(time())))
          matching_user_currency_balance = self.get_balance(session, order.user, currency)
          matching_user_currency_balance.amount += round_to_18_decimal_places(trade_amount * order.price)
          user_asset_balance = self.get_balance(session, user, asset)
          user_asset_balance.amount += trade_amount
          order.executed += trade_amount
          amount -= trade_amount
          if order.executed == order.amount:
            session.delete(order)
          else:
            foundStoppingPoint = True
            break
          if amount == 0:
            foundStoppingPoint = True
            break
      if amount > 0:
        order = Order(user_id=user.id, order_type=OrderType.BUY, amount=amount, executed=0, price=price)
        session.add(order)
        session.commit()
        session.commit()
        return {'order_id': order.id}
      session.commit()
      session.commit()
      return {'success': True}

  def sell(self, api_key, amount, price):
    if not is_valid(amount):
      return {'error': 'Invalid amount'}
    if not is_valid(price):
      return {'error': 'Invalid price'}
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error': 'api_key not found'}
      [asset] = session.query(Asset).where(Asset.name == 'XMR')
      [currency] = session.query(Asset).where(Asset.name == 'BTC')
      session.begin_nested()
      session.execute('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;')
      balance = self.get_balance(session, user, asset)
      if amount > balance.amount:
        session.commit()
        session.commit()
        return {'error': 'Insufficient XMR'}
      balance.amount -= amount
      foundStoppingPoint = False
      while not foundStoppingPoint:
        orders = session.query(Order).where(
            Order.order_type == OrderType.BUY
          ).order_by(
            Order.price.desc(),
            Order.id.asc()
          ).limit(1000).all()
        if orders == []:
          foundStoppingPoint = True
        for order in orders:
          if order.price > price:
            foundStoppingPoint = True
            break
          trade_amount = min(amount, order.amount - order.executed)
          session.add(Trade(user_id=order.user_id, order_type=OrderType.BUY, amount=trade_amount, price=order.price, timestamp=int(time())))
          session.add(Trade(user_id=user.id, order_type=OrderType.SELL, amount=trade_amount, price=order.price, timestamp=int(time())))
          matching_user_currency_balance = self.get_balance(session, order.user, asset)
          matching_user_currency_balance.amount += trade_amount
          user_asset_balance = self.get_balance(session, user, currency)
          user_asset_balance.amount += round_to_18_decimal_places(trade_amount * order.price)
          order.executed += trade_amount
          amount -= trade_amount
          if order.executed == order.amount:
            session.delete(order)
          else:
            foundStoppingPoint = True
            break
          if amount == 0:
            foundStopppingPoint = True
            break
      if amount > 0:
        order = Order(user_id=user.id, order_type=OrderType.SELL, amount=amount, executed=0, price=price)
        session.add(order)
        session.commit()
        session.commit()
        return {'order_id': order.id}
      session.commit()
      session.commit()
      return {'success': True}

  def cancel(self, api_key, order_id):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return {'error':'api_key not found'}
      session.begin_nested()
      session.execute('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;')
      try:
        [order] = session.query(Order).where((Order.id == order_id) & (Order.user == user))
      except:
        session.commit()
        session.commit()
        return {'error': 'Order not found'}
      [asset] = session.query(Asset).where(Asset.name == ('XMR' if order.order_type == OrderType.SELL else 'BTC'))
      balance = self.get_balance(session, order.user, asset)
      if order.order_type == OrderType.SELL:
        balance.amount += order.amount - order.executed
      else:
        balance.amount += round_to_18_decimal_places((order.amount - order.executed) * order.price)
      session.delete(order)
      session.commit()
      session.commit()
      return {'success': True}

  def auto(self, order_type, address, refund_address):
    with Session(self.engine) as session:
      try:
        deposit_address = assets['XMR' if order_type == OrderType.SELL else 'BTC'].get_new_deposit_address()
        auto_order = AutoOrder(id=self.random_128_bit_string(), order_type=order_type, withdrawal_address=address, deposit_address=deposit_address, refund_address=refund_address)
        session.add(auto_order)
        session.commit()
        return auto_order.id
      except:
        return None

  def get_auto(self, id):
    with Session(self.engine) as session:
      try:
        [auto] = session.query(AutoOrder).where(AutoOrder.id == id)
      except:
        return None, [], []
      return auto.deposit_address, assets['XMR' if auto.order_type == OrderType.SELL else 'BTC'].get_unconfirmed_transactions(auto.deposit_address), [d.amount for d in reversed(auto.deposits)]
