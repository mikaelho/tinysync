import unittest
from functools import partial
import copy

from tinysync import track, istracked, NoNameNoPersistence


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
    
    def test_change_action(self):
        l = [0, 1]
        check = []
        def change_action(check):
            check.append(True)
        t = track(l, change_action=partial(change_action, check))
        t[1] = 2
        self.assertTrue(check[0])
        
    def test_change_callback(self):
        l = [0, [1]]
        def change_callback(data):
            self.assertTrue(type(data.name) == NoNameNoPersistence)
            self.assertTrue(data.path == [1])
            self.assertTrue(data.target==l[1])
            self.assertTrue(data.func_name=='__setitem__')
            self.assertTrue(data.args == (0, 2))
        t = track(l, change_callback=change_callback)
        t[1][0] = 2


if __name__ == "__main__":
    unittest.main()
