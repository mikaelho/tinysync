# coding: utf-8

#from tinydb import Query
import dictdiffer
import json
import copy
import hashlib
import uuid

class Revision(dict):
  """Helper class that represents a CouchDB-like combination of a version number and a checksum of a dict"""
  def __init__(self, *args):
    if len(args) == 0:
      self.version = 0
      self.checksum = self._checksum({})
    elif len(args) == 1:
      super(Revision, self).__init__(*args)
    elif len(args) == 2:
      self.version = args[0]
      self.checksum = self._checksum(args[1])
  @property
  def version(self):
    return self['version']
  @version.setter
  def version(self, value):
    self['version'] = value
  @property
  def checksum(self):
    return self['checksum']
  @checksum.setter
  def checksum(self, value):
    self['checksum'] = value 
  def initialize_for(self, content):
    self.version = 0
    self.checksum = self._checksum(content)
  def update_for(self, content):
    self.version += 1
    self.checksum = self._checksum(content)  
  def _checksum(self, value):
    string_data = json.dumps(value, sort_keys=True)
    return hashlib.md5(string_data).hexdigest()
  def __str__(self):
    return str(self.version) + '-' + self.checksum

def set_defaults(state):
  defaults = [
    ('data', {}),
    ('shadow', {}),
    ('backup', {}),
    ('local_version', Revision(0, {})),
    ('remote_version', Revision(0, {})),
    ('backup_version', Revision(0, {})),
    ('edits', {})
  ]
  for value in defaults:
    if not hasattr(state, value[0]):
      setattr(state, value[0], value[1])
    #state.setdefault(value[0], value[1])

def sync_changes(state, server = False):
  """
  Args:
    state: State object
    server: True if we are running on server
  """
  #2: Client diff
  latest_changes = diff(state.data, state.shadow)
  if len(latest_changes) > 0:
    state.edits[state.local_version.version] = latest_changes
    message = {
      edits: state.edits,
      sender_last_version: state.local_version,
      receiver_expected_version: state.remote_version
    }
    #3 Shadow update
    state.shadow = copy.deepcopy(state.data)
    state.local_version.update_for(state.data)
    return message
  else: return None
    
def process_request(message, state, server = False, strict = True, server_wins_conflicts = True):
  """
  Args:
    server: True if function is called at server
    strict: True if we should check for conflicts between client and server changes
    server_wins_conflicts: True if server version is retained in case of a conflict
  """
  change_indexes = [ i for index in sorted(message.edits.keys()) if index >= state.remote_version.version ]
  # Normal operation
  if len(change_indexes) > 0 and message.receiver_expected_version == state.local_version:
    #5 Patch shadow
    delta = diff(state.shadow, state.data)
    for index in change_indexes:
      patch(message.data[index], state.shadow, copy_original = False)
    #6 Update shadow version
    state.remote_version.update_for(state.shadow)
    #7 Update backup shadow
    state.backup = copy.deepcopy(state.shadow)
    state.backup_version = state.local_version
    #8 Patch data
    no_conflict = True
    one_way = copy.deepcopy(state.data)
    for index in change_indexes:
      patch(message.data[index], one_way, copy_original = False)
    if strict: # check for conflict
      latest_changes = diff(state.backup, state.data)
      other_way = patch(latest_changes, state.shadow)    
      no_conflict = one_way == other_way
    if no_conflict:
      state.data = one_way
    # Remove local edits seen by the other end
    for index in sorted(state.edits.keys()):
      if index <= message.receiver_expected_version:
        del state.edits[index]
  elif message.receiver_expected_version == state.backup_version:
    # Previous update did not reach the other end
    pass

def p(dict_obj):
  print json.dumps(dict_obj, indent=2)

def diff(first, second):
  return copy.deepcopy(list(dictdiffer.diff(first, second)))
  
def patch(change, target, copy_original = True):
  patched = dictdiffer.patch(change, target, copy_original)
  return patched

