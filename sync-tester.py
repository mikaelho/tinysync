import tinysync

# coding: utf-8
import random
import json
import time

import faker
import tinysync
#from tinysync.conduit.memory import MemoryConduit
#from tinysync.conduit.pubnub import PubNubConduit
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

for i in range(1000):
  print('#'+str(i), end=' ')
  #input()
  data = fake.random_element(datas)
  func = None
  if len(data.content) == 0:
    func = insert
  else:
    func = fake.random_element(actions)
  #print(f' {func.__name__}', end=' ')
  func(data.content)
  #print(data.content)
  #print '#' + str(i) + ': ' + db.name + ' - ' + str(len(db))
  #start_time = time.time()
  data.update_others()
  #delta_time = time.time() - start_time
  #print(' ' + str(len(list(db.logic.prev_value.keys()))) + ' items, size ' + str(len(json.dumps(db.logic.prev_value))))
  #print(data.content)
  #print ' ' + str(delta_time) + ' sec'
  #print status_str
  #if i%20 == 0: console.clear()

  #print('-'*20)
  matching_baseline = None
  matching_checksum = None
  for data in datas:
    nid = data.conduit.node_id
    #print(nid[:8], data.content)
    for partner in data.edits:
      if len(data.edits[partner]) > 1:
        print('PROBLEM -', nid[:8])
      if matching_baseline is None:
        matching_baseline = data.baseline[partner]
        matching_checksum = data.edits[partner][-1][0]
      else:
        if data.baseline[partner] != matching_baseline:
          print('BASELINE problem -', nid[:8])
        if data.edits[partner][-1][0] != matching_checksum:
          print('CHECKSUM problem -', nid[:8])
  if i % 20 == 1:
    console.clear()
        
        
  
'''
for db in dbs:
  db.sync()
for db in dbs:
  db.sync()
for db in dbs:
  print(db.name + ' ' + str(db.all()))
'''

