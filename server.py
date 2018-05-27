from __future__ import print_function

import asyncore, json, logging, socket
import Queue
from ConfigParser import ConfigParser

class PolicyServer(asyncore.dispatcher):

    def __init__(self):
	asyncore.dispatcher.__init__(self)

	self.logger = logging.getLogger(self.__class__.__name__)
        self.handler = GenericHandler


    def handle_accept(self):
        connection, address = self.accept()
        self.logger.debug('accept -> %s', address)
        self.handler(connection)
        

    def handle_close(self):
        self.logger.debug('close')
        self.close()


    def _construct_socket(self, address):
	self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
	self.bind(address)
	self.address = self.socket.getsockname()
	self.logger.debug('binding to %s', self.address)
	self.listen(5)

class GenericHandler(asyncore.dispatcher):

    def __init__(self, sock):
	asyncore.dispatcher.__init__(self, sock=sock)

	self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.debug('Here is a %s, but it does nothing' % self.__class__.__name__)
        self.close()


class JsonHandler(GenericHandler):
    pass


class LcmHandler(GenericHandler):
    pass


class JsonPolicyServer(PolicyServer):

    def __init__(self, config):
        PolicyServer.__init__(self)

        self.handler = JsonHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'json_port')
        self._construct_socket((ip, port))


class LcmPolicyServer(PolicyServer):

    def __init__(self, config):
        PolicyServer.__init__(self)

        self.handler = LcmHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'lcm_port')
        self._construct_socket((ip, port))


def main():
    config = ConfigParser()
    config.read('config.ini')

    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    JsonPolicyServer(config)
    LcmPolicyServer(config)

    asyncore.loop()

if __name__ == '__main__':
    main()
