#coding: utf-8
from proxies import ObjectWrapper
from collections.abc import MutableSequence, MutableMapping, MutableSet
from types import SimpleNamespace
import copy
import itertools
import uuid
import dictdiffer
import pprint


class TrackerWrapper(ObjectWrapper):
  
  _tracker = None
  
  def __init__(self, obj, name = 'root', path = None, handler = None, file=None, callback=None):
    ObjectWrapper.__init__(self, obj)
    
    handler = handler if handler else Tracker(self, name, file, callback)
    path = path if path else []
    object.__setattr__(self, '_tracker', SimpleNamespace(handler=handler, path=path))
      
  def __deepcopy__(self, memo):
    return copy.deepcopy(self.__subject__, memo)
    
  def __enter__(self):
    self._tracker.handler.save_changes = False
    
  def __exit__(self, *exc):
    self._tracker.handler.save()
    self._tracker.handler.save_changes = True
    
    
class DictWrapper(TrackerWrapper):
  """ Tracked dicts support attribute-like access
  to items, if the item keys are valid attribute names.
  
  >>> dct = track({'a': 1}, callback=catcher.cb)
  >>> dct.a
  1
  >>> dct.b = 2
  >>> catcher.target.b
  2
  >>> del dct.b
  """
  def __getattr__(self, key):
    if key in self:
      return self[key]
    if hasattr(self, '__subject__'):
      return getattr(self.__subject__, key)
    raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, key))
    
  def __setattr__(self, key, value):
    if hasattr(self, key):
      object.__setattr__(self, key, value) #key in self:
    else:
      self[key] = value
      
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
  >>> tracked_object = track(custom_object, callback=catcher.cb)
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

class Persistence():
  pass

class File(Persistence):
  """ Basic file-based persistence providing several serialization format options. """
  (PICKLE, YAML, JSON) = ('pickle', 'yaml', 'json')
  default_format = YAML
  """ Class default serialization format. """
  
  def __init__(self, filename, format=None, in_memory=False):
    self.format = format if format else self.default_format
    self.filename = filename + '.' + self.format
    self.in_memory = io.StringIO() if in_memory else None
    
    import importlib
    self.serializer = importlib.import_module(self.format)
    
  def load(self):
    try:
      if self.in_memory:
        return self.serializer.load(self.in_memory)
      else:
        with open(self.filename) as fp:
          return self.serializer.load(fp)
    except (EOFError, FileNotFoundError):
      return {}
    
  def dump(self, to_save):
    with open(self.filename, 'w') as fp:
      self.serializer.dump(to_save, fp)
      

class Tracker(object):
  
  persistence_default = File
  
  def __init__(self, root, name, persist, callback):
    self.root = root
    self.name = name
    self.callback = callback
    self.persistence = None
    if isinstance(persist, Persistence):
      self.persistence = persist(name)
    elif isinstance(self.persistence_default, Persistence):
      self.persistence = self.persistence_default(name)
    
    self.change_paths = ChangePathItem()
    self.save_changes = True
 
  def on_change(self, target, func_name, *args, **kwargs):
    if self.callback:
      change_data = SimpleNamespace(
        name=self.name,
        root=self.root,
        path=target._tracker.path, 
        target=target,func_name=func_name, 
        args=args, kwargs=kwargs)
      self.callback(change_data)
    #print(func_name, args)
    self.make_updates(target)
    self.record_change_footprint(target._tracker.path)
    if self.save_changes: self.save()
    
  def save(self):
    pass
    
  def make_updates(self, node):
    """ Checks to see if some of the changed node's contents now need to be tracked.
    """
    
    to_upgrade = []
    for key, value in self.get_iterable(node):
      if self.should_upgrade(value):
        to_upgrade.append((key, value))
      else:
        if istracked(value):
          value._tracker.path = node._tracker.path + [key]
    for key, value in to_upgrade:
      self.set_value(node.__subject__, key, value, track(value, None, node._tracker.path + [key], self))
      
  def should_upgrade(self, contained):
    if istracked(contained):
      return False

    for abc in trackable_types.keys():
      if isinstance(contained, abc):
        return True
    if hasattr(contained, '__dict__'):
      return True
    if hasattr(contained, '__hash__'):
      return False

    raise TypeError('Not a trackable or hashable type: ' + str(contained))
      
  def get_iterable(self, obj):
    """ Returns a (key, value) iterator regardless of object type. """
    if isinstance(obj, MutableSequence):
      return list(enumerate(obj))
    elif isinstance(obj, MutableMapping):
      return list(obj.items())
    elif isinstance(obj, MutableSet):
      return [(value, value) for value in obj]
    elif hasattr(obj, '__dict__'):
      return list(obj.__dict__.items())
    else:
      raise TypeError('Cannot return an iterator for type ' + str(type(obj)))
      
  def set_value(self, obj, key, old_value, new_value):
    if isinstance(obj, MutableSequence) or isinstance(obj, MutableMapping):
      obj[key] = new_value
    elif isinstance(obj, MutableSet):
      obj.remove(old_value)
      obj.add(new_value)
    elif hasattr(obj, '__dict__'):
      object.setattr(obj, key, new_value)
    else:
      raise TypeError('Cannot set value for type ' + str(type(obj)))
      
  def get_value(self, obj, key):
    if isinstance(obj, MutableSet):
      return key
    elif isinstance(key, str) and hasattr(obj, key):
      return getattr(obj, key)
    else:
      return obj[key]
      
  def at(self, path):
    current = self.root
    for key in path:
      current = self.get_value(current, key)
    return current
      
  def record_change_footprint(self, change_path):
    change_id = str(uuid.uuid4())[-12:]
    current = self.change_paths
    for node in change_path:
      current.change_id = change_id
      current = current.setdefault(node, ChangePathItem())
    current.change_id = change_id
    current.end_id = change_id
    current.clear() # Any older, more detailed changes are no longer interesting

  def copy(self):
    """ Returns a deep copy of the handler but not of the handled. """
    root = self.root
    self.root = None
    new_me = copy.deepcopy(self)
    self.root = root
    return new_me


