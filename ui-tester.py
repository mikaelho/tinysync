from ui import *
from anchor import *
import tinysync
import random, functools

class MoveableView(ui.View):
  
  def touch_moved(self, touch):
    delta = touch.location - touch.prev_location
    self.center += delta
    x,y = self.center
    id = int(self.name)
    moving_balls[id][0] = x
    moving_balls[id][1] = y

moving_balls = {}

v = View(background_color='black')

active = View(background_color=.1)
passive = View(background_color=.1)

v.add_subview(active)
v.add_subview(passive)

active.dock.bottom(share=.45)
passive.dock.top(share=.45)

def add_ball(sender):
  ball_id = random.randint(1000000, 100000000)
  ball_x, ball_y = (
    random.randint(10, int(active.width)), 
    random.randint(10, int(active.height)))
  ball_color = random.choice(('red', 'blue', 'green', 'yellow', 'orange', 'cyan', 'violet', 'brown'))
  moving_balls[ball_id] = [ball_x, ball_y, ball_color]
  update_view(active)
  
def update_view(container):
  needed = set(moving_balls.keys())
  visible = set((int(view.name) for view in container.subviews))
  to_remove = visible - needed
  for view_id in to_remove:
    container.remove_subview(container[str(view_id)])
  for view in container.subviews:
    id = int(view.name)
    (x,y,color) = moving_balls[id]
    view.center = x, y
    needed.remove(id)
  for id in needed:
    (x,y,color) = moving_balls[id]
    view = MoveableView(name=str(id), background_color=color)
    container.add_subview(view)
    view.frame = (0,0,40,40)
    view.corner_radius = 20
    view.center = x, y

more_b = Button(title='+', background_color='blue', tint_color='lightblue', font=('<system-bold>', 32))
v.add_subview(more_b)
more_b.dock.bottom_trailing()
more_b.at.width == 40
more_b.at.height == 40
more_b.corner_radius = 20
more_b.action = add_ball

v.present()

moving_balls = tinysync.track(
  moving_balls, 
  change_action=
  functools.partial(update_view, passive))
