'''
Conduit implementation using the websocket package and an included server implementation.

See: https://websockets.readthedocs.io
'''

import uuid, json, urllib.parse, asyncio

from tinysync.conduit.conduit import Conduit

import websockets
    

class WebsocketConduit(Conduit):
  
  def __init__(self, host='localhost', port=8765, loop=None):
    super().__init__()
    self.host = host
    self.port = port
    self.loop = loop or asyncio.get_event_loop()
    
  def startup(self):
    uri = f'ws://{self.host}:{self.port}/{self.data_id}/{self.node_id}'
    self.websocket = self.loop.run_until_complete(websockets.connect(uri))
        
  async def main(self):
    
    async for message_raw in self.websocket:
      print(message_raw)
      message = json.loads(message_raw)
      source_id = message['source_id']
      action = message['action']
      if action == 'register':
        self.register_remote_handler(source_id)
      elif action == 'remove':
        self.remove_remote_handler(source_id)
      else:
        payload = message['payload']
        self.receive(source_id, payload)
    # Let shutdown call complete
    await asyncio.sleep(0.5)
        
  def send_to(self, target_node_id, message):
    wrapped_message = json.dumps({
      'action': 'message',
      'source_id': self.node_id,
      'target_id': target_node_id,
      'payload': message
    })
    asyncio.run_coroutine_threadsafe(
      self.websocket.send(wrapped_message), 
      loop=self.loop).result()
        
  def shutdown(self):
    asyncio.run_coroutine_threadsafe(self.websocket.close(), loop=self.loop).result()
    
    
class WebsocketServer:
  
  def __init__(self, host='localhost', port=8765, loop=None):
    self.mappings = {}
    _loop = loop or asyncio.get_event_loop()
    
    start_server = websockets.serve(
      self.handler,
      host, port,
      loop=_loop)
    self.server = start_server.ws_server
    asyncio.get_event_loop().run_until_complete(start_server)
    
  def stop(self):
    self.server.close()
  
  async def handler(self, websocket, path):
    _, data_id, node_id = path.split('/')
    mappings = self.mappings.setdefault(data_id, [{},{}])
    sockets = mappings[0]
    nodes = mappings[1]
    nodes[websocket] = node_id
    sockets[node_id] = websocket
    
    register_message = json.dumps({
      'action': 'register',
      'source_id': node_id
    })
    await asyncio.wait([
      ws.send(register_message)
      for ws in nodes])
    
    async for message_json in websocket:
      message = json.loads(message_json)
      target_id = message['target_id']
      message['source_id'] = node_id
      target_websocket = self.node_to_ws[target_id]
      await target_websocket.send(json.dumps(message))
    
    del nodes[websocket]
    del sockets[node_id]
    
    if len(nodes) > 0:
      remove_message = json.dumps({
        'action': 'remove',
        'source_id': node_id
      })
      await asyncio.wait([
        ws.send(register_message)
        for ws in nodes])
