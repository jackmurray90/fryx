from monerorpc.authproxy import AuthServiceProxy, JSONRPCException
from env import MONERO
from time import sleep
from decimal import Decimal
from http.client import CannotSendRequest

MINCONF = 24

class XMR:
  def height(self):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        return rpc.get_height()['height'] - MINCONF
      except Exception as e:
        sleep(1)

  def get_incoming_txs(self, height):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        txs = rpc.get_transfers({
          'in': True,
          'filter_by_height': True,
          'min_height': height-1,
          'max_height': height
          }).get('in', [])
        return [(tx['address'], Decimal(tx['amount'])/(10**12)) for tx in txs if tx['height'] == height and tx['locked'] == False]
      except:
        sleep(1)

  def get_unconfirmed_transactions(self, address):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        txs = rpc.get_transfers({
          'in': True,
          'filter_by_height': True,
          'min_height': self.height()-1,
          }).get('in', [])
        return [{'amount': Decimal(tx['amount'])/(10**12), 'confirmations': tx.get('confirmations')} for tx in txs if tx['address'] == address]
      except:
        sleep(1)

  def withdraw(self, address, amount):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        rpc.transfer({
          'destinations': [{
            'amount': int(amount * 10**12),
            'address': address
            }]
          })
        break
      except JSONRPCException:
        break
      except:
        sleep(1)

  def get_new_deposit_address(self):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        return rpc.create_address({'account_index': 0})['address']
      except:
        sleep(1)

  def validate_address(self, address):
    while True:
      try:
        rpc = AuthServiceProxy(MONERO)
        return rpc.validate_address({'address': address})['valid']
      except:
        sleep(1)

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def round_down(self, amount):
    return floor(amount * 10**12) / Decimal(10**12)

  def withdrawal_fee(self):
    return Decimal('0.0001')
