'''
Synchronization visualizer that only works on the Pythonista app on iOS devices.

Requires additional modules:
  * anchor module for layout
  * multipeer module for device-to-device conduit
'''

from ui_tester_core import *
from tinysync.conduit.pubnub import PubNubConduit

import sync_conf

v = CloseableView(background_color=.7)

one = SeaOfBalls(PubNubConduit(sync_conf.pubnub))
two = SeaOfBalls(PubNubConduit(sync_conf.pubnub))

grid = GridView(pack=GridView.FILL, frame=v.bounds, flex='WH')
v.add_subview(grid)

grid.add_subview(one)
grid.add_subview(two)

v.present()
