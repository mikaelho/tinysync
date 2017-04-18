# Use Cases

Simple syncing of Python data structures to file, to UI, or to another device.

* To file: 
* To UI: 
* To another device: 

* Effortless access and updates to structured data, like a configuration file
* Tracking and reacting to changes to large data structures

# Features

* Understands and wraps lists (MutableSequence), dicts (MutableMapping) and sets (MutableSet).
* Detects and reports changes to any part of the structure.
* Records the overall changed area of the structure, to provide more efficient diffing of large structures.
* Supports diff, patch and revert (using dictdiffer applied to tracked objects)
* Tracked objects can be used as context managers to control when changes are saved and to make a set of changes transactional (all saved successfully or no change to original object)
* Limited pollution of regular data structures:
  * Tracker data: `_tracker`
  * From ProxyTypes: `type`, `__subject__`
  * Context manager: `__enter__`, `__exit__`
  
# Examples
    
    >>> from tracker import *
    >>> lst = [1, 2]
    >>> tracked_list = track(lst, callback=catcher.cb)
  
catcher.cb is a test change callback which simply records the latest change information:

    >>> tracked_list.append(3)
    >>> assert catcher.func_name == 'append'
  
Tracked object looks like the original object, except for its type

    >>> assert isinstance(tracked_list, list)
    >>> assert type(tracked_list) == ListWrapper
