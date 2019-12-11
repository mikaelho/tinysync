'''
Synchronization visualizer that only works on the Pythonista app on iOS devices.

Requires additional modules:
  * PubNub client libraries
  * anchor module for layout
  * multipeer module for device-to-device conduit
'''

import random, functools, time

from ui import *
from anchor import *
from objc_util import on_main_thread

import tinysync
#from tinysync.conduit.conduit import MemoryConduit



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
            
            with open('logging.txt', 'a') as fp:
                fp.write('update loc\n')
            self.superview.balls[ball_id].center = tuple(self.center)
            #self.superview.sync.update_others()

    def touch_ended(self, touch):
        ball_id = int(self.name)
        if time.time() - self.start_time < .2:
            del self.superview.balls[ball_id]
        else:
            self.superview.balls[ball_id].center = tuple(self.center)
        #self.superview.sync.update_others()

class SeaOfBalls(ui.View):

    def __init__(self, conduit=None, **kwargs):
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

        self.balls = tinysync.track({},
          name='balls',
          persist=False, sync=conduit,
          change_callback=self.update_view,
          dot_access=True)

    def will_close(self):
        tinysync.handler(self.balls).sync.stop()

    def to_file(self, msg):
        pass
        #with open('logging.txt', 'a') as fp:
            #fp.write(f'{tinysync.handler(self.balls).sync.conduit.node_id[:3]} - {msg}\n')

    def add_ball(self, sender):
        s = self.superview.superview
        s.visible_touches.append([None, ui.convert_point(sender.center, self, s), 1.0])
        ball_id = random.randint(1000000, 100000000)
        ball_x, ball_y = (
          random.randint(10, int(self.width)),
          random.randint(10, int(self.height)))
        ball_color = random.choice(('red', 'blue', 'green', 'yellow', 'orange', 'cyan', 'violet', 'brown'))

        self.to_file('add ball')

        self.balls[ball_id] = { 'center': (ball_x, ball_y), 'color': ball_color }

    @on_main_thread
    def update_view(self, data):
        self.to_file('update view')
        
        with self.balls:
            needed = set(self.balls.keys())
            visible = set((int(id) for id in self.ball_views.keys()))
            to_remove = visible - needed
            for view_id in to_remove:
                self.remove_subview(self[str(view_id)])
                del self.ball_views[view_id]
            for view in list(self.ball_views.values()):
                id = int(view.name)
                view.center = self.balls[id].center
                needed.remove(id)
            for id in needed:
                ball = self.balls[id]
                view = MoveableView(name=str(id), background_color=ball.color)
                self.add_subview(view)
                self.ball_views[id] = view
                view.frame = (0,0,40,40)
                view.corner_radius = 20
                view.center = ball.center

if __name__ == '__main__':
    
    #with open('logging.txt', 'w') as fp:
    #    fp.write('START\n')
        

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

