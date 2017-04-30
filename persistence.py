import yaml
import dbm
import json
import importlib

from util import *

class Persistence():
  
  def load(self):
    """Load whole structure from persistence provider."""
    
  def load_specific(self, key):
    """Load a specific part of the structure, indicated by key."""
    
  def change_advisory(self, change):
    """Information about a change."""
    
  def dump(self, to_save, initial=False):
    """Persist the given structure.
    Initial save may be different in some cases."""
    

class AbstractFile(Persistence):
  
  file_format = 'abstract'
  
  def __init__(self, filename, testing=False):
    self.format = format if format else self.default_format
    self.filename = filename + '.' + self.file_format
    self.testing = testing
    if testing:
      #import tempfile
      self.testing = io.StringIO()#tempfile.TemporaryFile()
    
  def load(self):
    try:
      if self.testing:
        self.testing.seek(0)
        return self.loader(self.testing)
      else:
        with open(self.filename) as fp:
          return self.loader(fp)
    except (EOFError, FileNotFoundError):
      return None
      
  def load_specific(self, key):
    """ For file-based persistence, key is ignored,
    thus in effect identical to calling load().
    """
    return self.load()
    
  def dump(self, to_save, initial=False):
    if self.testing:
      self.testing = io.StringIO()
      self.dumper(to_save, self.testing)
    else:
      with open(self.filename, 'w') as fp:
        self.dumper(to_save, fp)


class SafeYamlFile(AbstractFile):
  
  file_format = 'yaml'
      
  def loader(self, fp):
    import yaml
    return yaml.safe_load(fp)
      
  def dumper(self, to_save, fp):
    import yaml
    yaml.dump(to_save, fp, default_flow_style=False, Dumper=TrackerSafeDumper)
  
class TrackerSafeDumper(yaml.SafeDumper):
  def represent_data(self, data):
    if hasattr(data, '__subject__'):
      data = data.__subject__
    return super().represent_data(data)


class JsonDBM(Persistence):
  
  def __init__(self, filename):
    self.filename = filename + '.dbm'
    self.db = dbm.open(self.filename, 'n')
    self.changed_keys = self.deleted_keys = set()
  
  def __del__(self):
    self.db.close()
  
  def load(self):
    try:
      if len(self.db) == 0:
        return None
      return_value = {}
      for key in self.db:
        eprint(key)
        return_value[key.decode()] = LazyLoadMarker()
      return return_value
    except (EOFError, FileNotFoundError):
      return None
    
  def load_specific(self, key):
    return json.loads(self.db[key].decode())
    
  def change_advisory(self, change):
    assert hasattr(change.root, '__getitem__')
    if len(change.path) == 0:
      if change.func_name == '__setitem__':
        self.changed_keys.add(change.args[0])
      if change.func_name == '__delitem__':
        self.deleted_keys.add(change.args[0])
    else:
      self.changed_keys.add(change.path[0])
    
  def dump(self, to_save, initial=False):
    assert hasattr(to_save, '__getitem__')
    if initial:
      self.changed_keys = (key for key in to_save)       
    for key in self.changed_keys:
      self.db[key] = json.dumps(to_save[key])
    self.changed_keys = set()
    for key in self.deleted_keys:
      del self.db[key]
    self.deleted_keys = set()
    
