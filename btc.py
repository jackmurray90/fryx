from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from math import floor
from decimal import Decimal
from env import BITCOIN
from time import sleep
from http.client import CannotSendRequest

MINCONF = 5

class BTC:
  def height(self):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        return rpc.getblockcount() - MINCONF
      except Exception as e:
        print(e)
        sleep(1)

  def get_incoming_txs(self, height):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        txs = rpc.listsinceblock(rpc.getblockhash(height-1))
        incoming_txs = []
        for tx in txs['transactions']:
          if tx.get('category') == 'receive' and tx.get('blockheight') == height:
            incoming_txs.append((tx.get('address'), tx.get('amount')))
        return incoming_txs
      except:
        sleep(1)

  def get_unconfirmed_transactions(self, address):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        txs = rpc.listsinceblock(rpc.getblockhash(self.height()))
        incoming_txs = []
        for tx in txs['transactions']:
          if tx.get('category') == 'receive' and tx.get('address') == address:
            incoming_txs.append({'amount': tx.get('amount'), 'confirmations': tx.get('confirmations') or 0})
        return incoming_txs
      except:
        sleep(1)

  def withdraw(self, address, amount):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        rpc.send({address: amount})
        break
      except CannotSendRequest:
        print("Cannot send request")
        sleep(1)

  def get_new_deposit_address(self):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        return rpc.getnewaddress()
      except Exception as e:
        print(e)
        sleep(1)

  def validate_address(self, address):
    while True:
      try:
        rpc = AuthServiceProxy(BITCOIN)
        return rpc.validateaddress(address)['isvalid']
      except:
        sleep(1)

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def round_down(self, amount):
    return floor(amount * 10**8) / Decimal(10**8)

  def withdrawal_fee(self):
    return Decimal('0.0001')
