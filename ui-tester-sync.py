from ui import *
from anchor import *
import tinysync
import random, functools, time

class MoveableView(ui.View):
  
  def touch_began(self, touch):
    self.start_time = time.time()
  
  def touch_moved(self, touch):
    if time.time() - self.start_time > .2:
      delta = touch.location - touch.prev_location
      self.center += delta
      x,y = self.center
      id = int(self.name)
      self.superview.sync.content[id][0] = x
      self.superview.sync.content[id][1] = y
      self.superview.sync.update_others()
      
  def touch_ended(self,touch):
    if time.time() - self.start_time < .2:
      id = int(self.name)
      del self.superview.sync.content[id]
      self.superview.sync.update_others()

class SeaOfBalls(ui.View):
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    enable(self)
    self.background_color = .3
    self.ball_views = {}
    #self.ball_data = {}
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
      change_callback=self.update_view)
    
  def add_ball(self, sender):
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
    for view in self.ball_views.values():
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



v = View(background_color=.7)

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

'''
moving_balls = tinysync.track(
  moving_balls, 
  change_action=
  functools.partial(update_view, passive))
'''
