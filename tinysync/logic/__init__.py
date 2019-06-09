# coding: utf-8

from tinydb import Query
import dictdiffer
#import json_delta
import json
import copy
import hashlib
import uuid

def p(dict_obj):
  print(json.dumps(dict_obj, indent=2))

def diff(first, second):
  return copy.deepcopy(list(dictdiffer.diff(first, second)))
  #return json_delta.diff(first, second, minimal = True, verbose = False)
  
def patch(change, target, copy_original = True):
  #prev_len = len(change)
  patched = dictdiffer.patch(change, target, copy_original)
  #assert len(change) == prev_len
  return patched
  #in_place = copy_original == False
  #return json_delta.patch(target, change, in_place = in_place)
  
def revert(change, target, copy_original = True):
  return dictdiffer.revert(change, target, copy_original)
  
def match(first, second):
  return first == second

class Client():
    
  def __init__(self, local_conf_db, server_connectivity = None):
    self.client_id = str(uuid.uuid4())
    self.db = local_conf_db
    self.dirty = set()
    self.working = set()
    self.prev_value = {}
    self.version = 0
    self.server_connectivity = server_connectivity if server_connectivity else ServerConnectivity()
    
    if not self.db.contains(Query().server_version.exists()):
      self.db.insert({
        'client_id': self.client_id,
        'server_version': 0,
        'dirty': [],
        'working': [],
        'changes': []
      })
    
  def sync(self, current_value):
    # Convert to plain dict
    #current_value = json.loads(json.dumps(current_value))
    #self.prev_value = dict(self.prev_value)
    
    #server_version = self.server_connectivity.server.version
    #if server_version > 0: server_last_change = self.server_connectivity.server.diffs[-1]
    
    version_diff = diff(self.prev_value, current_value)
    #assert match(patch(version_diff, self.prev_value), current_value), (patched, current_value)
    #print version_diff
    #print 'client before: ' + str(self.version)
    #backup = self.prev_value
    
    reply = self.server_connectivity.sync_up(self.version, version_diff, self.client_id, generate_checksum(self.prev_value))
    
    if reply['status'] == 'ok':
      print('ok ', end=' ')
      self.version = reply['version']
      self.prev_value = current_value
      #assert match(version_diff, self.server_connectivity.server.diffs[-1])
      #assert match(self.prev_value, self.server_connectivity.server.client_baselines[self.client_id])
      #assert server_version + 1 == self.server_connectivity.server.version
    
    elif reply['status'] == 'merged':
      print('merged ', end=' ')
      self.prev_value = patch(reply['diffs'], current_value)
      self.version = reply['version']
      #assert match(version_diff, self.server_connectivity.server.diffs[-1])
      #assert match(self.prev_value, self.server_connectivity.server.client_baselines[self.client_id])
      #assert server_version + 1 == self.server_connectivity.server.version
    
    elif reply['status'] == 'conflict':
      print('conflict ', end=' ')
      try:
        self.prev_value = patch(reply['diffs'], self.prev_value)
        self.version = reply['version']
      except Exception as e:
        print('Error patching client to match server')
        print('* previous client value:')
        p(self.prev_value)
        print('* diffs:')
        p(reply['diffs'])
        #self.server_connectivity.compare_diffs(reply['diffs'])
        raise e
      #assert not match(version_diff, self.server_connectivity.server.diffs[-1]),(diff(version_diff, self.server_connectivity.server.diffs[-1]),'client: ' + str(version_diff), 'server: '+ str(self.server_connectivity.server.diffs[-1]))
      #assert server_version == self.server_connectivity.server.version
      #if server_version > 0: assert match(server_last_change, self.server_connectivity.server.diffs[-1])
      #assert match(self.prev_value, self.server_connectivity.server.client_baselines[self.client_id])
        
    elif reply['status'] == 'misaligned':
      raise Exception('Version misalignment between client and server: ' + str(reply['message']))
    
    elif reply['status'] == 'error':
      raise Exception('Error: ' + str(reply['message']))
    
    else:
      raise Exception('Did not even get a proper error')
    #self.server_connectivity.check(self.prev_value)
    #print 'client after: ' + str(self.version)
    return copy.deepcopy(self.prev_value)

class ServerConnectivity():
  
  def __init__(self, server = None):
    self.server = server if server else Server()
    
  def sync_up(self, version, version_diff, client_id, checksum):
    return self.server.handler({
      'put': {
        'previous_version': version,
        'delta': version_diff,
        'client_id': client_id,
        'checksum': checksum
      }
    })

