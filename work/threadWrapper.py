import threading
import inspect
import ctypes
import time

# https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
def _async_raise(tid, exctype):
    if not inspect.isclass(exctype):
        raise TypeError("Only types can be raised (not instances)")
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid),
                                                  ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")

# https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
class ThreadWithExc(threading.Thread):
    def _get_my_tid(self):

        if not self.is_alive():
            raise threading.ThreadError("the thread is not active")

        if hasattr(self, "_thread_id"):
            return self._thread_id

        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

        raise AssertionError("could not determine the thread's id")

    def stop(self, exctype=SystemExit):
        _async_raise(self._get_my_tid(), exctype )

def work():
    try:
        while True:
            print('work')
            time.sleep(1)
    except SystemExit:
        pass

    print('exiting work() function')

if __name__ == '__main__':

    class demo(ThreadWithExc):
        def __init__(self):
            threading.Thread.__init__(self)
            print("start!")

        def run(self):
            try:
                while True:
                    print('work')
                    time.sleep(1)
            except Exception as e:
                print("error: {}".format(e))
            except SystemExit: pass
            print('exiting work() function')
    
    mydemo = demo()
    mydemo.start()
    mydemo.stop(ValueError)
    mydemo.join()
#    t = ThreadWithExc(target=work)
#    t.start()
#    t.stop()
#    t.join()
'''
class Server:
    class ThreadStopped(Exception): pass

    def __init__(self):
        self.thread = ThreadWithExc(target=work)

    def start(self):
        self.thread.start()

    def stop(self):
#        _async_raise(self.thread.raiseExc(TypeError))
        self.thread.raiseExc(self.ThreadStopped)

server = Server()
server.start()
server.stop()
'''
