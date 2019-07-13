'''
Differential synchronization of Python dict/list data structures

Peer-to-peer implementation of the algorithm described at:
https://neil.fraser.name/writing/sync/
'''

#TODO: Features to implement
# Disaster branch
# Timeout replies
# Specific masters

import copy, itertools, uuid, threading
import dictdiffer

from tinysync.conduit.conduit import MemoryConduit

class Sync:
  
  lock = threading.RLock()
  
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
    
  def stop(self):
    self.conduit.shutdown()
    
  def receive_message(self, source_id, message):
    self.remote_update(source_id, message, 
      message.get('upwards', False))
    
  def update_others(self):
    self.update_up()
    self.update_down()
    if self.change_callback is not None:
      self.change_callback()
    
  def update_up(self):
    up_id = self.conduit.up
    if up_id is None: return
    self.send_update(up_id, upwards=True)
    
  def update_down(self):
    down_ids = self.conduit.down
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
    self.conduit.send_to(receiver_id, message)

  def remote_update(self, source_id, message, upwards):
    with self.lock:
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
      
      if sender_version >= version_other and expected_local_version == version_local:
  
        # Discard local edits that have been
        # received by the other
        self.edit_chain_local[source_id] = [item for item in edit_chain_local
        if item[0] > version_local]
        
        # Discard incoming edits that have
        # already been processed
        
        diff_other = list(itertools.chain.from_iterable(
          [item[1] for item in edit_chain_other if item[0] >= version_local]
        ))
        
      elif (sender_version >= backup_version_other and 
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
      self.version_other[source_id] = version_other + 1 #+= 1
      
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
      

