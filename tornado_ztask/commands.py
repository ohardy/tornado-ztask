#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding: utf-8
"""
server.py

Created by Olivier Hardy on 2011-10-10.
Copyright (c) 2011 Olivier Hardy. All rights reserved.
"""

import os
import sys
import pickle
import urlparse
import logging
import traceback
from functools import partial

from datetime import date, datetime, time, timedelta

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado import autoreload

from tornado import gen

from tornado.web import url

from tornado.reloaded.management import Command

from tornado.options import options
from tornado.reloaded.db import get_db

from tornado.reloaded.utils import get_module_from_import

import zmq
from tornado.ioloop import IOLoop
from zmq.eventloop.ioloop import ZMQPoller

ZTASKD_RETRY_COUNT = 10
ZTASKD_RETRY_AFTER = 30

class ZTaskdCommand(Command):
    """docstring for ServerCommand"""
    name       = 'ztaskd'
    ioloop     = None
    func_cache = {}
    
    def add_arguments(self, subparser):
        pass
    
    def handle(self, replay_failed=False):
        """docstring for handle"""
        
        self.ioloop = IOLoop(ZMQPoller())
        self.ioloop.install()
        
        context = zmq.Context()
        socket  = context.socket(zmq.PULL)
        socket.bind("tcp://127.0.0.1:5000")
        
        self.db = get_db()
        
        def install_queue_handler(ioloop):
            def _queue_handler(socket, *args, **kwargs):
                try:
                    function_name, args, kwargs, after = socket.recv_pyobj()
                    if function_name == 'ztask_log':
                        logging.warn('%s: %s' % (args[0], args[1]))
                        return
                    
                    datetime.combine(date.today(), time()) + timedelta(hours=1)
                    
                    self.db.ztask.insert({
                        'function_name' : function_name,
                        'args'          : pickle.dumps(args),
                        'kwargs'        : pickle.dumps(kwargs),
                        'retry_count'   : 0,
                        'next_attempt'  : datetime.combine(date.today(), time()) + timedelta(seconds=after)
                    }, callback=self._on_insert)
                
                except Exception, e:
                    logging.error('Error setting up function. Details:\n%s' % e)
                    traceback.print_exc(e)
            
            ioloop.add_handler(socket, _queue_handler, ioloop.READ)
        
        # Reload tasks if necessary
        cursor = None
        
        if replay_failed:
            cursor = self.db.ztask.find()
        else:
            cursor = self.db.ztask.find()
        
        if cursor is not None:
            cursor.loop(callback=self._on_select)
        
        install_queue_handler(self.ioloop)
        
        if 0:#options.debug:
            from tornado import autoreload
            autoreload.add_reload_hook(partial(install_queue_handler, self.ioloop))
            autoreload.start(io_loop=self.ioloop)
        
        self.ioloop.start()
    
    @gen.engine
    def _call_function(self, task_id):
        try:
            response = yield gen.Task(self.db.ztask.find_one, {'_id' : task_id})
            
            if response:
                function_name = response['function_name']
                args          = pickle.loads(str(response['args']))
                kwargs        = pickle.loads(str(response['kwargs']))
                
                if response['retry_count'] >= ZTASKD_RETRY_COUNT:
                    logger.error('Retry count exceeded')
                    return
            
            else:
                logging.info('Count not get task with id %s:%s' % (task_id, response, ))
                return
            
            logging.info('Calling %s' % (function_name, ))
            
            if function_name not in self.func_cache:
                self.func_cache[function_name] = get_module_from_import(function_name)
            
            function = self.func_cache[function_name]
            
            function(*args, **kwargs)
            logging.info('Called %s successfully' % function_name)
            response = yield gen.Task(self.db.ztask.remove, {'_id' : task_id})
        except Exception as e:
            logging.error(e)
            
            self.db.ztask.update({
                    '_id' : task_id
                }, {
                    '$inc' : {
                        'retry_count' : 1
                    },
                    '$push' : {
                        'logs' : {
                            'failed' : datetime.utcnow(),
                            'last_exception' : '%s' % (e, )
                        }
                    },
                    '$set' : {
                        'next_attempt' : datetime.combine(date.today(), time()) + timedelta(seconds=ZTASKD_RETRY_AFTER)
                    }
                }, callback=self._on_insert)
            
            traceback.print_exc(e)
    
    def _on_insert(self, response):
        """docstring for _on_insert"""
        if response:
            self.ioloop.add_timeout(timedelta(seconds=1), lambda: self._call_function(response))
    
    def _on_select(self, response):
        """docstring for _on_select"""
        for task in response:
            if task['next_attempt'] < datetime.combine(date.today(), time()):
                self.ioloop.add_timeout(timedelta(seconds=5), lambda: self._call_function(task['_id']))
            else:
                after = task['next_attempt'] - datetime.combine(date.today(), time())
                self.ioloop.add_timeout(after, lambda: self._call_function(task['_id']))
            