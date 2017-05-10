#coding: utf-8

from collections.abc import MutableSequence, MutableMapping, MutableSet
from types import SimpleNamespace
import copy
import itertools
import uuid
import dictdiffer
import pprint
import sys, io
import importlib
import threading

from wrappers import *
from persistence import *
from util import *

    
class Handler(object):
  
  persistence_default = SafeYamlFile
  
  def __init__(self, subject, name, persist, change_callback, conflict_callback, path_prefix):
        
    self.lock = threading.RLock()

    self.name = name
    self.change_callback = change_callback
    self.conflict_callback = conflict_callback
    self.persist = persist
    self.path_prefix = path_prefix
    self.change_paths = ChangePathItem()
    self.save_changes = True
    self.root = self.start_to_track(subject, path_prefix)
 
  def on_change(self, target, func_name, *args, **kwargs):
    change_data = SimpleNamespace(
      name=self.name,
      root=self.root,
      path=target._tracker.path, 
      target=target,func_name=func_name, 
      args=args, kwargs=kwargs
    )
      
    self.make_updates(target)
    self.record_change_footprint(target._tracker.path)
    
    if self.change_callback:
      self.change_callback(change_data)
    
    if self.persist is not None:
      self.persist.change_advisory(change_data)
      if self.save_changes: 
        self.save()
        
  def save(self):
    if self.persist is not None:
      self.persist.dump(self.root, self, self.conflict_callback)
      
  def load(self, key, path):
    value = self.persist.load_specific(key)
    tracked_value = self.start_to_track(value, path + [key])
    return tracked_value
    
  def start_to_track(self, target, path):
    if istracked(target) or isinstance(target, LazyLoadMarker):
      return target
    
    tracked = None
    
    for abc in trackable_types:
      if isinstance(target, abc):
        tracked = trackable_types[abc](target, path, self)
        
    if tracked is None and hasattr(target, '__dict__'):
      tracked = CustomWrapper(target, path, self)
      
    if tracked is not None:
      self.make_updates(tracked)
      return tracked
      
    raise TypeError("'%s' does not have a trackable type: %s" % (target, type(target)))
    
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
      self.set_value(node.__subject__, key, value, self.start_to_track(value, node._tracker.path + [key]))
      
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
    
  def set(self, path, value):
    assert isinstance(path, list)
    if len(path) == 0:
      raise ValueError('Empty path, cannot set root')
    current = self.root
    for key in path[:-1]:
      current = self.get_value(current, key)
    key = path[-1]
    old_value = self.get_value(current, key)
    self.set_value(current, path[-1], old_value, value)
      
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
  

#def track(target, name='default', path=None, tracker=None, persist=None, callback=None):
  
def track(target, name='default', persist=None, change_callback=None, conflict_callback=None, path_prefix=None):
  """ Main function to start tracking changes to structures. 
  
  Give it a structure consisting of dicts, lists, sets and contained objects, and
  it returns an object that looks much the same but tracks changes.
  
  Parameters:
  
  * `target`: The data structure to track.
  * `name`: Name is used for persistence, e.g. as the file name. It is also included in change notifications.
  * `persist`: Optional - Overrides class default persistence setting as defined by the `Tracker` class `default_persistence` attribute.
  * `change_callback`: Optional - Function that is called every time the tracked structure is changed.
  * `conflict_callback`: Optional - Function called to resolve conflicts between the latest changes and the persisted values.
  * `path_prefix`: Optional - Path prefix as a list of segments.
  """
  tracked = None
  persistence = None
  path_prefix = path_prefix if path_prefix is not None else []

  if istracked(target):
    return target
    
  if persist is not False:
    if persist is not None and persist is not True:
      if isinstance(persist, Persistence):
        persistence = persist
      elif issubclass(persist, Persistence):
        persistence = persist(name)
    elif Handler.persistence_default is not None: #issubclass(Handler.persistence_default, Persistence):
      persistence = Handler.persistence_default(name)

  initial = True
  if persistence is not None:
    loaded_target = persistence.load()
    if loaded_target is not None:
      target = loaded_target
      initial = False
  
  handler = Handler(target, name, persistence, change_callback, conflict_callback, path_prefix)
  
  if persistence is not None:
    persistence.dump(handler.root, initial=initial)
    
  return handler.root

def configure(tracked_object, **kwargs):
  if not istracked(tracked_object):
    raise TypeError('Cannot configure a non-tracked object of type %s' % type(tracked_object))
  handler = tracked_object._tracker.handler
  for key in kwargs:
    if hasattr(handler, key):
      setattr(handler, key, kwargs[key])
    else:
      raise AttributeError('%s is not an available option to set' % key)

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
  extraglobs = {
    'catcher': TestCatcher()
  }
  
  #Handler.persistence_default = None
  
  doctest.testmod(extraglobs=extraglobs)
  extraglobs.update(importlib.import_module('tracker').__dict__)
  extraglobs.update(track({}, 'couchdb-conf'))
  
  doctest.testfile('README.md', extraglobs=extraglobs)
  
  # Remove temporary example files
  import os, glob
  os.remove('example-config.yaml')
  for f in glob.glob("example-dbm.dbm.*"):
    os.remove(f)
  
  """
  l = [0, 2]
  m = track(l, persist=False)
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
  
  g = { 'a': SimpleNamespace(b=1)}
  catcher = TestCatcher()
  h = track(g, callback=catcher.cb)
  h.a.b = 'new value'
  assert catcher.target.b == 'new value'
  
  h.a._tracker.foobar = 'blaa'
  """
