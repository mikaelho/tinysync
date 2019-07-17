import tinysync

# coding: utf-8
import random
import json
import time

import faker
import tinysync
#from tinysync.conduit.memory import MemoryConduit
from tinysync.conduit.pubnub import PubNubConduit
import dictdiffer
from decimal import Decimal
from datetime import datetime
import console

import sync_conf

data_ids = ('A','B', 'C')
datas = []
for data_id in data_ids:
  data = tinysync.Sync(initial_value=[], #conduit=PubNubConduit(
  #  sync_conf.pubnub_sub,
  #  sync_conf.pubnub_pub)
  )
  datas.append(data)
  
fake = faker.Faker()
fakers = (lambda: {}, fake.pyint, lambda: [])

class ComplexEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal) or isinstance(obj, datetime):
      return str(obj)
    return json.JSONEncoder.default(self, obj)

def make_safe(content):
  ''' Use the custom encoder to replace non-json-serializable items with their str versions '''
  json_content = json.dumps(content, cls=ComplexEncoder)
  return json.loads(json_content)

def random_content():
  return make_safe(fake.random_element(fakers)())

def insert(data):
  #print 'insert'
  data.append(make_safe({fake.pystr()[:3]: fake.pyint()}))

def at_random_location(data, content):
  elem = curr_elem = fake.random_element(data)
  key = fake.random_element(list(elem.keys()))
  while True:
    if random.random() < 0.3:
      curr_elem[key] = content
      break
    elif random.random() < 0.2:
      try:
        curr_elem[fake.pystr()[:3]] = content
        break
      except: pass
    try:
      key = fake.random_element(curr_elem.keys)
    except:
      curr_elem[key] = content
      break
    curr_elem = curr_elem[key]

def update(data):
  #print 'update'
  at_random_location(data, random_content())
  
def remove(data):
  #print 'remove'
  elem = fake.random_element(data)
  data.remove(elem)

actions = (insert, update, update, update, remove, remove)
#actions = (insert, update, update, update, update, update, remove)

for i in range(100):
  print('#'+str(i), end=' ')
  input()
  data = fake.random_element(datas)
  func = None
  if len(data.content) == 0:
    func = insert
  else:
    func = fake.random_element(actions)
  print(f' {func.__name__}', end=' ')
  func(data.content)
  print(data.content)
  #print '#' + str(i) + ': ' + db.name + ' - ' + str(len(db))
  #start_time = time.time()
  data.update_others()
  #delta_time = time.time() - start_time
  #print(' ' + str(len(list(db.logic.prev_value.keys()))) + ' items, size ' + str(len(json.dumps(db.logic.prev_value))))
  #print(data.content)
  #print ' ' + str(delta_time) + ' sec'
  #print status_str
  #if i%20 == 0: console.clear()
  for i, data in enumerate(datas):
    print(data.conduit.node_id[:8], data.content)
  
'''
for db in dbs:
  db.sync()
for db in dbs:
  db.sync()
for db in dbs:
  print(db.name + ' ' + str(db.all()))
'''

