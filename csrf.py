from flask import request, abort, make_response
from exchange import random_128_bit_string

def csrf(app, exchange):
  def get(path):
    def decorator(f):
      @app.route(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        csrf = random_128_bit_string()
        response = make_response(f(f'<input type="hidden" name="csrf" value="{csrf}"/>', exchange.check_user(request.cookies.get('api_key')), *args, **kwargs))
        response.set_cookie('csrf', csrf)
        return response
      return wrapper
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        if request.form['csrf'] != request.cookies.get('csrf'):
          abort(403)
        csrf = random_128_bit_string()
        response = make_response(f(f'<input type="hidden" name="csrf" value="{csrf}"/>', exchange.check_user(request.cookies.get('api_key')), *args, **kwargs))
        response.set_cookie('csrf', csrf)
        return response
      return wrapper
    return decorator

  return get, post
