from bitcoinrpc.authproxy import AuthServiceProxy
from math import floor
from decimal import Decimal
from env import BITCOIN

MINCONF = 2

def connect():
  rpc = AuthServiceProxy(BITCOIN)
  try:
    rpc.loadwallet('tradeapi')
  except:
    pass
  return rpc

class BTC:
  def height(self):
    rpc = connect()
    return rpc.getblockcount() - MINCONF

  def get_incoming_txs(self, height):
    rpc = connect()
    txs = rpc.listsinceblock(rpc.getblockhash(height-1))
    incoming_txs = []
    for tx in txs['transactions']:
      if tx['category'] == 'receive' and tx['blockheight'] == height:
        incoming_txs.append((tx['address'], tx['amount']))
    return incoming_txs

  def withdraw(self, address, amount):
    rpc = connect()
    rpc.send({address: amount})

  def get_new_deposit_address(self):
    rpc = connect()
    return rpc.getnewaddress()

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def round_down(self, amount):
    return floor(amount * 10**8) / Decimal(10**8)
