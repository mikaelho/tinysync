'''
Differential synchronization of Python dict/list data structures

Peer-to-peer implementation of the algorithm described at:
https://neil.fraser.name/writing/sync/
'''

#TODO: Features to implement
# Disaster branch

import copy, itertools, uuid
import dictdiffer

class Sync:
  
  def __init__(self,
  initial_value, content=None, 
  data_id='default', conduit=None, 
  change_callback=None):
    self.initial_value = initial_value
    self.content = content or copy.deepcopy(self.initial_value)
    self.data_id = data_id
    self.conduit = conduit or MemoryConduit()
    self.change_callback = change_callback

    self.conduit.register_handler(self)
    
    self.content_shadow = {}
    self.shadow_backup = {}
    self.edit_chain_local = {}
    self.version_local = {}
    self.version_other = {}
    self.backup_version_local = {}
    self.backup_version_other = {}
    
    '''
    # Upwards
    self.prev_content = self.init_func()
    self.my_version_up = 0
    # Downwards
    self.prev_content_down = {}
    self.my_version_down = {}
    self.version_from_below = {}
    #self.client_version = {}
    '''
   
  @staticmethod 
  def _generate_checksum(data):
    ''' Returns a hash of the JSON-serializable parameter '''
    string_data = json.dumps(data, sort_keys=True)
    return hashlib.md5(string_data.encode()).hexdigest()
   
  ''' 
  def update_local(self):
    self.update_up()
    self.update_down()
  '''
    
  def receive_message(self, source_id, message):
    self.remote_update(source_id, message, 
      message.get('upwards', False))
    
  def update_others(self):
    self.update_up()
    self.update_down()
    if self.change_callback is not None:
      self.change_callback()
    
  def update_up(self):
    up_id = self.conduit.up.get(self.data_id, None)
    if up_id is None: return
    self.send_update(up_id, upwards=True)
    
  #TODO: make down a list again
  def update_down(self):
    down_ids = self.conduit.peers_down(self)
    #self.conduit.down.get(self.data_id, None)
    #if down_id is None: return
    #self.send_update(down_id, upwards=False)
    for down_id in down_ids:
      self.send_update(down_id, upwards=False)
      
  def get_values_for(self, sync_id):
    return  (
      self.content_shadow.setdefault(sync_id, copy.deepcopy(self.initial_value)),
      self.shadow_backup.setdefault(sync_id, copy.deepcopy(self.initial_value)),
      self.edit_chain_local.setdefault(sync_id, []),
      self.version_local.setdefault(sync_id, 0),
      self.version_other.setdefault(sync_id, 0),
      self.backup_version_local.setdefault(sync_id, 0),
      self.backup_version_other.setdefault(sync_id, 0),
    )
    
  def send_update(self, receiver_id, upwards):
    (content_shadow,
    shadow_backup,
    edit_chain_local,
    version_local,
    version_other,
    backup_version_local, 
    backup_version_other) = self.get_values_for(receiver_id)
    
    #1
    local_diff = list(dictdiffer.diff(content_shadow, self.content))
    edit_chain_local.append(
      (version_local, local_diff))
    
    #2
    message = {
      'upwards': upwards,
      'edits': edit_chain_local,
      'sender_version': version_local,
      'receiver_version': version_other
      #'checksum': checksum
    }
    
    #3
    self.content_shadow[receiver_id] = copy.deepcopy(self.content)
    self.version_local[receiver_id] += 1
    
    #print('SEND', self.conduit.index(self), message)
    self.conduit.send_to(receiver_id, self, message)

  def remote_update(self, source_id, message, upwards):
    (content_shadow,
    shadow_backup,
    edit_chain_local,
    version_local,
    version_other,
    backup_version_local, 
    backup_version_other) = self.get_values_for(source_id)
    
    edit_chain_other = message['edits']
    sender_version = message['sender_version']
    expected_local_version = message['receiver_version']
    
    content_at_start = copy.deepcopy(self.content)
    
    if sender_version == version_other and expected_local_version == version_local:

      # Discard local edits that have been
      # received by the other
      self.edit_chain_local[source_id] = [item for item in edit_chain_local
      if item[0] > version_local]
      
      diff_other = list(itertools.chain.from_iterable(
        [item[1] for item in edit_chain_other]
      ))
      
    elif (sender_version == backup_version_other and 
    expected_local_version == backup_version_local):

      # delete local edit stack
      edit_chain_local = self.edit_chain_local[source_id] = []
      
      # copy the shadow backup into content shadow
      content_shadow = self.content_shadow[source_id] = copy.deepcopy(shadow_backup)
      
      # disregard incoming edits already seen
      diff_other = list(itertools.chain.from_iterable(
        [item[1] for item in edit_chain_other if item[0] > backup_version_local]
      ))
    else:
      raise NotImplementedError('Catastrophies not handled yet')
    
    baseline = copy.deepcopy(content_shadow)
  
    #5, 6
    dictdiffer.patch(diff_other, content_shadow, in_place=True)
    self.version_other[source_id] += 1
    
    #7
    self.shadow_backup[source_id] = copy.deepcopy(content_shadow)
    self.backup_version_local[source_id] = version_local
    self.backup_version_other[source_id] = self.version_other[source_id]
    
    #8, 9 with merge
    diff_local = dictdiffer.diff(baseline, self.content)
    self.merge(diff_other, diff_local, baseline, upwards)
    
    if content_at_start != self.content:
      self.update_others()
      if self.change_callback is not None:
        self.change_callback()
    elif len(edit_chain_other) > 1 or len(edit_chain_other[0][1]) > 0:
      self.send_update(source_id, upwards==False)
      

  def merge(self, diff_other, diff_local, baseline, upwards):
    # Merge is possible if it does not matter
    # in which order we apply the two deltas
    build_up_ok = True
    try:
      one_way = dictdiffer.patch(diff_other, baseline)
      one_way = dictdiffer.patch(diff_local, one_way, in_place=True)

      other_way = dictdiffer.patch(diff_local, baseline)
      other_way = dictdiffer.patch(diff_other, other_way, in_place=True)
    except Exception:
      build_up_ok = False

    if build_up_ok and one_way == other_way:
      self.content = one_way
    elif not upwards:
      self.content = dictdiffer.patch(diff_other, baseline)
      
