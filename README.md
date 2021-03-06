# tinysync

Magic syncing of Python data structures

## Quick Start

If I take a data structure like:

    >>> data = {'my': ['data', 'structure']}
    
I can track it simply with:

    >>> data = track(data)
    
So what can I do with tracked data?

1. If I give it a name, every change gets synced to a [file](#sync-with-files) by the same name. This is handy for configuration files or similar.
1. If I give it a callback, I can update the [UI](#sync-ui) every time my data changes.
1. [Databases](#sync-to-database): Persisting larger data sets
1. Other devices: Differential data synchronization

### Sync with files

Say you have data structure, built primarily with dicts and lists, maybe also with sets and other objects. As an example, some kind of configuration data:
  
    >>> conf = {
    ...   'endpoint': {
    ...     'protocol': 'HTTP',
    ...     'address':  'docs.python.org' },
    ...   'retry_intervals': [1, 3, 5]
    ... }
  
Give the structure to tracker with a name, and it will be persisted, by default as YAML, to a file called _name_.yaml:

    >>> conf = track(conf, 'example-config')
  
If a file already exists, `conf` will now be the structure created based on the contents of the file. Otherwise, structure given to `track` - `conf`, here - is used as the initial value and saved to file.

Use the object returned by `track` as you would have used the original structure to access and update it.

    >>> conf['retry_intervals'].append(10)

For dicts, you have the option of using attribute access (dot) syntax.

    >>> conf.endpoint.protocol
    'HTTP'

(If you do not like this option, you can turn it off - see the fine print on [dot access](#dot-access).)

All changes to the structure are automatically saved to the file. Default format for saving the structure, "safe" YAML, is easy to read and edit manually if needed:
    
    >>> with open('example-config.yaml') as f:
    ...   print(f.read())
    ...
    endpoint:
      address: docs.python.org
      protocol: HTTP
    retry_intervals:
    - 1
    - 3
    - 5
    - 10
    <BLANKLINE>
    
(As the contents of the data structure are written to file, dict keys are outputted in alphabetical order, disregarding any meaningful order I might have had when inserting the keys to the structure or when manually editing the file. Also, `<BLANKLINE>` above just means a blank line in the file. It is included in the example for doctests to work.)

Writing the whole structure to file after every change can become a performance issue. To mitigate this, tracked objects also act as context managers, only saving at the successful completion of the block:

    >>> with conf:
    ...   conf.endpoint.protocol = 'HTTPS'
    ...   conf.retry_intervals[0] = 2

Context manager blocks are also thread safe, see the [fine print](#thread-safety) for details.

YAML, while very nice for human-readable files, can also be relatively slow. You can also save in JSON, non-safe YAML, pickle and shelve formats - see instructions and the fine print in the section [Persistence options].

### Sync UI

You can use the tracked data structure as the model in the Model-View-Controller pattern, by giving `track` a callback function that is called and updates the user-visible UI View every time the data is changed.

For example, with the following 'Model' for managing user information:

    >>> user_dir = { 'regulars': set(), 'admins': set() }
    
And this 'View' callback, where the print statements update the 'UI':

    >>> def update_view(change):
    ...   if change.path == ['regulars']:
    ...     print('Number of users:', len(change.target))
    ...   if change.path == ['admins']:
    ...     print('Number of admins:', len(change.target))
    
Given to the tracker:

    >>> user_dir = track(user_dir,
    ...   change_callback=update_view)

Now whenever a 'Controller' changes the 'Model', 'View' is automatically updated:

    >>> user_dir.regulars.add("Random User")
    Number of users: 1
    >>> user_dir.admins.add("Superuser")
    Number of admins: 1
    >>> user_dir.regulars.add("Another User")
    Number of users: 2

Here are information elements provided as attributes of the single change callback argument:

* root: The object reference you gave to the `track` function.
* name: Name you gave to the `track` function, or "<No name - no persistence>" if no name was given.
* path: Path from the root of the structure to the changed part, as a list. Empty list means the root has changed. Might not correspond to the actual path used in code if your structure is not a tree.
* func_name: Name of the function used to modify the structure (`__setitem__`, `append`, etc.)
* args and kwargs: Function arguments.
* target: The part of the structure that was modified.

An example to illustrate what the target is:

    >>> family = {
    ...   'parents': {},
    ...   'siblings': []
    ... }
    >>> family = track(family, 
    ...   change_callback=catcher.cb)
    >>> family.siblings.append('Brother')
    >>> catcher.target # is the list that was appended to
    ['Brother']
 
 Note that all of these elements are direct references; you need to deepcopy them if you want to retain an unmutable snapshot.

### Sync to database

tinysync supports the following key-value store persistence options:

* [DBM](#dbm)
* [CouchDB](#couchdb)
* TBC: MongoDB
* TBC: ReminderStore (on iOS)

#### DBM

If the data structure goes larger, performance suffers if I always serialize the whole structure to file. DBM-based option assumes that the root of the structure is a dict, and only saves the branch (key) that was changed. Also, the value of a specific key is only loaded when needed. Thus the performance is improved if you can divide your large data structure into sensible chunks, and especially if you typically only access and update some of the values.

Of course, these optimizations are invisible to you as the user of the API:

    >>> large = {
    ...   'one branch': 'lots of data',
    ...   'other branch': 'even more data'
    ... }
    >>> large = track(large, 'example-dbm', 
    ...   persist=JsonDBM)
    >>> large['one branch'] # Lazily loaded
    'lots of data'
    >>> large['one branch'] = 'changed data'
    ... # Saved by specific key

#### CouchDB

If your data is a "JSON-compatible dict of dicts", you can use [CouchDB](http://couchdb.apache.org) for persistence. All you need to do to get your structure saved to the cloud is to get account info from a small-use-is-free service like [Cloudant](https://cloudant.com).

    >>> my_device = track({}, 'tinysync_demo', persist=CouchDB)
    
CouchDB needs a server address and a database name. These can be provided as a full url to `track`, including the database name as well, i.e. 'https://username:password@host:port/database_name'. Or give just the database name to `track`, like in the example above, and provide the server address in one of the following ways, in the order of precedence:

1. Class attribute `CouchDB.server_address`
2. Environment variable `COUCHDB_URL`
3. Or rely on the non-authenticated CouchDB standard `localhost:5984`.

couchdb-python is a synchronous library, which means that you need to have a network vonnection, and network delays will slow down your code.

First "level" of your data structure must be dicts, as these correspond to the documents that CouchDB expects to see. These dicts will get "polluted" by the CouchDB standard metadata elements, _id and _rev.

    >>> my_device.one = { 'data': 'first version' }
    >>> my_device.one._id
    'one'

If the database is used by others, their updates may cause per-document conflicts, which are by default resolved in the favor of the version on the server. To demonstrate this, we have someone else coming in and messing with our data:

    >>> other_device = track({}, 'tinysync_demo', persist=CouchDB)
    >>> other_device.one.data = 'second version'
    
Now if I try to update the same bit, I will have no impact, going about with my outdated data. I will first set up a callback to changes due to remote changes.

    >>> my_device_handler = handler(my_device)
    >>> def conflict(change_spec):
    ...   print('Conflict', change_spec)
    >>> my_device_handler.conflict_callback = conflict
    
Then we cause a conflict:

    >>> my_device.one.data = 'third version'
    >>> my_device.one.data  # The other guy wins
    'second version'

This is the first part of the default conflict resolution strategy, "remote wins".

If I try again, I am aligned with the server version, and my next update works just fine:

    >>> my_device.one.data = 'third version'
    >>> my_device.one.data
    'third version'

The second part of the default conflict resolution strategy is "try to fix". This means that if there is a way to apply the local change in a way that could have resulted in the same end result at the remote, we merge the two changes and apply them without fuss.

    >>> eprint('eka')
    >>> other_device.two = {'branch_one': 'their value'}
    >>> eprint('toka')
    >>> my_device.two = {'branch_two': 'my value'}
    >>> my_device.two #doctest: +ELLIPSIS
    {'_id': 'two', '_rev': '2-...', 'branch_one': 'their value', 'branch_two': 'my value'}

As a convenience method, a clean-up function is available to delete the database. Also, if you need more fine-grained control, you can access the underlying couchdb-python [Database object](https://pythonhosted.org/CouchDB/client.html#database).

    >>> cdb = my_device_handler.persist
    >>> cdb.db.name # couchdb.client.Database method
    'tinysync_demo'
    >>> cdb.clean() # Delete the database


### Sync between devices


## Fine print

Here I cover the hairy details of some of the features described in the previous section:

1. [Thread safety](#thread-safety)
2. [Dot access](#dot-access) to dict contents

### Thread safety

All methods used to access and change a tracked structure are individually thread safe. In addition, a `with` block is thread safe as a whole, i.e. it will not be pre-empted by another thread.

As a simple example, I will take a counter object:

    >>> counter = track({}, persist=False)
    
... and an obviously poorly designed counter increment operation:
    
    >>> from time import sleep
    >>> def increment_counter():
    ...   previous_value = counter['value']
    ...   new_value = previous_value + 1
    ...   sleep(.01)   # Let other threads run
    ...   counter['value'] = new_value
    
Using this operation in separate threads produces undesirable results (`run_async` is a simple decorator that launches the decorated function in a new thread):
    
    >>> @run_async
    ... def increment_unsafe():
    ...   increment_counter()
    
    >>> counter.value = 0
    >>> c1 = increment_unsafe()
    >>> c2 = increment_unsafe()
    >>> c1.join() and c2.join()
    >>> counter.value    # 1 + 1 = what?!
    1
    
If I instead use the context manager, we get the desired results:
    
    >>> @run_async
    ... def increment_safe():
    ...   with counter:          # <-- This
    ...     increment_counter()
    
    >>> counter.value = 0
    >>> c1 = increment_safe()
    >>> c2 = increment_safe()
    >>> c1.join() and c2.join()
    >>> counter.value    # Back to regular math
    2

### Dot access

As accessing dict items with the attribute-access-like dot notation is not for eveyone (see [discussion](http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python)), you can turn the feature off, globally. This is done on class level, so you have to do it before starting to track a structure:

    >>> dot_off()
    >>> vanilla_access = track({}, persist=False)
    >>> vanilla_access['test'] = 'value'
    >>> hasattr(vanilla_access, 'test')
    False
    
To turn the dot access feature back on (you guessed it):

    >>> dot_on()
    
If you like dot access in general but have a specific case where it is problematic - e.g. a conflict with another package - you can turn it off for a single structure:

    >>> special_case = track({}, persist=False,
    ...   dot_access=False)
    >>> special_case['test'] = 'value'
    >>> hasattr(special_case, 'test')
    False
    

## Feature summary

* Understands and wraps lists (MutableSequence), dicts (MutableMapping) and sets (MutableSet).
* Detects and reports changes to any part of the structure.
* Records the overall changed area of the structure, to provide more efficient diffing of large structures.
* Supports diff, patch and revert (using dictdiffer applied to tracked objects)
* Tracked objects can be used as context managers to control when changes are saved and to make a set of changes transactional (all saved successfully or no change to original object)
* Limited pollution of regular data structures:
  * Tracker data: `_tracker`
  * From ProxyTypes: `type`, `__subject__`
  * Context manager: `__enter__`, `__exit__`
  
## Persistence options
  
## Examples
    
    >>> lst = [1, 2]
    >>> tracked_list = track(lst, persist=False, 
    ...   change_callback=catcher.cb)
  
catcher.cb is a test change callback which simply records the latest change information:

    >>> tracked_list.append(3)
    >>> assert catcher.func_name == 'append'
  
Tracked object looks like the original object, except for its type

    >>> assert isinstance(tracked_list, list)
    >>> assert type(tracked_list) == ListWrapper
