# coding: utf-8

import unittest
import unittest.mock as mock
from functools import partial
import copy

from tinysync import track, istracked, atomic, NoNameNoPersistence


class TestBasics(unittest.TestCase):

    def test_basics_list(self):
        l = [0, 1]
        t = track(l)
        self.assertTrue(istracked(t))
        self.assertTrue(t.__subject__ == l)
        t[1] = ['a']
        self.assertTrue(istracked(t[1]))
        
    def test_basics_dict(self):
        d = {'a': 1, 'b': 2}
        t = track(d)
        self.assertTrue(istracked(t))
        self.assertTrue(t.__subject__ == d)
        t['b'] = [3]
        self.assertTrue(istracked(t['b']))
        
    def test_basics_set(self):
        s = {'a', 'b'}
        t = track(s)
        self.assertTrue(istracked(t))
        self.assertTrue(t.__subject__ == s)
        
    def test_vanilla_copy(self):
        l = [0, { 'a': 1 }]
        t = track(l)
        back_to_l = copy.deepcopy(t)
        self.assertTrue(type(back_to_l) == list)
        self.assertTrue(type(back_to_l[1]) == dict)
        

class TestChangeCallbacks(unittest.TestCase):
        
    def test_change_callback(self):
        l = [0, [1]]
        def change_callback(data):
            self.assertTrue(type(data.name) == NoNameNoPersistence)
            self.assertTrue(data.path == [1])
            self.assertTrue(data.target==l[1])
        t = track(l, change_callback=change_callback)
        t[1][0] = 2


class TestContextManagers(unittest.TestCase):
    
    def test_lock_ctxtmgr(self):
        t = track({'a': 1})
        with t:
            t._tracker.handler.lock.release()
            t._tracker.handler.lock.acquire()
        with self.assertRaises(RuntimeError):
            t._tracker.handler.lock.release()
            
    def test_atomic_ctxtmgr_baseline(self):
        t = track({'a': 1})
        with atomic(t):
            t['a'] = { 'b': [2, 3]}
        self.assertTrue(t['a']['b'][1] == 3)
        self.assertTrue(istracked(t['a']['b']))
        
    def test_atomic_ctxtmgr_exception(self):
        original = {'a': 1}
        t = track(copy.deepcopy(original))
        with self.assertRaises(RuntimeError):
            with atomic(t):
                t['a'] = { 'b': [2, 3]}
                raise RuntimeError('Something failed')
        self.assertTrue(t['a'] == 1)
        self.assertTrue(t == original)
        self.assertTrue(istracked(t))
        

class TestPersistence(unittest.TestCase):
    
    def test_new_file(self):
        m = mock.mock_open()
        with mock.patch('tinysync.persistence.open', m):
            t = track({'ä': 1}, 'testing')
        m.assert_any_call('testing.yaml', encoding='utf-8')
        m.assert_called_with('testing.yaml', 'w', encoding='utf-8')
        h = m()
        [h.write.assert_any_call(letter) for letter in 'ä: 1\n']
        
    def test_existing_file(self):
        file_content = 'ä: 1\n'
        m = mock.mock_open(read_data=file_content)
        with mock.patch('tinysync.persistence.open', m):
            t = track({}, 'testing')
        m.assert_called_once_with('testing.yaml', encoding='utf-8')
        self.assertTrue(t['ä'] == 1)
    
    
class TestSync(unittest.TestCase):
    pass
    

if __name__ == "__main__":
    unittest.main()