class MemoryConduit:
  
  nodes = {}
  
  def __init__(self, conduit):
    self.node_id = str(uuid.uuid4())
    self.conduit = conduit
    self.nodes[self.node_id] = self
    self.locals = {}
    self.remotes = {}
    self.up = {}
    self.down = {}
  
  def register_handler(self, handler):
    self.locals[handler.data_id] = handler
    for node in self.nodes.values():
      if node is not self:
        node.register_remote_handler(self.node_id, handler.data_id)
    
  def register_remote_handler(self, node_id, data_id):
    remote_handlers = self.remotes.setdefault(data_id, set())
    #print(remote_handlers)
    if node_id not in remote_handlers:
      remote_handlers.add(node_id)
      if data_id in self.locals:
        self.nodes[node_id].register_remote_handler(self.node_id, data_id)
    for id in sorted(remote_handlers):
      if id > self.node_id:
        self.up[data_id] = id
        break
    else:
      self.up[data_id] = None
    for id in sorted(remote_handlers, reverse=True):
      if id < self.node_id:
        self.down[data_id] = id
        break
    else:
      self.down[data_id] = None
      
  def index(self, handler):
    return sorted(self.nodes.keys()).index(self.node_id)
      
  def peers_down(self, handler):
    down = self.down[handler.data_id]
    return [] if down is None else [down]
      
  def broadcast(self, handler, message):
    for node in self.nodes.values():
      if node is not self:
        node.receive_message(self.node_id, handler.data_id, message)
        
  def receive_message(self, remote_node_id, data_id, message):
    handler = self.locals.get(data_id, None)
    if handler:
      handler.receive_message(remote_node_id, message)
    
  def send_up(self, handler, message):
    to_id = self.up[handler.data_id]
    if to_id is not None:
      self.send_to(to_id, handler, message)
    return to_id is not None
    
  def send_to(self, to_node_id, handler, message):
    self.nodes[to_node_id].receive_message(self.node_id, handler.data_id, message)
