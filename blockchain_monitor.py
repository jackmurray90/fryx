from sqlalchemy.orm import Session
from assets import assets
from db import Asset, Balance, DepositAddress, AutoOrder
from sqlalchemy import create_engine
from threading import Thread
from time import sleep
from env import DB

class BlockchainMonitor:
  def __init__(self):
    self.rapid_update = False

  def start(self, db, rapid_update=False):
    self.engine = create_engine(db)
    self.running = True
    self.rapid_update = rapid_update
    with Session(self.engine) as session:
      for asset in session.query(Asset):
        Thread(target=self.monitor_blockchain, args=(asset.name,)).start()

  def stop(self):
    self.running = False
    sleep(0.2 if self.rapid_update else 1.1)

  def monitor_blockchain(self, asset_name):
    with Session(self.engine) as session:
      [asset] = session.query(Asset).where(Asset.name == asset_name)
      while self.running:
        while asset.height < assets[asset.name].height():
          print("Proccesing block height", asset.height, "for asset", asset_name)
          for address, amount in assets[asset.name].get_incoming_txs(asset.height):
            try:
              [auto] = session.query(AutoOrder).where(AutoOrder.deposit_address == address)
              self.execute_trade(auto, amount)
              continue
            except:
              pass
            try:
              [deposit_address] = session.query(DepositAddress).where(DepositAddress.address == address)
              try:
                [balance] = session.query(Balance).where((Balance.user == deposit_address.user) & (Balance.asset == asset))
              except:
                balance = Balance(user_id=deposit_address.user_id, asset_id=asset.id, amount=0)
                session.add(balance)
              balance.amount += amount
              session.commit()
            except:
              pass
          asset.height += 1
          session.commit()
        sleep(0.1 if self.rapid_update else 1)

  def execute_trade(auto, amount):
    foundStoppingPoint = False
    withdrawal_amount = 0
    with Session(self.engine) as session:
      session.begin_nested()
      session.execute('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;')
      while not foundStoppingPoint:
        orders = session.query(Order).where(
            Order.order_type == OrderType.BUY if order_type == OrderType.SELL else OrderType.SELL
          ).order_by(
            Order.price.desc() if order_type == OrderType.SELL else Order.price.asc(),
            Order.id.asc()
          ).limit(1000).all()
        if orders == []:
          foundStoppingPoint = True
        for order in orders:
          trade_amount = min(amount, order.amount - order.executed)
          session.add(Trade(user=order.user, order_type=OrderType.BUY, amount=trade_amount, price=order.price))
          matching_user_currency_balance = self.get_balance(session, order.user, asset)
          matching_user_currency_balance.amount += trade_amount
          withdrawal_amount += round_to_18_decimal_places(trade_amount * order.price)
          order.executed += trade_amount
          amount -= trade_amount
          if order.executed == order.amount:
            session.delete(order)
          else:
            foundStoppingPoint = True
            break
          if amount == 0:
            foundStoppingPoint = True
            break
      session.commit()
      session.commit()
      asset = assets['BTC' if order_type == Order.SELL else 'XMR']
      withdrawal_amount -= asset.withdrawal_fee()
      if withdrawal_amount > 0:
        try:
          asset.withdraw(auto.withdrawal_address, withdrawal_amount)
        except:
          pass
      if amount > 0:
        try:
          other_asset.withdraw(auto.refund_address, amount)
        except:
          pass

blockchain_monitor = BlockchainMonitor()

if __name__ == '__main__':
  blockchain_monitor.start(DB)
