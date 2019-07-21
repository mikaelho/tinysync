'''
Differential synchronization of Python dict/list data structures

Peer-to-peer implementation of the algorithm described at:
https://neil.fraser.name/writing/sync/
'''

#TODO: Features to implement
# Specific masters

import copy, itertools, uuid, json, hashlib, threading
import dictdiffer

from tinysync.conduit.conduit import MemoryConduit

debugging = False

class Sync:
  
  lock = threading.RLock()
  
  def __init__(self,
  initial_value, content=None, 
  data_id='default', conduit=None, 
  change_callback=None):
    self.initial_value = initial_value
    self.initial_checksum = Sync.generate_checksum(initial_value)
    self.content = content or copy.deepcopy(self.initial_value)
    self.data_id = data_id
    self.conduit = conduit or MemoryConduit()
    self.change_callback = change_callback

    self.conduit.register_handler(self)
    
    self.baseline = {}
    self.edits = {}
    
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
    for down_id in down_ids:
      self.send_update(down_id, upwards=False)
      
  def get_values_for(self, node_id):   
    return  (
      self.baseline.setdefault(node_id, copy.deepcopy(self.initial_value)),
      self.edits.setdefault(
        node_id,
        [(self.initial_checksum, [])])
        #[('0-'+str(self.initial_checksum), [])])
    )
    
  def send_update(self, receiver_id, upwards):
    #global debugging
    
    #with self.lock:
    
      (baseline,
      edits
      ) = self.get_values_for(receiver_id)
      
      if debugging:
        print(self.conduit.node_id[:8], '->', receiver_id[:8])
      
      '''
      ctrl = input()
      if ctrl == 'd':
        debugging = True
      '''
      
      #1
      #previous_version = int(edits[-1][0].split('-')[0])
      add_to_baseline = Sync.collapse_edits(edits)
  
      previous_value = dictdiffer.patch(
        add_to_baseline, baseline)
      latest_edit = list(dictdiffer.diff(
        previous_value, self.content))
      latest_checksum = Sync.generate_checksum(self.content)
      #edits.append((str(previous_version+1)+'-'+str(latest_checksum), latest_edit))
      if len(latest_edit) > 0:
        edits.append((latest_checksum, latest_edit))
      
      if debugging:
        print('edits out', edits)
      
      #2
      message = {
        'upwards': upwards,
        'edits': edits,
      }
    
      self.conduit.send_to(receiver_id, message)

  def remote_update(self, source_id, message, upwards):
    global debugging
    
    with self.lock:
      (baseline,
      edits
      ) = self.get_values_for(source_id)
      
      remote_edits = copy.deepcopy(message['edits'])
      
      # Find matching edit level
      remote_index = local_index = -1
      for j, local_item in reversed(list(
        enumerate(edits))):
          for i, remote_item in reversed(list(
            enumerate(remote_edits))):
              if remote_item[0] == local_item[0]:
                remote_index = i
                local_index = j
                break
          if remote_index != -1: break
          
      if remote_index == -1:
        print('PROBLEM', edits, remote_edits)
        
      content_at_start = copy.deepcopy(self.content)
      
      if debugging:          
        print('local edits', edits)
        print('baseline before', baseline)
                
      if local_index > -1:
        add_to_baseline = Sync.collapse_edits(edits[:local_index+1])
        #print('add to baseline', add_to_baseline)
        
        dictdiffer.patch(
          add_to_baseline, baseline,
          in_place=True)
          
        #print('baseline after', self.baseline[source_id])
          
        baseline_checksum = edits[local_index][0]
        self.edits[source_id] = list([(baseline_checksum, [])] + [
          item for i, item in enumerate(edits)
          if i > local_index
        ])
        #print('edits', self.edits[source_id])
        
        diff_local = Sync.collapse_edits(edits[local_index+1:])

        diff_other = Sync.collapse_edits(remote_edits[remote_index+1:])
        
        local_change = self.merge(diff_other, diff_local, baseline, upwards)
        #print('local change', local_change)
        dictdiffer.patch(local_change, self.content, in_place=True)
        
        #print('content', self.content)

      if content_at_start != self.content:
        self.update_others()
        if self.change_callback is not None:
          self.change_callback()
      elif len(self.edits[source_id]) > 1 or len(remote_edits) > 1:
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
    except Exception as e:
      build_up_ok = False

    if build_up_ok and one_way == other_way:
      #return one_way
      return diff_other
    else:
      #print('merge failed')
      if not upwards:
        #return dictdiffer.patch(diff_other, baseline)
        #print('PROBLEM')
        return list(dictdiffer.diff(self.content, baseline)) + diff_other
      else:
        #return self.content
        return []
      
      
  def stop(self):
    self.conduit.shutdown()    

  @staticmethod 
  def generate_checksum(data):
    "Returns a hash of the JSON-serializable parameter"
    string_data = json.dumps(data, sort_keys=True)
    return hashlib.md5(string_data.encode()).hexdigest()
    
  @staticmethod
  def collapse_edits(edits):
    result = []
    for edit in edits:
      result += edit[1]
    return result

  
if __name__ == '__main__':
  test_edit_chain = [(1, ['edit']), (2, ('edit', 'edit')), (3, [])]
  assert Sync.collapse_edits(test_edit_chain) == ['edit', 'edit', 'edit']
