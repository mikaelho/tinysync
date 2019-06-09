import tinysync

# coding: utf-8
import random
import json
import time

import faker
import tinydb
import tinysync
import dictdiffer
from decimal import Decimal
from datetime import datetime
import console

data_ids = ('A','B', 'C')
datas = []
for data_id in data_ids:
  db = tinysync.TinySyncDB(server = server)
  db.name = 'db' + db_id
  db.purge_table('_default')
  dbs.append(db)
  data = ...

fake = faker.Faker()
#fakers = (fake.pystr, fake.pydict, fake.pyint, fake.pyfloat, fake.pylist)
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

def insert(db):
  #print 'insert'
  db.insert(make_safe({fake.pystr()[:3]: fake.pyint()}))

def at_random_location(db, content):
  elems = list(db.all())
  elem = curr_elem = fake.random_element(elems)
  id = elem.eid
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
  db.update(elem, eids=[id])

def update(db):
  #print 'update'
  at_random_location(db, random_content())
  
def remove(db):
  #print 'remove'
  elems = list(db.all())
  elem = fake.random_element(elems)
  db.remove(eids=[elem.eid])

actions = (insert, update, update, update, remove, remove)
#actions = (insert, update, update, update, update, update, remove)

for db in dbs: db.purge()

for i in range(10):
  print('#'+str(i), end=' ')
  input()
  db = fake.random_element(dbs)
  func = None
  if len(db) == 0:
    func = insert
  else:
    func = fake.random_element(actions)
  print(' ' + db.name + ' ' + func.__name__, end=' ')
  func(db)
  print(db.all())
  #print '#' + str(i) + ': ' + db.name + ' - ' + str(len(db))
  #start_time = time.time()
  db.sync()
  #delta_time = time.time() - start_time
  print(' ' + str(len(list(db.logic.prev_value.keys()))) + ' items, size ' + str(len(json.dumps(db.logic.prev_value))))
  print(db.all())
  #print ' ' + str(delta_time) + ' sec'
  #print status_str
  if i%20 == 0: console.clear()
  
for db in dbs:
  db.sync()
for db in dbs:
  db.sync()
for db in dbs:
  print(db.name + ' ' + str(db.all()))

