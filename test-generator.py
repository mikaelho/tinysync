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

server = tinysync.logic.ServerConnectivity()

db_ids = ('1','2','3')
dbs = []
for db_id in db_ids:
  #db = tinysync.TinySyncDB('test' + db_id + '.json', server = server)
  db = tinysync.TinySyncDB(server = server)
  db.name = 'db' + db_id
  db.purge_table('_default')
  dbs.append(db)

fake = faker.Faker()
fakers = (fake.pystr, fake.pydict, fake.pyint, fake.pyfloat, fake.pylist)

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
  db.insert(make_safe(fake.pydict()))

def at_random_location(db, content):
  elems = list(db.all())
  elem = curr_elem = fake.random_element(elems)
  id = elem.eid
  key = fake.random_element(elem.keys())
  while True:
    if random.random() < 0.5:
      curr_elem[key] = content
      break
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

for i in xrange(100000):
  print '#'+str(i),
  db = fake.random_element(dbs)
  func = None
  if len(db) == 0:
    func = insert
  else:
    func = fake.random_element(actions)
  print ' ' + db.name + ' ' + func.__name__,
  func(db)
  #print '#' + str(i) + ': ' + db.name + ' - ' + str(len(db))
  start_time = time.time()
  db.sync()
  delta_time = time.time() - start_time
  print ' ' + str(len(db.logic.prev_value.keys())) + ' items, size ' + str(len(json.dumps(db.logic.prev_value)))
  #print ' ' + str(delta_time) + ' sec'
  #print status_str
  if i%20 == 0: console.clear()