class Server():
  ''' Baseline server logic implementation. This memory-based base class is intended mainly for testing. '''
  
  def __init__(self):
    self.content = {}
    self.version = 0
    #self.diffs = []
    self.client_last_seen_content = {}
  
  '''
  @property
  def version(self):
    return len(self.diffs)
  '''
    
  def handler(self, client_input):
    ''' Handles a request from a client. '''
    reply = {}
    #print 'server before: ' + str(self.version)
    #try:
    if 'put' in client_input:
      reply = self.handle_request(client_input['put'])
    else:
      print('Unknown client request')
    #except Exception as e:
      #reply = {
       # 'status': 'error',
       # 'message': str(e)
      #}
    #print 'server after: ' + str(self.version)
    return reply
      
  def handle_request(self, request):
    #print 'Version: ' + str(request['previous_version'])
    #print 'Delta: ' + str(list(request['delta']))
    
    client_previous_version = int(request['previous_version'])
    if client_previous_version < 0 or client_previous_version > self.version:
      return {
        'status': 'error',
        'message': 'Version number out of range: ' + str(client_previous_version)
      }
    client_id = request['client_id']
    checksum = request['checksum']
    client_delta = copy.deepcopy(request['delta'])
    self.update_content()
    
    if client_previous_version == self.version:
      if not checksum == generate_checksum(self.content):
        return { 
          'status': 'misaligned',
          'message': 'Content checksums do not match for client ' + client_id
        }
      self.content = patch(client_delta, self.content)
      self.version += 1
      #self.diffs.append(client_delta)
      #if not len(self.diffs) == self.version:
          #raise Exception('Update - version mgmt broken, ' + str(len(self.diffs)) + ' <> ' + str(self.version))
      self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
      return { 'status': 'ok', 'version': self.version }
    
    elif client_previous_version < self.version:
      #last_diffs = copy.deepcopy(self.diffs[client_previous_version:])
      #assert len(last_diffs) == self.version - client_previous_version
      #p(self.last_diffs)
      baseline = self.client_last_seen_content.get(client_id, {})
      #last_diffs = diff(baseline, self.content)
      '''
      baseline = copy.deepcopy(self.content)
      try:
        for change in self.diffs[client_previous_version:][::-1]:
          baseline = revert(change, baseline, copy_original = False)
      #test_patch = dictdiffer.patch(collapsed_delta, request['current_value'])
      #try:
        #reversed_collapsed_delta = list(dictdiffer.swap(copy.deepcopy(collapsed_delta)[::-1]))
        #baseline = dictdiffer.revert(collapsed_delta, self.content)
      except Exception as e:
        print 'Baseline revert failed'
        #print '* reversed delta:'
        #p(reversed_collapsed_delta)
        print '* starting server content:'
        p(self.content)
        raise e
      '''
      if not checksum == generate_checksum(baseline):
        return { 
          'status': 'misaligned',
          'message': 'Baseline checksums do not match in merge for client ' + client_id
        }
      
      server_diff = diff(baseline, self.content)
      
      '''
      version_delta = list(dictdiffer.diff(baseline, request['current_value']))
      check_ok = len(version_delta) == 0
      if not check_ok:
        print 'pre-check NOT OK'
        print '* baseline: ' + str(baseline)
        print '* client: ' + str(request['current_value'])
        print '* delta: ' + str(version_delta)
        print '* server: ' + str(self.content)
        raise Exception('pre-check broken')
      '''
      
      build_up_ok = True
      try:

        one_way = patch(client_delta, baseline)
        one_way = patch(server_diff, one_way, copy_original = False)
        #for change in self.diffs[client_previous_version:]:
          #one_way = patch(change, one_way, copy_original = False)
          
        #other_way = copy.deepcopy(baseline)
        #for change in self.diffs[client_previous_version:]:
        other_way = patch(server_diff, baseline)
        other_way = patch(client_delta, other_way, copy_original = False)
        
      except Exception:
        build_up_ok = False

      if build_up_ok and match(one_way, other_way):
        self.version += 1
        #self.diffs.append(client_delta)
        self.content = other_way # patch(client_delta, self.content)
        self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
        
        return {
          'status': 'merged',
          'version': self.version,
          'diffs': server_diff
        }
      else:
        self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
        return {
          'status': 'conflict',
          'version': self.version,
          'diffs': server_diff
        }

  def update_content(self):
    pass
  
class FileBasedServer():
  pass
  
def generate_checksum(data):
  ''' Returns a hash of the JSON-serializable parameter '''
  string_data = json.dumps(data, sort_keys=True)
  return hashlib.md5(string_data.encode()).hexdigest()

