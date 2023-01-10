from flask import request, abort
from db import RateLimit, User
from sqlalchemy.orm import Session
from time import time

def rate_limit(engine, ip=False):
  with Session(engine) as session:
    if ip:
      address = request.remote_addr
    else:
      if request.args['api_key'] == 'auto': abort(403)
      try:
        [user] = session.query(User).where(User.api_key == request.args['api_key'])
        address = request.args['api_key']
      except:
        abort(403)
    try:
      [rate_limit] = session.query(RateLimit).where(RateLimit.address == address)
    except:
      rate_limit = RateLimit(address=address, timestamps='')
      session.add(rate_limit)
      session.commit()
    timestamps = [float(t) for t in rate_limit.timestamps.split() if float(t) >= time()-1]
    if len(timestamps) > 50:
      abort(429)
    timestamps.append(time())
    rate_limit.timestamps = ' '.join([str(t) for t in timestamps])
    session.commit()
