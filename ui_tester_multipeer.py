'''
Synchronization visualizer that only works on the Pythonista app on iOS devices.

Requires additional modules:
  * anchor module for layout
  * multipeer module for device-to-device conduit
'''

from ui_tester_core import *
from tinysync.conduit.multipeer import MultipeerConduit

v = CloseableView(background_color=.7)

one = SeaOfBalls(MultipeerConduit())
#two = SeaOfBalls(MultipeerConduit())
#three = SeaOfBalls(MultipeerConduit())
#four = SeaOfBalls(MultipeerConduit())

grid = GridView(pack=GridView.FILL, frame=v.bounds, flex='WH')
v.add_subview(grid)

grid.add_subview(one)
#grid.add_subview(two)
#grid.add_subview(three)
#grid.add_subview(four)

v.present()

