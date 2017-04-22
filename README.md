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

    >>> conf = track(default_conf, 'example-config')
  
Use the resulting object to access and update the data structure. All changes to the structure are automatically saved to the file. For dicts, you have the option of using attribute access (dot) syntax.

    >>> conf['retry_intervals'].append(10)
    >>> conf.endpoint.protocol
    'HTTP'

Writing the whole structure to file after every change can become a performance issue. To mitigate this, tracked objects also act as context managers, only saving at the successful completion of the block:

    >>> with conf:
    ...   conf.endpoint.protocol = 'HTTPS'
    ...   conf.retry_intervals[0] = 2
    
Default safe YAML format is easy to read and update if you want to directly edit the file:
    
    >>> with open('example-config.yaml') as f:
    ...   print(f.read())
    ...
    endpoint:
      address: docs.python.org
      protocol: HTTPS
    retry_intervals:
    - 2
    - 3
    - 5
    - 10
    <BLANKLINE>
    
(Note: '<BLANKLINE>' above just means a blank line in the file. It is included in the example for doctest to work.)

Structures can contain dicts, lists, sets and random objects. You can also save in JSON, non-safe YAML and pickle formats - see instructions and the fine print in the section [Persistence options].

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
