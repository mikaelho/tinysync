'''
Conduit implementation using the PubNub messaging service at pubnub.com.

You need to register with PubNub to create an "application" and get publish and subscribe keys to use with this conduit. Small-volume messaging is free.
'''

import uuid

from tinysync.conduit.conduit import Conduit

from pubnub.pnconfiguration import PNConfiguration
from pubnub.callbacks import SubscribeCallback
from pubnub.pubnub import PubNub

#TODO:
# register-data_id
# unregister_handler
# unsubscribe both data_id-specific topics

class PubNubConduit(Conduit, SubscribeCallback):
  
  def __init__(self, sub_key, pub_key):
    super().__init__()
    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = sub_key
    pnconfig.publish_key = pub_key
    pnconfig.ssl = True
 
    self.pubnub = PubNub(pnconfig)
    self.pubnub.add_listener(self)
    self.node_id = str(self.pubnub.uuid)
    
  def startup(self):
    '''
      * Perform setup needed before announcing node to peers
    '''
    self.reg_channel = 'registrations-' + self.data_id
    self.channel = self.data_id + '-' + self.node_id
    self.pubnub.subscribe().channels(self.reg_channel).execute()
    self.pubnub.subscribe().channels(self.channel).execute()
    
  def announce_node(self):
    '''
      * Call `register_remote_handler` at all nodes that handle the same 
      data_id
    '''
    self.pubnub.publish().\
    channel(self.reg_channel).\
    message({
      'action': 'register'
    }).sync()
    
  def send_to(self, target_node_id, message):
    '''
      * Call `receive` method on the target node with sending node id and 
      message content
    '''
    self.pubnub.publish().\
    channel(f'{self.data_id}-{target_node_id}').\
    message(message).sync()
    
  def shutdown(self):
    '''
      * Close all channels
      * Call `remove_remote_handler` at all nodes that handle the same data_id
    '''
    self.pubnub.publish().\
    channel(self.reg_channel).\
    message({
      'action': 'remove'
    }).sync()
    self.pubnub.unsubscribe_all()
    
  def message(self, pubnub, pn_message):
    source_id = str(pn_message.publisher)
    if pn_message.channel == self.reg_channel:
      action = pn_message.message['action']
      if action == 'register':
        self.register_remote_handler(source_id)
      else:
        self.remove_remote_handler(source_id)
    else:
      message = pn_message.message
      self.receive(source_id, message)
    
    
if __name__ == '__main__':

  import sync_conf
  
  c = PubNubConduit(
    sync_conf.pubnub_sub,
    sync_conf.pubnub_pub)
