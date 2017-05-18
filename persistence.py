import json
import importlib
from collections.abc import MutableMapping
from contextlib import contextmanager
from copy import deepcopy

from util import *

@contextmanager
def do_not_track(obj):
  previous_value = obj._tracker.handler.track
  obj._tracker.handler.track = False
  yield
  obj._tracker.handler.track = previous_value
  
@contextmanager
def do_not_save(obj):
  previous_value = obj._tracker.handler.save_changes
  obj._tracker.handler.save_changes = False
  yield
  obj._tracker.handler.save_changes = previous_value

class Persistence():
  
  def load(self):
    """Load whole structure from persistence provider."""
    
  def load_specific(self, key):
    """Load a specific part of the structure, indicated by key."""
    
  def change_advisory(self, change):
    """Information about a change."""
    
  def dump(to_save, handler, conflict_callback, initial=False):
    """Persist the given structure.
    Initial save may be different in some cases.
    
    Returns a list of conflicts from the persistence layer or None if no conflicts.
    Conflicts are reported as a list of (path, new value) tuples. """
    

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
    
  def dump(self, to_save, handler=None, conflict_callback=None, initial=False):
    if self.testing:
      self.testing = io.StringIO()
      self.dumper(to_save, self.testing)
    else:
      with open(self.filename, 'w') as fp:
        self.dumper(to_save, fp)


class SafeYamlFile(AbstractFile):
  
  file_format = 'yaml'
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    globals()['yaml'] = importlib.import_module('yaml')
      
  def loader(self, fp):
    return yaml.safe_load(fp)
      
  def dumper(self, to_save, fp):
    
    class TrackerSafeDumper(yaml.SafeDumper):
      def represent_data(self, data):
        if hasattr(data, '__subject__'):
          data = data.__subject__
        return super().represent_data(data)
    
    yaml.dump(to_save, fp, default_flow_style=False, Dumper=TrackerSafeDumper)


class LazyPersistence(Persistence):
  """Persistence options that assume that the
  structure starts with a dict, and separate parts of the structure can be updated and loaded by 
  key, instead of the whole structure.
  
  Subclass __init__ functions should set a self.db
  value to be used in the other operations.
  """
  
  def __init__(self):
    self.changed_keys = self.deleted_keys = set()
    
  def change_advisory(self, change):
    assert hasattr(change.root, '__getitem__')
    if len(change.path) == 0:
      if change.func_name == '__setitem__':
        self.changed_keys.add(change.args[0])
      if change.func_name == '__delitem__':
        self.deleted_keys.add(change.args[0])
    else:
      self.changed_keys.add(change.path[0])

class JsonDBM(LazyPersistence):
  
  def __init__(self, filename):
    super().__init__()
    globals()['dbm'] = importlib.import_module('dbm')
    self.filename = filename + '.dbm'
    self.db = dbm.open(self.filename, 'n')
  
  def __del__(self):
    self.db.close()
  
  def load(self):
    try:
      if len(self.db) == 0:
        return None
      return_value = {}
      for key in self.db:
        return_value[key.decode()] = LazyLoadMarker()
      return return_value
    except (EOFError, FileNotFoundError):
      return None
    
  def load_specific(self, key):
    return json.loads(self.db[key].decode())
    
  def dump(self, to_save, handler=None, conflict_callback=None, initial=False):
    assert hasattr(to_save, '__getitem__')
    if initial:
      self.changed_keys = (key for key in to_save)       
    for key in self.changed_keys:
      self.db[key] = json.dumps(to_save[key])
    self.changed_keys = set()
    for key in self.deleted_keys:
      del self.db[key]
    self.deleted_keys = set()
    
    
class CouchDB(LazyPersistence):
  """ Save structure to CouchDB, or a variant
  like Cloudant.
  Root must be a dict, likewise the elements 
  contained in the root dict, which are further 
  polluted by CouchDB `_id` and `_rev` elements
  (where _id == key in the root dict).
  """
  
  server_address = None
  
  def __init__(self, database_url):
    """ Initializes a CouchDB persistence provider, with the assumption that one provider corresponds to one CouchDB database and one Python data structure.
    
    Parameters:
      
      * `database` parameter is either:
        * a plain CouchDB database name
        * a url that starts  with 'http' and includes the database name, e.g.: https://username:password@accountname.server.net/database.
          
    If only the database name is defined, connection is made to the default 'localhost:5984' with no authentication. If only database name is defined and the class-level `url` attribute is also defined, the two are combined.
    """
    
    super().__init__()
    globals()['couchdb'] = importlib.import_module('couchdb')
    
    if not database_url.startswith('http') and self.server_address is not None:
      import urllib.parse
      database_url = urllib.parse.urljoin(self.server_address, database_url)
      
    self.name = database_url.split('/')[-1]
    server_url = database_url[:-len(self.name)]
    
    self.server = couchdb.Server(couchdb.client.DEFAULT_BASE_URL if server_url == '' else server_url)
      
    try:
      self.db = self.server[self.name]
    except couchdb.http.ResourceNotFound:
      self.db = self.server.create(self.name)
    
  def load(self):
    if len(self.db) == 0:
      return None
    return_value = {}
    for key in self.db:
      return_value[key] = LazyLoadMarker()
    return return_value
    
  def load_specific(self, key):
    return self.db[key]
    #del doc['_id']
    #self.revs[key] = doc['_rev']
    #del doc['_rev']
    #return doc
    
  def dump(self, to_save, handler=None, conflict_callback=None, initial=False):
    assert hasattr(to_save, '__getitem__')
    
    # Must not trigger new saves to remote
    with do_not_save(to_save):
      conflicts = []
      if initial:
        self.changed_keys = (key for key in to_save)       
      for key in self.changed_keys:
        doc = to_save[key]
        assert isinstance(doc, MutableMapping)
        with do_not_track(to_save):
          doc['_id'] = key
          try:
            (_, rev) = self.db.save(deepcopy(doc))
            doc['_rev'] = rev
          except couchdb.ResourceConflict:
            self.handle_conflict(to_save, key, doc, conflict_callback)
      self.changed_keys = set()
      for key in self.deleted_keys:
        doc = to_save[key]
        doc['_id'] = key
        try:
          self.db.delete(key)
        except couchdb.ResourceConflict:
          return self.add_to_conflicts(conflicts, key)
      self.deleted_keys = set()
    
  def handle_conflict(self, to_save, key, local_doc, conflict_callback):
    remote_doc = self.db[key]
    local_doc['_rev'] = remote_doc['_rev']
    if conflict_callback and conflict_callback([key], local_doc, remote_doc):
      # Local wins, may have been modified by the callback
      self.db.save(local_doc)
    else: # Remote wins
      to_save[key] = remote_doc
      
  def clean(self):
    """ Convenience function that deletes the underlying CouchDB database. """
    self.server.delete(self.name)
