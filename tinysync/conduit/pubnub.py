'''

'''

import uuid

from pubnub.pnconfiguration import PNConfiguration
from pubnub.callbacks import SubscribeCallback
from pubnub.pubnub import PubNub

class PubNubConduit(SubscribeCallback):
  
  def __init__(self, sub_key, pub_key):
    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = sub_key
    pnconfig.publish_key = pub_key
    pnconfig.ssl = True
 
    self.pubnub = PubNub(pnconfig)
    self.pubnub.add_listener(self)
    self.node_id = str(self.pubnub.uuid)
    
    self.locals = {}
    self.remotes = {}
    self.up = {}
    self.down = {}
    self.pubnub.subscribe().channels('registrations').execute()
    
  def register_handler(self, handler):
    self.locals[handler.data_id] = handler
    self.pubnub.subscribe().channels(handler.data_id + '-' + self.node_id).execute()
    self.announce_node(handler.data_id)
    
  def announce_node(self, data_id):
    self.pubnub.publish().\
    channel('registrations').\
    message({
      'data_id': data_id,
      'node_id': self.node_id
    }).sync()
    
  def register_remote_handler(self, node_id, data_id):
    remote_handlers = self.remotes.setdefault(data_id, set())
    if node_id not in remote_handlers:
      remote_handlers.add(node_id)
      if data_id in self.locals:
        self.announce_node(data_id)
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
    
  def send_to(self, to_node_id, handler, message):
    self.pubnub.publish().\
    channel(handler.data_id+'-'+to_node_id).\
    message(message).sync()
  
  def message(self, pubnub, pn_message):
    print(pn_message.message)
    print(pn_message.channel)
    print(pn_message.publisher)
    if pn_message.channel == 'registrations':
      content = pn_message.message
      data_id = content['data_id']
      node_id = content['node_id']
      self.register_remote_handler(node_id, data_id)
    else:
      message = pn_message.message
      source_id = str(pn_message.publisher)
      data_id = pn_message.channel[:-(len(source_id)+1)]
      handler = self.locals.get(data_id, None)
      if handler:
        handler.receive_message(source_id, message)
      

if __name__ == '__main__':

  import sync_conf
  
  c = PubNubConduit(
    sync_conf.pubnub_sub,
    sync_conf.pubnub_pub)
