from sqlalchemy.orm import Session
from assets import assets
from db import Asset, Balance, DepositAddress
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
        if asset.name != 'XMR' or not __name__ == '__main__':
          Thread(target=self.monitor_blockchain, args=(asset.name,)).start()

  def stop(self):
    self.running = False
    sleep(0.2 if self.rapid_update else 1.1)

  def monitor_blockchain(self, asset_name):
    with Session(self.engine) as session:
      [asset] = session.query(Asset).where(Asset.name == asset_name)
      while self.running:
        while asset.height < assets[asset.name].height():
          for address, amount in assets[asset.name].get_incoming_txs(asset.height):
            try:
              [deposit_address] = session.query(DepositAddress).where(DepositAddress.address == address)
            except:
              continue
            try:
              [balance] = session.query(Balance).where((Balance.user == deposit_address.user) & (Balance.asset == asset))
            except:
              balance = Balance(user=deposit_address.user, asset=asset, amount=0)
              session.add(balance)
              session.commit()
            balance.amount += amount
            session.commit()
          asset.height += 1
          session.commit()
        sleep(0.1 if self.rapid_update else 1)

blockchain_monitor = BlockchainMonitor()

if __name__ == '__main__':
  blockchain_monitor.start(DB)
