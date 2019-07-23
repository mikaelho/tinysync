from ui_tester_core import *
from tinysync.conduit.websocket import WebsocketConduit
from tinysync.conduit.websocket_server import WebsocketServer
import asyncio


import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
host = s.getsockname()[0]
s.close()
print(host)

# This is necessary in Pythonista on iOS
asyncio.set_event_loop(asyncio.new_event_loop())

server = WebsocketServer(host='10.0.0.6')
  
v = CloseableView(background_color=.7)

conduit = WebsocketConduit(host='10.0.0.6')
one = SeaOfBalls(conduit)

grid = GridView(pack=GridView.FILL, frame=v.bounds, flex='WH')
v.add_subview(grid)
grid.add_subview(one)
v.present()

asyncio.get_event_loop().run_until_complete(
  conduit.main())
server.close()

