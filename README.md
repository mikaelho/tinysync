# tinysync

## Use Cases

Sync Python dicts and other data structures to:

1. File: Configuration files, keyed storage
1. UI: Reacting to changes in data model
1. Another device: Differential data synchronization

### Sync with files

Define structure with default values:
  
  >>> default_conf = {
  ...   'endpoint': {
  ...     'protocol': 'HTTP',
  ...     'address':  'docs.python.org' },
  ...   'retry_intervals': [1, 3, 5]
  ... }
  
Give it to tracker with a name, and it will be persisted, by default as YAML, to a file called '<name>.yaml':

  >>> from tracker import *
  >>> conf = track(default_conf, 'config')
  
Use the resulting object to access and update the data structure. All changes to the structure are automatically saved to the file. For dicts, you have the option of using attribute access (dot) syntax.

  >>> conf['retry_intervals'].append(10)
  >>> conf.endpoint.protocol
  'HTTP'
  
Default YAML format is nicely accessible if you want to directly edit the file. You can also use JSON, non-safe YAML and pickle - see instructions and fine print in the section Persistence options.

### Sync UI

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
  
## Examples
    
    >>> lst = [1, 2]
    >>> tracked_list = track(lst, callback=catcher.cb)
  
catcher.cb is a test change callback which simply records the latest change information:

    >>> tracked_list.append(3)
    >>> assert catcher.func_name == 'append'
  
Tracked object looks like the original object, except for its type

    >>> assert isinstance(tracked_list, list)
    >>> assert type(tracked_list) == ListWrapper
