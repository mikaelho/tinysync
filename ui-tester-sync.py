'''
Synchronization visualizer that only works on the Pythonista app on iOS devices.

Requires additional modules:
  * PubNub client libraries
  * anchor module for layout
  * multipeer module for device-to-device conduit
'''

from ui import *
from anchor import *
import tinysync
from tinysync.conduit.pubnub import PubNubConduit
from tinysync.conduit.ios_multipeer import MultipeerConduit
import random, functools, time

import sync_conf

class CloseableView(ui.View):
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.visible_touches = []
    self.update_interval = 1/60
  
  def update(self):
    for t in self.visible_touches:
      if t[0] is None:
        t[0] = ui.View(
          background_color=(0.9,0.9,0.9,0.5),
          border_color=(0.9,0.9,0.9),
          border_width=1,
          width=30,
          height=30,
          corner_radius=15,
          touch_enabled=False
        )
        t[0].center = t[1]
        self.add_subview(t[0])
      else:
        t[2] -= 0.1
        t[0].alpha = t[2]
        if t[2] == 0.0:
          self.remove_subview(t[0])
    self.visible_touches = [
      t for t in self.visible_touches
      if t[2] > 0.0
    ]
  
  def will_close(self):
    for subv in self.subviews[0].subviews:
      subv.will_close()

class MoveableView(ui.View):
  
  def touch_began(self, touch):
    self.start_time = time.time()
    self.start_location = ui.convert_point(touch.location, self)
    self.start_center = self.center
  
  def touch_moved(self, touch):
    s = self.superview.superview.superview
    s.visible_touches.append([None, ui.convert_point(touch.location, self, s), 1.0])
    if time.time() - self.start_time > .2:
      delta = ui.convert_point(touch.location, self) - self.start_location
      self.center = self.start_center + delta
      ball_id = int(self.name)
      self.superview.sync.content[ball_id][:2] = self.center
      self.superview.sync.update_others()
      
  def touch_ended(self, touch):
    ball_id = int(self.name)
    if time.time() - self.start_time < .2:
      del self.superview.sync.content[ball_id]
    else:
      self.superview.sync.content[ball_id][:2] = self.center
    self.superview.sync.update_others()

class SeaOfBalls(ui.View):
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    enable(self)
    self.background_color = .3
    self.ball_views = {}
    more_b = Button(
      title='+',
      name='',
      background_color='blue', 
      tint_color='lightblue',
      font=('<system-bold>', 32))
    self.add_subview(more_b)
    more_b.dock.bottom_trailing()
    more_b.at.width == 40
    more_b.at.height == 40
    more_b.corner_radius = 20
    more_b.action = self.add_ball
    self.sync = tinysync.Sync(
      {},
      conduit=MultipeerConduit(
      #conduit=PubNubConduit(
        #sync_conf.pubnub_sub,
        #sync_conf.pubnub_pub
      ),
      change_callback=self.update_view)
      
  def will_close(self):
    self.sync.stop()
    
  def update(self):
    if time.time() > self.update_others_time:
      self.sync.update_others()
      self.update_interval = 0
    
  def add_ball(self, sender):
    s = self.superview.superview
    s.visible_touches.append([None, ui.convert_point(sender.center, self, s), 1.0])
    ball_id = random.randint(1000000, 100000000)
    ball_x, ball_y = (
      random.randint(10, int(self.width)), 
      random.randint(10, int(self.height)))
    ball_color = random.choice(('red', 'blue', 'green', 'yellow', 'orange', 'cyan', 'violet', 'brown'))
    self.sync.content[ball_id] = [ball_x, ball_y, ball_color]
    self.sync.update_others()

  def update_view(self):
    needed = set(self.sync.content.keys())
    visible = set((int(id) for id in self.ball_views.keys()))
    to_remove = visible - needed
    for view_id in to_remove:
      self.remove_subview(self[str(view_id)])
      del self.ball_views[view_id]
    for view in list(self.ball_views.values()):
      id = int(view.name)
      (x,y,color) = self.sync.content[id]
      view.center = x, y
      needed.remove(id)
    for id in needed:
      (x,y,color) = self.sync.content[id]
      view = MoveableView(name=str(id), background_color=color)
      self.add_subview(view)
      self.ball_views[id] = view
      view.frame = (0,0,40,40)
      view.corner_radius = 20
      view.center = x, y



v = CloseableView(background_color=.7)

one = SeaOfBalls()
two = SeaOfBalls()
three = SeaOfBalls()
four = SeaOfBalls()

grid = GridView(pack=GridView.FILL, frame=v.bounds, flex='WH')
v.add_subview(grid)

grid.add_subview(one)
grid.add_subview(two)
grid.add_subview(three)
grid.add_subview(four)

v.present()

