from monero.backends.jsonrpc import JSONRPCWallet
from monero.wallet import Wallet
from env import MONERO_RPC_PASSWORD
from time import sleep

MINCONF = 15

def connect():
  return Wallet(JSONRPCWallet(host='10.128.0.4', user='tradeapi', password=MONERO_RPC_PASSWORD))

class XMR:
  def height(self):
    while True:
      try:
        wallet = connect()
        return wallet.height() - MINCONF
      except:
        sleep(1)

  def get_incoming_txs(self, height):
    while True:
      try:
        wallet = connect()
        txs = wallet.incoming(min_height=height, max_height=height)
        return [(tx.local_address, tx.amount) for tx in txs]
      except:
        sleep(1)

  def withdraw(self, address, amount):
    while True:
      try:
        wallet = connect()
        wallet.transfer(address, amount)
      except ValueError:
        raise ValueError
      except:
        sleep(1)

  def get_new_deposit_address(self):
    while True:
      try:
        wallet = connect()
        return wallet.new_address()[0]
      except:
        sleep(1)

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def round_down(self, amount):
    return floor(amount * 10**12) / Decimal(10**12)

  def withdrawal_fee(self):
    return Decimal('0.0001')
