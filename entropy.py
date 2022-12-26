from secrets import randbits
from random import getrandbits

def random_128_bit_string(secure=True):
  num = randbits(128) if secure else getrandbits(128)
  arr = []
  arr_append = arr.append
  _divmod = divmod
  ALPHABET = "23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
  base = len(ALPHABET)
  while num:
    num, rem = _divmod(num, base)
    arr_append(ALPHABET[rem])
  return ''.join(arr)
