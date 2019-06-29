'''

'''

import uuid

class MemoryConduit:
  
  nodes = {}
  
  def __init__(self):
    self.node_id = uuid.uuid4()
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
    
if __name__ == '__main__':
  
  from types import SimpleNamespace
  
  class MinimalHandler:
    
    def __init__(self, data_id):
      self.data_id = data_id
      
    def receive_message(self, remote_node_id, message):
      print(f'{self.data_id} received {message} from node {str(remote_node_id)[-12:]}')
  
  ha = MinimalHandler('A')
  n1 = MemoryConduit()
  n1.register_handler(ha)
  
  hb = MinimalHandler('B')
  n2 = MemoryConduit()
  n2.register_handler(ha)
  n2.register_handler(hb)
  
  n1.broadcast(ha, 'Message #1')
  n1.send_to(n2.node_id, ha, 'Message #2')
  n1.send_up(ha, 'Message #3')
