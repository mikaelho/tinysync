import asyncio, json
import websockets

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
    
  def close(self):
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
        
        
if __name__ == '__main__':
  server = WebsocketServer()
  server.close()
