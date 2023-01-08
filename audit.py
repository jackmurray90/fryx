from sqlalchemy.orm import Session
from assets import assets
from db import Asset, Balance, DepositAddress, AutoOrder, Order, Trade, OrderType
from sqlalchemy import create_engine
from threading import Thread
from time import sleep
from exchange import round_to_18_decimal_places, round_up_to_18_decimal_places
from bitcoinrpc.authproxy import AuthServiceProxy as BitcoinAuthServiceProxy
from monerorpc.authproxy import AuthServiceProxy as MoneroAuthServiceProxy
from env import DB, BITCOIN, MONERO
from decimal import Decimal

if __name__ == '__main__':
  engine = create_engine(DB)

  with Session(engine) as session:
    [btc] = session.query(Asset).where(Asset.name == 'BTC')
    [xmr] = session.query(Asset).where(Asset.name == 'XMR')
    btc_balances = session.query(Balance).where(Balance.asset_id == btc.id)
    xmr_balances = session.query(Balance).where(Balance.asset_id == xmr.id)
    buy_orders = session.query(Order).where(Order.order_type == OrderType.BUY)
    sell_orders = session.query(Order).where(Order.order_type == OrderType.SELL)
    total_btc_in_accounts = sum([balance.amount for balance in btc_balances])
    total_btc_in_orders = sum([round_up_to_18_decimal_places(order.amount * order.price) for order in buy_orders])
    total_xmr_in_accounts = sum([balance.amount for balance in xmr_balances])
    total_xmr_in_orders = sum([order.amount for order in sell_orders])
    total_btc = total_btc_in_accounts + total_btc_in_orders
    total_xmr = total_xmr_in_accounts + total_xmr_in_orders
    btc_rpc = BitcoinAuthServiceProxy(BITCOIN)
    xmr_rpc = MoneroAuthServiceProxy(MONERO)
    btc_balance = Decimal(btc_rpc.getbalance())
    xmr_balance = Decimal(xmr_rpc.get_balance()['balance'])/10**12

    if btc_balance >= total_btc:
      print("Bitcoin passed.")
    else:
      print("Bitcoin failed.")
    if xmr_balance >= total_xmr:
      print("Monero passed.")
    else:
      print("Monero failed.")
    print("btc wallet balance is ", btc_balance, "total in accounts is", total_btc_in_accounts, "total in orders is", total_btc_in_orders)
    print("difference is", btc_balance-total_btc)
    print("xmr wallet balance is ", xmr_balance, "total in accounts is", total_xmr_in_accounts, "total in orders is", total_xmr_in_orders)
    print("difference is", xmr_balance-total_xmr)
