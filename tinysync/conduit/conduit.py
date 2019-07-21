'''
Abstract base class for conduits that move messages between a group of peer nodes all sharing the same data id.

Implemented:
  * In-memory reference conduit
  * PubNub conduit supporting internet-wide sync
  * iOS multipeer connectivity supporting local peer discovery and syncing
  abc
Planned:
  * Websocket conduit for running your own server
  * AWS/Azure/Google messaging conduits
  * Apple messaging?
'''

import uuid

class Conduit:
  '''
  Baseclass for conduits. Not an ABC to avoid confusion if subclasses need multiple inheirtance.
  '''
  
  def __init__(self):
    self.node_id = str(uuid.uuid4())
    self.up = None
    self.down = []
    self.handler = None
    
  def register_handler(self, handler):
    self.handler = handler
    self.data_id = handler.data_id
    self.node_ids = set([self.node_id])
    self.startup()
    self.announce_node()
    
  def register_remote_handler(self, node_id):
    #with self.handler.lock:
      if node_id not in self.node_ids:
        self.node_ids.add(node_id)
        self.announce_node()
        self.set_up_and_down()
    
  def receive(self, source_node_id, message):
    self.handler.receive_message(
      source_node_id,
      message)
    
  def remove_remote_handler(self, node_id):
    #with self.handler.lock:
      self.node_ids.discard(node_id)
      self.set_up_and_down()
    
  def set_up_and_down(self):
    for id in sorted(self.node_ids):
      if id > self.node_id:
        self.up = id
        break
    else:
      self.up = None
    for id in sorted(self.node_ids, reverse=True):
      if id < self.node_id:
        self.down = [id]
        break
    else:
      self.down = []
      
  def startup(self):
    '''
    Implement in subclasses:
      * Perform any setup needed before announcing node to peers
    '''
    ...
      
  def announce_node(self):
    '''
    Implement in subclasses:
      * Must call `register_remote_handler` at all nodes that handle the same 
      data_id
    '''
    ...
    
  def send_to(self, target_node_id, message):
    '''
    Implement in subclasses:
      * Must call `receive` method on the target node
    '''
    ...
    
  def shutdown(self):
    '''
    Implement in subclasses:
      * Perform any needed cleanup
      * Must call `remove_remote_handler` at all nodes that handle the same data_id
    '''
    ...
    
  
class MemoryConduit(Conduit):
  '''
  Conduit for in-memory testing.
  
  Uses a class variable to keep track of all the different "nodes" of handlers.
  Node-to-node messages are just method calls.
  '''
  
  nodes = {}
  nodes_by_data_id = {}
  
  def startup(self):
    self.nodes[self.node_id] = self
  
  def announce_node(self):
    self.all_nodes = self.nodes_by_data_id.setdefault(
      self.data_id, set([self.node_id]))
    self.all_nodes.add(self.node_id)
    for node_id in self.all_nodes:
      self.nodes[node_id].register_remote_handler(self.node_id)
    
  def shutdown(self):
    del self.nodes[self.node_id]
    self.all_nodes.discard(self.node_id)
    for node_id in self.all_nodes:
      self.nodes[node_id].remove_remote_handler(self.node_id)
      
  def send_to(self, target_node_id, message):
    self.nodes[target_node_id].receive(self.node_id, message)
    
  '''
  def deregister_handler(self, handler):
    if handler.data_id not in self.locals:
      return
    del self.locals[handler.data_id]
    self.remove_node(handler.data_id)
    
  def remove_node(self, data_id):
    pass
    

      
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
  '''
