#!/usr/bin/env python
#-*- coding: utf-8 -*-
# vim: set bg=dark noet sw=4 ts=4 fdm=indent : 

"""Poem Mock Client"""
__author__='chutong'

import os
import sys
import logging
try:
	import ConfigParser
except ImportError:
	import configparser as ConfigParser
from domob_thrift.omg_types.ttypes import *
from domob_thrift.omg_types.constants import *
from domob_thrift.omg.ttypes import *
from domob_thrift.omg.constants import *
from domob_thrift.omg import OmgService

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer


if  __name__ == '__main__':

	basepath = os.path.abspath(os.getcwd())
	confpath = os.path.join(basepath, 'conf/poem.conf')
	conf = ConfigParser.RawConfigParser()
	conf.read(confpath)
	logging.basicConfig(filename=os.path.join(basepath, 'logs/poem_service.log'), level=logging.DEBUG,
		format = '[%(filename)s:%(lineno)s - %(funcName)s %(asctime)s;%(levelname)s] %(message)s',
		datefmt = '%Y-%m-%d %H:%M:%S')

	logger = logging.getLogger("PoemClient")
	try:
		host = "127.0.0.1"
		port = "29900"

		transport = TSocket.TSocket(host, port)
		transport = TTransport.TFramedTransport(transport)
		protocol = TBinaryProtocol.TBinaryProtocol(transport)
		client = OmgService.Client(protocol) 
		transport.open()
		try:
			print 'test'
			result = client.test(123)
			print result
		except Exception as e:
			print e
			logger.exception(e)
		finally:
			transport.close()

	except Exception as e:
		logger.exception(e)
