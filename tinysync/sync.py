import copy
import dictdiffer

class Sync:
  
  def __init__(self, data_id, conduit, change_callback):
    self.data_id = data_id
    self.conduit = conduit
    self.change_callback = change_callback
    conduit.register_handler(self)
    self.dirty = set()
    self.working = set()
    self.prev_value = {}
    self.version = 0
   
  @staticmethod 
  def _generate_checksum(data):
    ''' Returns a hash of the JSON-serializable parameter '''
    string_data = json.dumps(data, sort_keys=True)
    return hashlib.md5(string_data.encode()).hexdigest()
    
  def update(self, current_value):
    version_diff = dictdiffer.diff(self.prev_value, current_value)
    checksum = self._generate_checksum(self.prev_value)
    message = {
      'put': {
        'previous_version': version,
        'delta': version_diff,
        'data_id': self.data_id,
        'checksum': checksum
      }
    }
    self.conduit.send_up(self, message)
    
  def remote_update(self, message):
    if 'put' in message:
      client_previous_version = int(message['previous_version'])
      if client_previous_version < 0 or client_previous_version > self.version:
        return {
          'status': 'error',
          'message': 'Version number out of range: ' + str(client_previous_version)
        }
      client_id = message['client_id']
      checksum = message['checksum']
      client_delta = copy.deepcopy(message['delta'])
      
      if client_previous_version == self.version:
        if not checksum == generate_checksum(self.content):
          return { 
            'status': 'misaligned',
            'message': 'Content checksums do not match for client ' + client_id
          }
        self.content = dictdiffer.patch(client_delta, self.content)
        self.version += 1
        self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
        return {
          'status': 'ok',
          'version': self.version,
          'baseline': client_previous_version }
      
      elif client_previous_version < self.version:
        baseline = self.client_last_seen_content.get(client_id, {})

        if not checksum == generate_checksum(baseline):
          return { 
            'status': 'misaligned',
            'message': 'Baseline checksums do not match in merge for client ' + client_id
          }
        
        server_diff = diff(baseline, self.content)
        
        build_up_ok = True
        try:
  
          one_way = dictdiffer.patch(client_delta, baseline)
          one_way = dictdiffer.patch(server_diff, one_way, copy_original = False)

          other_way = dictdiffer.patch(server_diff, baseline)
          other_way = dictdiffer.patch(client_delta, other_way, copy_original = False)
          
        except Exception:
          build_up_ok = False
  
        if build_up_ok and one_way == other_way:
          self.version += 1
          self.content = other_way
          self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
          
          return {
            'status': 'merged',
            'version': self.version,
            'baseline': client_previous_version,
            'diffs': server_diff
          }
        else:
          self.client_last_seen_content[client_id] = copy.deepcopy(self.content)
          return {
            'status': 'conflict',
            'version': self.version,
            'baseline': client_previous_version,
            'diffs': server_diff
          }
      
      
    if 'status' in message:
      
      if message['status'] == 'misaligned':
        raise Exception('Version misalignment between client and server: ' + str(message['message']))
      
      if message['status'] == 'error':
        raise Exception('Error: ' + str(message['message']))
      
      if message['baseline'] == self.version:
        if message['status'] == 'ok':
          #print('ok ', end=' ')
          self.version = message['version']
          self.prev_value = current_value
        
        elif message['status'] == 'merged':
          #print('merged ', end=' ')
          self.prev_value = dictdiffer.patch(message['diffs'], current_value)
          self.version = message['version']
        
        elif message['status'] == 'conflict':
          #print('conflict ', end=' ')
          try:
            self.prev_value = dictdiffer.patch(message['diffs'], self.prev_value)
            self.version = reply['version']
          except Exception as e:
            print('Error patching client to match server')
            print('* previous client value:')
            p(self.prev_value)
            print('* diffs:')
            p(message['diffs'])
            raise e
