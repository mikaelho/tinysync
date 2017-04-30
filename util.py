#coding: utf-8

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)


class LazyLoadMarker():
  """Marker object indicating content that has not been loaded yet. DictWrapper __getitem__ method loads the content when this object is encountered."""


if __name__ == '__main__':
  pass
