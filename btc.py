from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from math import floor
from decimal import Decimal
from env import BITCOIN
from time import sleep
from http.client import CannotSendRequest

MINCONF = 2

def connect():
  rpc = AuthServiceProxy(BITCOIN)
  try:
    rpc.loadwallet('tradeapi')
  except JSONRPCException:
    pass
  return rpc

class BTC:
  def height(self):
    while True:
      try:
        rpc = connect()
        return rpc.getblockcount() - MINCONF
      except CannotSendRequest:
        sleep(1)

  def get_incoming_txs(self, height):
    while True:
      try:
        rpc = connect()
        txs = rpc.listsinceblock(rpc.getblockhash(height-1))
        incoming_txs = []
        for tx in txs['transactions']:
          if tx['category'] == 'receive' and tx['blockheight'] == height:
            incoming_txs.append((tx['address'], tx['amount']))
        return incoming_txs
      except CannotSendRequest:
        sleep(1)

  def withdraw(self, address, amount):
    while True:
      try:
        rpc = connect()
        rpc.send({address: amount})
      except CannotSendRequest:
        sleep(1)

  def get_new_deposit_address(self):
    while True:
      try:
        rpc = connect()
        return rpc.getnewaddress()
      except CannotSendRequest:
        sleep(1)

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def round_down(self, amount):
    return floor(amount * 10**8) / Decimal(10**8)
