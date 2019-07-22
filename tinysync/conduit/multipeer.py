'''
Conduit implementation using the Apple Multipeer Connectivity framework and Pythonista app on iOS devices.

See: https://github.com/mikaelho/multipeer/
'''

import uuid

from tinysync.conduit.conduit import Conduit

import multipeer

class MultipeerConduit(Conduit):
    
  def startup(self):
    '''
      * Perform setup needed before announcing node to peers
    '''
    self.mc = MultipeerHandler(
      self,
      service_type=self.data_id,
      initial_data=self.node_id
    )
    
  def send_to(self, target_node_id, message):
    '''
      * Call `receive` method on the target node with sending node id and 
      message content
    '''
    self.mc.send_message(target_node_id, message)
    
  def shutdown(self):
    '''
      * Disconnect from the peer network
      * Call `remove_remote_handler` at all nodes that handle the same data_id
    '''
    self.mc.end_all()
    
    
class MultipeerHandler(multipeer.MultipeerConnectivity):
  
  def __init__(self, conduit, *args, **kwargs):
    self.conduit = conduit
    self.peer_by_node = {}
    self.node_by_peer = {}
    super().__init__(*args, **kwargs)
    
  def peer_added(self, peer_id):
    node_id = self.get_initial_data(peer_id)
    self.peer_by_node[node_id] = peer_id
    self.node_by_peer[peer_id] = node_id
    self.conduit.register_remote_handler(node_id)
    
  def peer_removed(self, peer_id):
    node_id = self.node_by_peer[peer_id]
    self.conduit.remove_remote_handler(node_id)
    
  def send_message(self, target_node_id, message):
    peer_id = self.peer_by_node[target_node_id]
    self.send(message, to_peer=peer_id)
    
  def receive(self, message, from_peer):
    source_id = self.node_by_peer[from_peer]
    self.conduit.receive(source_id, message)
    
