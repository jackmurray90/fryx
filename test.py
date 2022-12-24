from unittest import main, TestCase, skip
from decimal import Decimal
from unittest.mock import MagicMock
from assets import assets
from exchange import Exchange
from sqlalchemy import create_engine
from db import Base, Market, Asset
from sqlalchemy.orm import Session
from mock_blockchain import MockBlockchain
from time import sleep

DB = 'postgresql://:@localhost/tradeapi_test'

def fresh_exchange():
  engine = create_engine(DB)
  Base.metadata.drop_all(engine)
  Base.metadata.create_all(engine)
  session = Session(engine)
  session.add(Market(asset=Asset(name='XMR', height=0), currency=Asset(name='BTC', height=0)))
  session.commit()
  assets['BTC'] = MockBlockchain(8)
  assets['XMR'] = MockBlockchain(12)
  return Exchange(DB, rapid_update=True)

def deposit(asset, address, amount):
  assets[asset].deposit(address, amount)
  sleep(0.2)

class TestExchange(TestCase):
  def test_deposit(self):
    exchange = fresh_exchange()
    user = exchange.new_user()
    self.assertEqual(exchange.deposit('unknown', 'BTC'), 'api_key not found')
    self.assertEqual(exchange.deposit(user, 'unknown'), 'asset not found')
    assets['BTC'].get_new_deposit_address = MagicMock(return_value='1btcaddress')
    assets['XMR'].get_new_deposit_address = MagicMock(return_value='1xmraddress')
    self.assertEqual(exchange.deposit(user, 'BTC'), '1btcaddress')
    self.assertEqual(exchange.deposit(user, 'BTC'), '1btcaddress')
    self.assertEqual(exchange.deposit(user, 'XMR'), '1xmraddress')
    # test actual deposit
    deposit('BTC', '1btcaddress', Decimal('0.01'))
    self.assertEqual(exchange.balance(user, 'BTC'), Decimal('0.01'))
    deposit('BTC', '1btcaddress', Decimal('0.015'))
    self.assertEqual(exchange.balance(user, 'BTC'), Decimal('0.025'))
    self.assertEqual(exchange.balance(user, 'XMR'), 0)
    deposit('XMR', '1xmraddress', Decimal('0.015'))
    self.assertEqual(exchange.balance(user, 'XMR'), Decimal('0.015'))
    exchange.stop()

  def test_withdrawal(self):
    exchange = fresh_exchange()
    user = exchange.new_user()
    # deposit
    deposit('BTC', exchange.deposit(user, 'BTC'), Decimal('0.01'))
    # withdraw
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('-1')), 'Invalid amount')
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.00009999')), 'amount too small')
    self.assertEqual(exchange.withdraw('unknown', 'BTC', '1btcaddress', Decimal('1')), 'api_key not found')
    self.assertEqual(exchange.withdraw(user, 'unknown', '1btcaddress', Decimal('1')), 'asset not found')
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.01000001')), 'Not enough funds')
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.005')), 'Success')
    self.assertEqual(exchange.balance(user, 'BTC'), Decimal('0.005'))
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.0025')), 'Success')
    self.assertEqual(exchange.balance(user, 'BTC'), Decimal('0.0025'))
    self.assertEqual(assets['BTC'].withdrawals(), [
        ('1btcaddress', Decimal('0.005')),
        ('1btcaddress', Decimal('0.0025'))
      ])
    exchange.stop()

  def test_trades(self):
    exchange = fresh_exchange()
    user1 = exchange.new_user()
    user2 = exchange.new_user()
    deposit('BTC', exchange.deposit(user1, 'BTC'), Decimal('0.01000000'))
    deposit('XMR', exchange.deposit(user2, 'XMR'), Decimal('1.00000000'))
    self.assertEqual(exchange.buy(user1, 'XMR', 'BTC', Decimal('0.01'), Decimal('0.01')), 1)
    self.assertEqual(exchange.orders(user1), [
      {
        'asset': 'XMR',
        'currency': 'BTC',
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
        'type': 'BUY'
      }
    ])
    exchange.sell(user2, 'XMR', 'BTC', Decimal('0.01'), Decimal('0.01'))
    self.assertEqual(exchange.orders(user1), [])
    self.assertEqual(exchange.orders(user2), [])
    self.assertEqual(exchange.trades(user1), [
      {
        'asset': 'XMR',
        'currency': 'BTC',
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
        'type': 'BUY'
      }
    ])
    self.assertEqual(exchange.trades(user2), [
      {
        'asset': 'XMR',
        'currency': 'BTC',
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
        'type': 'SELL'
      }
    ])
    self.assertEqual(exchange.balance(user1, 'BTC'), Decimal('0.01')-Decimal('0.0001'))
    self.assertEqual(exchange.balance(user2, 'BTC'), Decimal('0.0001')-Decimal('0.0001')*Decimal('0.001'))
    self.assertEqual(exchange.balance(user1, 'XMR'), Decimal('0.01'))
    self.assertEqual(exchange.balance(user2, 'XMR'), Decimal('0.99'))
    exchange.stop()

if __name__ == '__main__':
  main()
