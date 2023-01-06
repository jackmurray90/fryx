from random import choice
from string import ascii_lowercase
from math import floor
from decimal import Decimal

class TX:
  def __init__(self, height, address, amount):
    self.height = height
    self.address = address
    self.amount = amount

class MockBlockchain:
  def __init__(self, decimal_places):
    self._height = 0
    self.incoming_txs = []
    self._withdrawals = []
    self.decimal_places = decimal_places

  def deposit(self, address, amount):
    self.incoming_txs.append(TX(self._height, address, amount))
    self._height += 1

  def withdrawals(self):
    return self._withdrawals

  def height(self):
    return self._height

  def get_incoming_txs(self, height):
    return [(tx.address, tx.amount) for tx in self.incoming_txs if tx.height == height]

  def withdraw(self, address, amount):
    self._withdrawals.append((address, amount))

  def get_new_deposit_address(self):
    return ''.join(choice(ascii_lowercase) for i in range(100))

  def validate_address(self, address):
    return True

  def round_down(self, amount):
    return floor(amount * 10**self.decimal_places) / Decimal(10**self.decimal_places)

  def minimum_withdrawal(self):
    return Decimal('0.0001')

  def withdrawal_fee(self):
    return Decimal('0.0001')
