# coding: utf-8

import unittest
import unittest.mock as mock
from functools import partial
import copy, time, threading

from tinysync import track, istracked, atomic, NoNameNoPersistence, handler
from tinysync.sync import QueueControl, queued
from tinysync.conduit.conduit import MemoryConduit


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


class TestHistory(unittest.TestCase):
    
    def test_history(self):
        data = track({}, history=True)
        h = handler(data).history
        data['a'] = 5
        data['a'] = [1, 2]
        self.assertTrue(h.capacity == 0)
        self.assertTrue(len(h) == 2)
        self.assertTrue(h.undo() == 1)
        self.assertTrue(h.active == 1)
        self.assertTrue(data['a'] == 5)
        self.assertTrue(h.redo() == 0)
        self.assertTrue(data['a'] == [1, 2])

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
        original = {'a': {'b': 1}}
        call_count = 0
        def cb(data):
            nonlocal call_count
            call_count += 1
        t = track(copy.deepcopy(original), change_callback=cb)
        with self.assertRaises(RuntimeError):
            with atomic(t):
                t['a']['b'] = [2, 3]
                raise RuntimeError('Something failed')
        self.assertTrue(t['a']['b'] == 1, t['a']['b'])
        self.assertTrue(t == original, t)
        self.assertTrue(istracked(t['a']))
        self.assertTrue(call_count == 0, call_count)
        

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
    
    
class TestQueueControl(unittest.TestCase):
    
    def test_queued_tasks(self):
        
        class TestQueue(QueueControl):
            
            result = ''
            
            @queued
            def func(self, sleep_time, data):
                time.sleep(sleep_time)
                self.result += data
                
            @queued
            def failing_func(self):
                raise Exception('Intentional fail')
        
        tester = TestQueue()
        with self.assertLogs(level='ERROR') as cm:
            t1 = threading.Thread(target=partial(tester.func, 0.2, 'one'))
            t2 = threading.Thread(target=partial(tester.func, 0.1, 'two'))
            t1.start()
            tester.failing_func()
            t2.start()
            tester.stop()
            tester.queue_thread.join()
            self.assertTrue(
                cm.output[0].startswith('ERROR:root:Intentional fail'), 
                cm.output[0])
        self.assertTrue(tester.result == 'onetwo')
    
    
class TestSync(unittest.TestCase):
    
    def test_baseline_memory_sync(self):
        data1 = track({}, sync=MemoryConduit())
        data2 = track({}, sync=MemoryConduit())
        
        data1['a'] = 1
        
        time.sleep(0.1)
        handler(data1).sync.stop()
        handler(data2).sync.stop()
        
        self.assertTrue(data1 == data2)
    

if __name__ == "__main__":
    unittest.main()
