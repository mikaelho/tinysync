# tinysync

## Use Cases

Sync Python dicts and other data structures to:

1. File: Configuration files and similar
2. Database: Persisting larger data sets
1. UI: Reacting to changes in data model
1. Another device: Differential data synchronization

### Sync with files

Say you have data structure, built primarily with dicts and lists, maybe also with sets and other objects. As an example, some kind of configuration data:
  
    >>> default_conf = {
    ...   'endpoint': {
    ...     'protocol': 'HTTP',
    ...     'address':  'docs.python.org' },
    ...   'retry_intervals': [1, 3, 5]
    ... }
  
Give the structure to tracker with a name, and it will be persisted, by default as YAML, to a file called _name_.yaml:

    >>> conf = track(default_conf, 'example-config')
  
If a file already exists, `conf` will now be the structure created based on the contents of the file. Otherwise, structure given to `track` - `default_conf` in the example - is used as the initial valie and saved to file.

Use the object returned by `track` as you would have used the original structure to access and update it.

    >>> conf['retry_intervals'].append(10)

For dicts, you have the option of using attribute access (dot) syntax.

    >>> conf.endpoint.protocol
    'HTTP'

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
    
(`<BLANKLINE>` above just means a blank line in the file. It is included in the example for doctests to work.)

Writing the whole structure to file after every change can become a performance issue. To mitigate this, tracked objects also act as context managers, only saving at the successful completion of the block:

    >>> with conf:
    ...   conf.endpoint.protocol = 'HTTPS'
    ...   conf.retry_intervals[0] = 2

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
    
Given to the tracker (not bothering to save changes to file, in this example):

    >>> user_dir = track(user_dir, 'user directory', callback=update_view, persist=False)

Now whenever a 'Controller' changes the 'Model', 'View' is automatically updated:

    >>> user_dir.regulars.add("Random User")
    Number of users: 1
    >>> user_dir.admins.add("Superuser")
    Number of admins: 1
    >>> user_dir.regulars.add("Another User")
    Number of users: 2

Note that if you use the context manager and make several changes to the structure, there will only be one change notification where the parameter is a list of change data objects.

Here are information elements provided as attributes of the single change callback argument:
 
* root: The object reference you gave to the `track` function.
* name: Name you gave to the `track` function.
* path: Path from the root of the structure to the changed part, as a list. Empty list means the root has changed. Might not correspond to the actual path used in code if your structure is not a tree.
* func_name: Name of the function used to modify the structure (`__setitem__`, `append`, etc.)
* args and kwargs: Function arguments.
* target: The part of the structure that was modified. For example:

    >>> family = track({
    ...   'parents': {},
    ...   'siblings': []
    ... }, 'family', callback=catcher.cb, persist=False)
    >>> family.siblings.append('Brother')
    >>> catcher.target # is the list that was appended to
    ['Brother']
 
 Note that all of these elements are direct references; you need to deepcopy them if you want to retain an unmutable snapshot.

    {'args': ('admin', 'Administrator'),
     'func_name': '__setitem__',
     'kwargs': {},
     'name': 'user directory',
     'path': [],
     'root': {'admin': 'Administrator'},
     'target': {'admin': 'Administrator'}}




### Sync between devices

## Features

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
    >>> tracked_list = track(lst, callback=catcher.cb)
  
catcher.cb is a test change callback which simply records the latest change information:

    >>> tracked_list.append(3)
    >>> assert catcher.func_name == 'append'
  
Tracked object looks like the original object, except for its type

    >>> assert isinstance(tracked_list, list)
    >>> assert type(tracked_list) == ListWrapper
