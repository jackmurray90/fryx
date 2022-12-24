from bitcoinrpc.authproxy import AuthServiceProxy
from math import floor
from decimal import Decimal

MINCONF = 2

def connect():
  rpc = AuthServiceProxy('http://:abcd@127.0.0.1:18332')
  try:
    rpc.loadwallet("test")
  except:
    pass
  return rpc

class BTC:
  def height(self):
    rpc = connect()
    return rpc.getblockcount() - MINCONF

  def get_incoming_txs(self, height):
    rpc = connect()
    block = rpc.getblock(rpc.getblockhash(height))
    incoming_txs = []
    for txid in block['tx']:
      try:
        transaction = rpc.gettransaction(txid)
      except:
        continue
      for details in transaction['details']:
        if details['category'] == 'receive':
          incoming_txs.append((details['address'], details['amount']))
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
