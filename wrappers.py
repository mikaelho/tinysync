#coding: utf-8

from proxies import ObjectWrapper
from collections.abc import MutableSequence, MutableMapping, MutableSet
from types import SimpleNamespace

from util import *
  

class TrackerWrapper(ObjectWrapper):
  
  _tracker = None
  
  def __init__(self, obj, path, handler):
    ObjectWrapper.__init__(self, obj)
    
    #handler = handler if handler else Handler(self, name, file, callback)
    #path = path if path else []
    object.__setattr__(self, '_tracker', SimpleNamespace(handler=handler, path=path))
      
  def __deepcopy__(self, memo):
    return copy.deepcopy(self.__subject__, memo)
    
  def __enter__(self):
    """ Tracked objects are also context managers,
    and can be used to manage performance and transactionality.
    
    All changes are persisted only on exiting the
    context manager: 
    
    >>> dct = {'a': 1}
    >>> test = SafeYamlFile('test', testing=True)
    >>> tracked_dct = track(dct, persist=test)
    >>> initial_len = len(test.testing.getvalue())
    >>> def unchanged():
    ...   return len(test.testing.getvalue()) == initial_len
    >>>
    >>> with tracked_dct:
    ...   tracked_dct['b'] = 2
    ...   assert unchanged()
    >>> assert not unchanged()
    """
    self._tracker.handler.save_changes = False
    
  def __exit__(self, *exc):
    self._tracker.handler.save()
    self._tracker.handler.save_changes = True
  
  def __repr__(self):
    return self.__subject__.__repr__()
    
class DictWrapper(TrackerWrapper):
  """ Tracked dicts support attribute-like access
  to items, if the item keys are valid attribute names.
  
  >>> dct = track({'a': 1, 'b': {'c': 2}}, persist=False, callback=catcher.cb)
  >>> dct.a
  1
  >>> dct.b.c
  2
  >>> dct.b.c = 3
  >>> dct['b']['c']
  3
  >>> catcher.target.c
  3
  >>> del dct.b
  """
  
  def __getitem__(self, key):
    value = self.__subject__[key]
    if isinstance(value, LazyLoadMarker):
      value = self._tracker.handler.load(key, self._tracker.path)
      self.__subject__[key] = value
    return value
  
  def __getattr__(self, key):
    if key in self:
      return self[key]
    if hasattr(self, '__subject__'):
      return getattr(self.__subject__, key)
    raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, key))
    
  def __setattr__(self, key, value):
    if key in self:
      self[key] = value
    else:
      object.__setattr__(self, key, value)
      
  def __delattr__(self, key):
    if key in self:
      del self[key]
      return
    if hasattr(self, '__subject__'):
       delattr(self.__subject__, key)
       return
    raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, key))
    
    
class ListWrapper(TrackerWrapper): pass


class SetWrapper(TrackerWrapper): pass


class CustomWrapper(TrackerWrapper):
  """ If an object has a __dict__ attribute,
  we track attribute changes.
  
  >>> custom_object = SimpleNamespace(a=1)
  >>> tracked_object = track(custom_object, persist=False, callback=catcher.cb)
  >>> tracked_object.a = 'new value'
  >>> catcher.target.a
  'new value'
  """

trackable_types = {
  MutableSequence: ListWrapper,
  MutableMapping: DictWrapper,
  MutableSet: SetWrapper
}

mutating_methods = {
  CustomWrapper: [ '__setattr__'],
  DictWrapper: 
    ['__setitem__', '__delitem__', 'pop', 'popitem', 'clear', 'update', 'setdefault'],
  ListWrapper: 
    ['__setitem__', '__delitem__', 'insert', 'append', 'reverse', 'extend', 'pop', 'remove', 'clear', '__iadd__'],
  SetWrapper: 
    ['add', 'discard', 'clear', 'pop', 'remove', '__ior__', '__iand__', '__ixor__', '__isub__']
}

# Add tracking wrappers to all mutating functions
for wrapper_type in mutating_methods:
  for func_name in mutating_methods[wrapper_type]:
    def func(self, *args, tracker_function_name=func_name, **kwargs):
      return_value = getattr(self.__subject__, tracker_function_name)(*args, **kwargs)
      self._tracker.handler.on_change(self, tracker_function_name, *args, **kwargs)
      return return_value
    setattr(wrapper_type, func_name, func)
    getattr(wrapper_type, func_name).__name__ = func_name

if __name__ == '__main__':
  pass
