from monero.backends.jsonrpc import JSONRPCWallet
from monero.wallet import Wallet
from env import MONERO_RPC_PASSWORD

MINCONF = 15

def connect():
  return Wallet(JSONRPCWallet(host='10.128.0.4', user='tradeapi', password=MONERO_RPC_PASSWORD))

class XMR:
  def height(self):
    wallet = connect()
    return wallet.height() - MINCONF

  def get_incoming_txs(self, height):
    wallet = connect()
    txs = wallet.incoming(min_height=height, max_height=height)
    return [(tx.local_address, tx.amount) for tx in txs]

  def withdraw(self, address, amount):
    wallet = connect()
    wallet.transfer(address, amount)

  def get_new_deposit_address(self):
    wallet = connect()
    return wallet.new_address()[0]

  def minimum_withdrawal(self):
    return Decimal('0.0001')
