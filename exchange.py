from db import Asset, DepositAddress, User, Balance, Order, Market, OrderType, Trade
from assets import assets
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from threading import Thread
from time import sleep
from hashlib import sha256
from math import floor, ceil
from decimal import Decimal
from signal import signal, SIGTERM, SIGINT
from secrets import randbits

def hash_api_key(api_key):
  return sha256(api_key.encode('utf-8')).hexdigest()

def round_to_18_decimal_places(amount):
  return floor(amount * 10**18) / Decimal(10**18)

def round_up_to_18_decimal_places(amount):
  return ceil(amount * 10**18) / Decimal(10**18)

def is_valid(amount):
  return amount > 0 and not amount.is_nan() and round_to_18_decimal_places(amount) == amount

FEE = Decimal('0.001')

class Exchange:
  def __init__(self, db, rapid_update=False):
    self.engine = create_engine(db)
    self.rapid_update = rapid_update
    self.stopped = False
    with Session(self.engine) as session:
      for asset in session.query(Asset):
        Thread(target=self.monitor_blockchain, args=(asset.name,)).start()
    signal(SIGINT, self.stop)
    signal(SIGTERM, self.stop)

  def stop(self, *args):
    self.stopped = True

  def monitor_blockchain(self, asset_name):
    with Session(self.engine) as session:
      [asset] = session.query(Asset).where(Asset.name == asset_name)
      while not self.stopped:
        while asset.height < assets[asset.name].height():
          print("Polling height=",asset.height)
          for address, amount in assets[asset.name].get_incoming_txs(asset.height):
            try:
              [deposit_address] = session.query(DepositAddress).where(DepositAddress.address == address)
            except:
              continue
            balance = self.get_balance(session, deposit_address.user, asset)
            balance.amount += amount
            session.commit()
          asset.height += 1
          session.commit()
        sleep(0.1 if self.rapid_update else 1)

  def check_user(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
        return True
      except:
        return False

  # API Methods

  def markets(self):
    with Session(self.engine) as session:
      return [{
        'asset': market.asset.name,
        'currency': market.currency.name
       } for market in session.query(Market)]

  def get_balance(self, session, user, asset):
    try:
      [balance] = session.query(Balance).where((Balance.user == user) & (Balance.asset == asset))
    except:
      balance = Balance(user=user, asset=asset, amount=0)
      session.add(balance)
      session.commit()
    return balance

  def new_user(self):
    num = randbits(128) if secure else getrandbits(128)
    arr = []
    arr_append = arr.append
    _divmod = divmod
    ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
    base = len(ALPHABET)
    while num:
      num, rem = _divmod(num, base)
      arr_append(ALPHABET[rem])
    api_key = ''.join(arr)
    user = User(api_key=hash_api_key(api_key))
    with Session(self.engine) as session:
      session.add(user)
      session.commit()
      return api_key

  def deposit(self, api_key, asset_name):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name)
      except:
        return 'asset not found'
      try:
        [deposit_address] = session.query(DepositAddress).where((DepositAddress.user == user) & (DepositAddress.asset == asset))
      except:
        deposit_address = DepositAddress(
            user=user,
            asset=asset,
            address=assets[asset.name].get_new_deposit_address()
          )
        session.add(deposit_address)
        session.commit()
      return deposit_address.address

  def withdraw(self, api_key, asset_name, address, amount):
    if not is_valid(amount) or amount != assets[asset.name].round_down(amount):
      return 'Invalid amount'
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name)
      except:
        return 'asset not found'
      if amount < assets[asset.name].minimum_withdrawal():
        return 'amount too small'
      balance = self.get_balance(session, user, asset)
      if balance.amount < amount:
        return 'Not enough funds'
      try:
        assets[asset.name].withdraw(address, amount)
      except:
        return 'Invalid address'
      balance.amount -= amount
      session.commit()
      return 'Success'

  def balance(self, api_key, asset_name):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      if asset_name is None:
        return [{
          'asset': asset.name,
          'amount': self.get_balance(session, user, asset).amount
          } for asset in session.query(Asset).all()]
      else:
        try:
          [asset] = session.query(Asset).where(Asset.name == asset_name)
        except:
          return 'asset not found'
        balance = self.get_balance(session, user, asset)
        return balance.amount

  def orders(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      return [{
          'asset': order.market.asset.name,
          'currency': order.market.currency.name,
          'type': 'BUY' if order.order_type == OrderType.BUY else 'SELL',
          'amount': order.amount,
          'price': order.price
        } for order in user.orders]

  def trades(self, api_key):
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      return [{
          'asset': trade.market.asset.name,
          'currency': trade.market.currency.name,
          'type': 'BUY' if trade.order_type == OrderType.BUY else 'SELL',
          'amount': trade.amount,
          'price': trade.price,
          'fee': trade.fee
        } for trade in user.trades]

  def buy(self, api_key, asset_name, currency_name, amount, price):
    if not is_valid(amount):
      return 'Invalid amount'
    if not is_valid(price):
      return 'Invalid price'
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name)
      except:
        return 'asset not found'
      try:
        [currency] = session.query(Asset).where(Asset.name == currency_name)
      except:
        return 'currency not found'
      try:
        [market] = session.query(Market).where((Market.asset == asset) & (Market.currency == currency))
      except:
        return 'Market not found'
      balance = self.get_balance(session, user, currency)
      if round_up_to_18_decimal_places(amount * price) > balance.amount:
        return 'Insufficient funds'
      balance.amount -= round_up_to_18_decimal_places(amount * price)
      foundStoppingPoint = False
      while not foundStoppingPoint:
        orders = session.query(Order).where(
            (Order.market == market) & (Order.order_type == OrderType.BUY)
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
          trade_amount = min(amount, order.amount)
          fee = round_up_to_18_decimal_places(order.amount * order.price * FEE)
          session.add(Trade(user=order.user, market=market, order_type=OrderType.SELL, amount=trade_amount, price=order.price, fee=fee))
          session.add(Trade(user=user, market=market, order_type=OrderType.BUY, amount=trade_amount, price=order.price, fee=fee))
          matching_user_currency_balance = self.get_balance(session, order.user, currency)
          matching_user_currency_balance.amount += round_to_18_decimal_places(trade_amount * order.price - FEE)
          user_asset_balance = self.get_balance(session, user, asset)
          user_asset_balance.amount += trade_amount
          order.amount -= trade_amount
          amount -= trade_amount
          if order.amount == 0:
            session.delete(order)
          else:
            foundStoppingPoint = True
            break
      if amount > 0:
        order = Order(user=user, market=market, order_type=OrderType.BUY, amount=amount, price=price)
        session.add(order)
        session.commit()
        return order.id
      session.commit()
      return 'Success'

  def sell(self, api_key, asset_name, currency_name, amount, price):
    if not is_valid(amount):
      return 'Invalid amount'
    if not is_valid(price):
      return 'Invalid price'
    with Session(self.engine) as session:
      try:
        [user] = session.query(User).where(User.api_key == hash_api_key(api_key))
      except:
        return 'api_key not found'
      try:
        [asset] = session.query(Asset).where(Asset.name == asset_name)
      except:
        return 'asset not found'
      try:
        [currency] = session.query(Asset).where(Asset.name == currency_name)
      except:
        return 'currency not found'
      try:
        [market] = session.query(Market).where((Market.asset == asset) & (Market.currency == currency))
      except:
        return 'Market not found'
      balance = self.get_balance(session, user, asset)
      if amount > balance.amount:
        return 'Insufficient assets'
      balance.amount -= amount
      foundStoppingPoint = False
      while not foundStoppingPoint:
        orders = session.query(Order).where(
            (Order.market == market) & (Order.order_type == OrderType.BUY)
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
          trade_amount = min(amount, order.amount)
          fee = round_up_to_18_decimal_places(order.amount * order.price * FEE)
          session.add(Trade(user=order.user, market=market, order_type=OrderType.BUY, amount=trade_amount, price=order.price, fee=fee))
          session.add(Trade(user=user, market=market, order_type=OrderType.SELL, amount=trade_amount, price=order.price, fee=fee))
          matching_user_currency_balance = self.get_balance(session, order.user, asset)
          matching_user_currency_balance.amount += trade_amount
          user_asset_balance = self.get_balance(session, user, currency)
          user_asset_balance.amount += round_to_18_decimal_places(trade_amount * order.price - fee)
          order.amount -= trade_amount
          amount -= trade_amount
          if order.amount == 0:
            session.delete(order)
          else:
            foundStoppingPoint = True
            break
      if amount > 0:
        order = Order(user=user, market=market, order_type=OrderType.SELL, amount=amount, price=price)
        session.add(order)
        session.commit()
        return order.id
      session.commit()
      return 'Success'
