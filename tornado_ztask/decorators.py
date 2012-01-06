import logging
from functools import wraps
import types

import zmq

logger = logging.getLogger('ztaskd')

ZTASKD_DISABLED = False
ZTASKD_ALWAYS_EAGER = False
def task():
    try:
        from zmq import PUSH
    except:
        from zmq import DOWNSTREAM as PUSH
    def wrapper(func):
        function_name = '%s.%s' % (func.__module__, func.__name__)
        
        logger.info('Registered task: %s' % function_name)
        
        context = zmq.Context()
        socket = context.socket(PUSH)
        socket.connect("tcp://127.0.0.1:5000")
        
        @wraps(func)
        def _func(*args, **kwargs):
            after = kwargs.pop('after', 0)
            socket.send_pyobj((function_name, args, kwargs, after, ))
        
        def _func_after(after, *args, **kwargs):
            _func(after=after, *args, **kwargs)
        
        setattr(func, 'async', _func)
        setattr(func, 'after', _func_after)
        return func
    
    return wrapper