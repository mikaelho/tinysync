import copy
import dictdiffer

class Sync:
  
  default_init_func = list
  
  def __init__(self, content, data_id, conduit, change_callback=None, init_func=None):
    self.content = content
    self.data_id = data_id
    self.conduit = conduit
    self.change_callback = change_callback
    self.init_func = init_func or self.default_init_func
    conduit.register_handler(self)
    # Upwards
    self.prev_content = None
    self.my_version_up = 0
    # Downwards
    self.prev_content_down = {}
    self.my_version_down = {}
    self.version_from_below = {}
    #self.client_version = {}
   
  @staticmethod 
  def _generate_checksum(data):
    ''' Returns a hash of the JSON-serializable parameter '''
    string_data = json.dumps(data, sort_keys=True)
    return hashlib.md5(string_data.encode()).hexdigest()
    
  def update_local(self):
    self.update_up()
    self.update_down()
    
  def receive_message(self, sync_id, message):
    switch = {
      'update up': self.update_from_below,
      'update down': self.update_from_above
    }
    switch[message['action']](sync_id, message)
    
  def update_up(self):
    version_diff = list(dictdiffer.diff(self.prev_content, self.content))
    if len(version_diff) == 0:
      return 
    #checksum = self._generate_checksum(self.prev_content)
    message = {
      'action': 'update up',
      'previous_version': self.my_version_up,
      'delta': version_diff,
      'data_id': self.data_id,
      #'checksum': checksum
    }
    self.conduit.send_up(self, message)
    
  def update_down(self):
    for sync_id in self.conduit.peers_down(self):
      down_diff = list(dictdiffer.diff(self.prev_content_down.get(sync_id, self.init_func()), self.content))
      if len(down_diff) == 0:
        continue
      version = self.my_version_down.get(sync_id, 0) + 1
      self.my_version_down[sync_id] = version
      message = {
        'action': 'update down',
        'version': version,
        'previous_version': self.version_from_below.get(sync_id, 0),
        'delta': down_diff
      }
      print(message)
      self.conduit.send_to(sync_id, self, message)
    
  def update_from_above(self, sync_id, message):
    previous_version = int(message['previous_version'])
    
    if previous_version != self.my_version_up:
      pass
    diff_from_above = message['delta']
    local_diff = list(dictdiffer.diff(self.prev_content, self.content))
    
    if len(local_diff) == 0:
      dictdiffer.patch(diff_from_above, self.content, in_place=True)
      self.prev_content = copy.deepcopy(self.content)
      self.my_version_up = message['version']
      
    elif len(diff_from_above) == 0:
      self.prev_content = copy.deepcopy(self.content)
      self.my_version_up = message['version']
      self.update_up()
      
    else:
      build_up_ok = True
      try:
  
        one_way = dictdiffer.patch(local_diff, self.prev_content)
        one_way = dictdiffer.patch(diff_from_above, one_way, in_place=True)

        other_way = dictdiffer.patch(diff_from_above, self.prev_content)
        other_way = dictdiffer.patch(local_diff, other_way, in_place=True)
          
      except Exception:
        build_up_ok = False
  
      if build_up_ok and one_way == other_way:
        self.my_version_up = message['version']
        self.content = other_way
        dictdiffer.patch(diff_from_above, self.prev_content)
      else:
        self.my_version_up = message['version']
        dictdiffer.patch(diff_from_above, self.prev_content)
        self.content = copy.deepcopy(self.prev_content)
      self.update_down()
    
  def update_from_below(self, sync_id, message):
    previous_version = int(message['previous_version'])
    local_version = self.my_version_down.get(sync_id, 0)
    
    '''
    if previous_version < 0 or previous_version > my_version_down:
      message = {
        'status': 'error',
        'message': f'Version number out of range: {previous_version}'
      }
      self.conduit.send_to(sync_id, self, message)
      return
    '''
    #checksum = message['checksum']
    #delta_from_down = copy.deepcopy(message['delta'])
    diff_from_below = message['delta']
      
    if previous_version == local_version:
      
      '''
      if not checksum == generate_checksum(self.content):
        message = { 
          'status': 'misaligned',
          'message': 'Content checksums do not match for peer ' + sync_id
        }
        self.conduit.send_to(sync_id, self, message)
        return
      '''
      print('dfb', diff_from_below)
      print('sc', self.content)
      dictdiffer.patch(diff_from_below, self.content, in_place=True)
      self.my_version_down[sync_id] += 1
      self.prev_content_down[sync_id] = copy.deepcopy(self.content)
      
      self.update_up()
      self.update_down()
      
      '''
      message = {
        'status': 'ok',
        'version': self.my_version_down[sync_id],
        'baseline': previous_version
      }
      self.conduit.send_to(sync_id, self, message)
      self.update_up()
      return 
      '''
      
    elif previous_version < local_version:
      baseline = self.prev_content_down.get(sync_id, self.init_func())

      '''
      if not checksum == generate_checksum(baseline):
        message = { 
          'status': 'misaligned',
          'message': 'Baseline checksums do not match in merge for peer ' + sync_id
        }
        self.conduit.send_to(sync_id, self, message)
        return
      '''
        
      local_diff = diff(baseline, self.content)
        
      build_up_ok = True
      try:
  
        one_way = dictdiffer.patch(diff_from_below, baseline)
        one_way = dictdiffer.patch(local_diff, one_way, in_place=True)

        other_way = dictdiffer.patch(local_diff, baseline)
        other_way = dictdiffer.patch(client_delta, other_way, in_place=True)
          
      except Exception:
        build_up_ok = False
  
      if build_up_ok and one_way == other_way:
        self.my_version_down[sync_id] += 1
        self.content = one_way
        self.prev_content_down[sync_id] = other_way
          
        '''
        message = {
          'status': 'merged',
          'version': self.my_version_down[sync_id],
          'baseline': previous_version,
          'diffs': my_diff
        }
        self.conduit.send_to(sync_id, self, message)
        '''
        self.update_up()
        self.update_down()
        
      else:
        self.prev_content_down[sync_id] = copy.deepcopy(self.content)
        
        '''
        message = {
          'status': 'conflict',
          'version': self.my_version_down[sync_id],
          'baseline': previous_version,
          'diffs': server_diff
        }
        self.conduit.send_to(sync_id, self, message)
        return
        '''
        self.update_down()
    

  '''  
  def remote_update(self, remote_id, message):
    if 'put' in message:

      
      
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
  '''
