# coding: utf-8

import json
import random

import tinydb
#import json_delta
#import dictdiffer
import tinysync.logic

class TinySyncServer():

  def __init__(self, filename):
    self.db = tinydb.TinyDB(filename)

  def process_local(self, version, diffs):
    pass

class TinySyncDB(tinydb.TinyDB):

  def __init__(self, *args, **kwargs):
    #tinydb.TinyDB.table_class = SyncClientTable
    #self._storage = tinydb.storages.MemoryStorage()
    self.table_class = SyncClientTable
    sync_logic_class = kwargs.pop('sync_logic', tinysync.logic.Client)
    server = kwargs.pop('server', None)
    super(TinySyncDB, self).__init__(*args, storage = tinydb.storages.MemoryStorage, **kwargs)
    #self.table_class = SyncClientTable
    self.table_class = tinydb.database.Table
    local_conf = self.table('_conf')
    self.set_logic(sync_logic_class, local_conf, server)

class SyncClientTable(tinydb.database.Table):
  '''
  A TinyDB Table that supports syncing changes to a server.
  '''

  def __init__(self, *args, **kwargs):
    
    super(SyncClientTable, self).__init__(*args, **kwargs)

  def set_logic(self, sync_logic_class, table, server):
    self.logic = sync_logic_class(table, server_connectivity = server)

  def sync(self):
    current_value = self._read().copy()
    new_value = self.logic.sync(current_value)
    self._write(new_value)

  def _get_next_id(self):
    max_value = 2147483647 # max positive 32-bit int
    retries = 0
    max_retries = 10
    data = self._read()
    while retries < max_retries:
      new_id = random.randrange(max_value)
      if new_id not in data:
        return new_id
      retries += 1
    print 'id range saturated'
    return None

  def insert(self, element):
    # See Table.insert

    # Insert element
    eid = super(SyncClientTable, self).insert(element)

    self.logic.dirty.add(eid)

    return eid

  def insert_multiple(self, elements):
    # See Table.insert_multiple

    # We have to call `SmartCacheTable.insert` here because
    # `Table.insert_multiple` doesn't call `insert()` for every element
    return [self.insert(element) for element in elements]

  def update(self, fields, cond=None, eids=None):
    # See Table.update

    if callable(fields):
      _update = lambda data, eid: fields(data[eid])
    else:
      _update = lambda data, eid: data[eid].update(fields)

    def process(data, eid):
      # Update element
      _update(data, eid)
      self.logic.dirty.add(eid)

    self.process_elements(process, cond, eids)

  def remove(self, cond=None, eids=None):
    # See Table.remove

    def process(data, eid):
      # Remove element
      data.pop(eid)
      self.logic.dirty.add(eid)

    self.process_elements(process, cond, eids)

  def purge(self):
    # See Table.purge
    data = self._read()
    for eid in data:
      self.logic.dirty.add(eid)
    super(SyncClientTable, self).purge()
    
#class MemoryStorage(tinydb.Storage):

class JSONOwnerStorage(tinydb.Storage):
  """
  Store the data in a JSON file. Assumes full ownership of the underlying file, i.e. no need to keep loading from file on every read.

  Note that the data is passed by reference.
  """

  def __init__(self, path, **kwargs):
    """
    Create a new instance.

    Also creates the storage file, if it doesn't exist.

    :param path: Where to store the JSON data.
    :type path: str
    """

    super(JSONOwnerStorage, self).__init__()
    tinydb.storages.touch(path)  # Create file if it does not exist
    self.kwargs = kwargs
    self._handle = open(path, 'r+')
    self.data = None

  def close(self):
    self._handle.close()

  def read(self):
    if self.data is not None:
      return self.data

    # Get the file size
    self._handle.seek(0, 2)
    size = self._handle.tell()

    if not size:
      self.data = {}
      self.write(self.data)
    else:
      self._handle.seek(0)
      self.data = json.load(self._handle)
    return self.data

  def write(self, data):
    self._handle.seek(0)
    serialized = json.dumps(data, **self.kwargs)
    self._handle.write(serialized)
    self._handle.flush()
    self._handle.truncate()

