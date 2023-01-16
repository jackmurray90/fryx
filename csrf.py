from flask import request, abort, make_response, render_template, redirect
from exchange import random_128_bit_string

def csrf(app, exchange):
  def get(path):
    def decorator(f):
      @app.route(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        user = exchange.check_user(request.cookies.get('api_key'))
        api_key = user.api_key if user else ''
        csrf = f'<input type="hidden" name="csrf" value="{api_key}"/>'
        def rt(path, **kwargs):
          if 'message' not in kwargs:
            kwargs['message'] = request.cookies.get('message')
          response = make_response(render_template(path, csrf=csrf, user=user, **kwargs))
          response.set_cookie('message', '', expires=0)
          return response
        return f(rt, user, *args, **kwargs)
      return wrapper
    return decorator

  def post(path):
    def decorator(f):
      @app.post(path, endpoint=random_128_bit_string())
      def wrapper(*args, **kwargs):
        user = exchange.check_user(request.cookies.get('api_key'))
        if user and request.form['csrf'] != user.api_key:
          abort(403)
        def r(path, message=''):
          response = make_response(redirect(path))
          response.set_cookie('message', message)
          return response
        return f(r, user, *args, **kwargs)
      return wrapper
    return decorator

  return get, post
