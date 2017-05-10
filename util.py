#coding: utf-8
from sys import stderr
from threading import Thread
from functools import wraps

def run_async(func):
  @wraps(func)
  def async_func(*args, **kwargs):
    func_hl = Thread(target = func, args = args, kwargs = kwargs)
    func_hl.start()
    return func_hl
  return async_func

def eprint(*args, **kwargs):
  print(*args, file=stderr, **kwargs)

class LazyLoadMarker():
  """Marker object indicating content that has not been loaded yet. DictWrapper __getitem__ method loads the content when this object is encountered."""

if __name__ == '__main__':
  pass
