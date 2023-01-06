from unittest import main, TestCase, skip
from decimal import Decimal
from unittest.mock import MagicMock
from assets import assets
from exchange import Exchange
from sqlalchemy import create_engine
from db import Base, Asset
from sqlalchemy.orm import Session
from mock_blockchain import MockBlockchain
from time import sleep
from blockchain_monitor import blockchain_monitor
from env import TEST_DB

def fresh_exchange():
  engine = create_engine(TEST_DB)
  Base.metadata.drop_all(engine)
  Base.metadata.create_all(engine)
  blockchain_monitor.stop()
  session = Session(engine)
  session.add(Asset(name='XMR', height=0))
  session.add(Asset(name='BTC', height=0))
  session.commit()
  assets['BTC'] = MockBlockchain(8)
  assets['XMR'] = MockBlockchain(12)
  blockchain_monitor.start(TEST_DB, True)
  return Exchange(TEST_DB)

def deposit(asset, address, amount):
  assets[asset].deposit(address, amount)
  sleep(0.2)

class TestExchange(TestCase):
  def test_deposit(self):
    exchange = fresh_exchange()
    user = exchange.new_user()['api_key']
    self.assertEqual(exchange.deposit('unknown', 'BTC'), {'error': 'api_key not found'})
    self.assertEqual(exchange.deposit(user, 'unknown'), {'error': 'Currency not found'})
    assets['BTC'].get_new_deposit_address = MagicMock(return_value='1btcaddress')
    assets['XMR'].get_new_deposit_address = MagicMock(return_value='1xmraddress')
    self.assertEqual(exchange.deposit(user, 'BTC'), {'address': '1btcaddress'})
    self.assertEqual(exchange.deposit(user, 'BTC'), {'address': '1btcaddress'})
    self.assertEqual(exchange.deposit(user, 'XMR'), {'address': '1xmraddress'})
    # test actual deposit
    deposit('BTC', '1btcaddress', Decimal('0.01'))
    self.assertEqual(exchange.balances(user), {"BTC": Decimal('0.01'), "XMR": 0})
    deposit('BTC', '1btcaddress', Decimal('0.015'))
    self.assertEqual(exchange.balances(user), {"BTC": Decimal('0.025'), "XMR": 0})
    deposit('XMR', '1xmraddress', Decimal('0.015'))
    self.assertEqual(exchange.balances(user), {"BTC": Decimal('0.025'), "XMR": Decimal('0.015')})
    blockchain_monitor.stop()

  def test_withdrawal(self):
    exchange = fresh_exchange()
    user = exchange.new_user()['api_key']
    # deposit
    deposit('BTC', exchange.deposit(user, 'BTC')['address'], Decimal('0.01'))
    # withdraw
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('-1')), {'error': 'Invalid amount'})
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.00009999')), {'error': 'Amount too small'})
    self.assertEqual(exchange.withdraw('unknown', 'BTC', '1btcaddress', Decimal('1')), {'error': 'api_key not found'})
    self.assertEqual(exchange.withdraw(user, 'unknown', '1btcaddress', Decimal('1')), {'error': 'Currency not found'})
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.01000001')), {'error': 'Not enough funds'})
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.005')), {'success': True})
    self.assertEqual(exchange.balances(user), {"BTC": Decimal('0.0049'), "XMR": 0})
    self.assertEqual(exchange.withdraw(user, 'BTC', '1btcaddress', Decimal('0.0025')), {'success': True})
    self.assertEqual(exchange.balances(user), {"BTC": Decimal('0.0023'), "XMR": 0})
    self.assertEqual(assets['BTC'].withdrawals(), [
        ('1btcaddress', Decimal('0.005')),
        ('1btcaddress', Decimal('0.0025'))
      ])
    blockchain_monitor.stop()

  def test_trades(self):
    exchange = fresh_exchange()
    user1 = exchange.new_user()['api_key']
    user2 = exchange.new_user()['api_key']
    deposit('BTC', exchange.deposit(user1, 'BTC')['address'], Decimal('0.01000000'))
    deposit('XMR', exchange.deposit(user2, 'XMR')['address'], Decimal('1.00000000'))
    self.assertEqual(exchange.buy(user1, Decimal('0.01'), Decimal('0.01')), {"order_id": 1})
    self.assertEqual(exchange.orders(user1), [
      {
        'id': 1,
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
        'executed': Decimal('0'),
        'type': 'BUY'
      }
    ])
    self.assertEqual(exchange.sell(user2, Decimal('0.01'), Decimal('0.01')), {"success": True})
    self.assertEqual(exchange.orders(user1), [])
    self.assertEqual(exchange.orders(user2), [])
    self.assertEqual(exchange.trades(user1), [
      {
        'type': 'BUY',
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
      }
    ])
    self.assertEqual(exchange.trades(user2), [
      {
        'type': 'SELL',
        'amount': Decimal('0.01'),
        'price': Decimal('0.01'),
      }
    ])
    self.assertEqual(exchange.balances(user1), {"BTC": Decimal('0.01')-Decimal('0.01')*Decimal('0.01'), "XMR": Decimal('0.01')})
    self.assertEqual(exchange.balances(user2), {"BTC": Decimal('0.0001'), "XMR": Decimal("0.99")})
    blockchain_monitor.stop()

if __name__ == '__main__':
  main()