class TrackerData():
  def __init__(self, handler, path):
    self.handler = handler
    self.path = path


class ChangePathItem(dict):
  """ Class to enable adding a change ID to change path items. """
  

def track(obj, name='default', path=None, tracker=None, persist=None, callback=None):
  """ Main function for tracking changes to structures. 
  
  Give it a structure consisting of dicts, lists, sets and contained objects, and
  it returns an object that looks much the same but tracks changes.
  
  Parameters:
  
  * `obj`: The data structure to track.
  * `name`: Name is used for persistence, e.g. as the file name. It is also included in change notifications.
  * `path`: Optional - Path prefix as a list of segments.
  * `tracker`: Optional - Pre-existing handler.
  * `persist`: Optional - Overrides class default persistence setting as defined by the `Tracker` class `default_persistence` attribute.
  * `callback`: Optional - Function that is called every time the tracked structure is changed.
  """
  tracked = None

  if istracked(obj):
    return obj

  for abc in trackable_types:
    if isinstance(obj, abc):
      tracked = trackable_types[abc](obj, name, path, tracker, persist, callback)
      
  if not tracked and hasattr(obj, '__dict__'):
    tracked = CustomWrapper(obj, name, path, tracker, persist, callback)
    
  if tracked:
    tracked._tracker.handler.make_updates(tracked)
    return tracked
    
  if hasattr(obj, '__hash__'):
    return obj
  raise TypeError('Not a trackable or hashable type: ' + str(obj))

def istracked(obj):
  return issubclass(type(obj), TrackerWrapper)

def deepcopy_tracked(obj):
  if not istracked(obj):
    raise TypeError('Cannot copy a non-tracked type: ' + str(type(obj)))    
  content = copy.deepcopy(obj)
  return _track_and_copy_meta(content, obj)
  
def _track_and_copy_meta(content, source_tracker):
  old_handler = source_tracker._tracker.handler
  tracked = track(content, old_handler.name)
  new_handler = tracked._tracker.handler
  new_handler.change_paths = copy.deepcopy(old_handler.change_paths)
  new_handler.callback = old_handler.callback
  return tracked

def diff_paths(earlier_version, later_version=None):
  if later_version is not None:
    earlier_version = earlier_version._tracker.handler.change_paths
    later_version = later_version._tracker.handler.change_paths
  else:
    earlier_version = ChangePathItem()
    later_version = earlier_version._tracker.handler.change_paths
  paths = []
  def get_paths(earlier, later, path):
    if earlier is not None and later.change_id == earlier.change_id:
      return
    if hasattr(later, 'end_id'):
      if not hasattr(earlier, 'end_id') or later.end_id != earlier.end_id:
        paths.append(path)
        return
    for key in later:
      new_earlier = earlier
      if new_earlier is not None:
        new_earlier = earlier.get(key, None)
      get_paths(new_earlier, later[key], path + [key])
  get_paths(earlier_version, later_version, [])
  return paths
  
def diff(earlier_version, later_version):
  paths = diff_paths(earlier_version, later_version)
  results = []
  for path in paths:
    earlier = earlier_version._tracker.handler.at(path)
    later = later_version._tracker.handler.at(path)
    results.append(dictdiffer.diff(earlier, later, node=path))
  return itertools.chain(*results)
  
def patch(changes, target, in_place=False):
  if not istracked(target):
    raise TypeError('This method is intended to patch a tracked type, not ' + str(type(obj)))
  if not in_place:
    target = deepcopy_tracked(target)  
  dictdiffer.patch(changes, target, in_place=True)
  return target
  
def revert(changes, target, in_place=False):
  if not istracked(target):
    raise TypeError('This method is intended to revert a tracked type, not ' + str(type(obj)))
  if not in_place:
    target = deepcopy_tracked(target)  
  dictdiffer.revert(changes, target, in_place=True)
  return target

if __name__ == '__main__':
  
  class TestCatcher():
    change = 'No change'
    def cb(self, change):
      for key in change.__dict__:
        self.__dict__[key] = change.__dict__[key]
  
  import doctest
  catcher = TestCatcher()
  doctest.testfile('README.md', extraglobs={'catcher': catcher})
  doctest.testmod(extraglobs={'catcher': catcher})
  
  l = [0, 2]
  m = track(l)
  with m:
    m[0] = { 'a': {'b': {'c', 'd'}}}
    m.append(3)
    m.append({4: 5})
    m[3][6] = 7
  assert m._tracker.handler.change_paths == {3: {}}
  
  back_to_l = copy.deepcopy(m)
  assert type(back_to_l[3]) == dict
  
  n = deepcopy_tracked(m)
  assert type(n[3]) == DictWrapper
  
  n[3][6] = { 7: 8 }
  n[3][6][7] = 9
  
  assert n._tracker.handler.change_paths == {3: {6: {}}}
  
  assert diff_paths(m, n) == [[3]]
  
  o = deepcopy_tracked(n)

  o[0]['a']['b'].add('e')
  
  d = diff(m, o)
  
  res = patch(d, m)
  
  assert o == res
  assert type(res) == type(m)
  
  f = File('testing.yaml')
  #print(f.load())
  f.dump(['a', 'b'])
  #print(f.load())
  
  g = { 'a': SimpleNamespace(b=1)}
  catcher = TestCatcher()
  h = track(g, callback=catcher.cb)
  h.a.b = 'new value'
  assert catcher.target.b == 'new value'
