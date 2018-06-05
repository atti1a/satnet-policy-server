from __future__ import print_function

import asyncore, asynchat, enum, json, logging, socket
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

class GenericHandler(asynchat.async_chat):

    def __init__(self, sock):
	asynchat.async_chat.__init__(self, sock=sock)

	self.logger = logging.getLogger(self.__class__.__name__)

class JsonProtocolType(enum.Enum):
    INIT    = 0
    TR      = 1
    RESP    = 2
    GS      = 3
    CANCEL  = 4

class JsonHandler(GenericHandler):

    def __init__(self, sock):
        GenericHandler.__init__(self, sock)

        self.buffer = []
        self.set_terminator('\n')

    def collect_incoming_data(self, data):
        self.logger.debug('collect_incoming_data() -> (%d bytes)\n"""%s"""',
                          len(data),
                          data)
        self.buffer.append(data)

    def found_terminator(self):
        msg = ''.join(self.buffer)
        self.buffer = []

        try:
            json_dict = json.loads(msg)
        except ValueError as e:
            self.logger.error("Failed to parse JSON message")
            self.logger.debug(str(e))
            self.logger.debug(msg)
            self.close()
            return

        try:
            message_type = JsonProtocolType[json_dict['type']]
        except KeyError as e:
            self.logger.error("Invalid message type")
            self.logger.debug(str(e))
            self.logger.debug(msg)
            self.close()
            return

        data_field = str(message_type.name).lower() + "List"

        try:
            data = json_dict[data_field]
        except KeyError as e:
            self.logger.error("Could not get data field for message")
            self.logger.debug(str(e))
            self.logger.debug(msg)
            self.close()
            return

        self.logger.debug('succesfully parsed json\n"""%s"""\n"""%s"""',
                          message_type,
                          data_field)


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

    logging.basicConfig(level=logging.DEBUG, 
            format='%(name)s: %(levelname)s: %(message)s')

    JsonPolicyServer(config)
    LcmPolicyServer(config)

    asyncore.loop()

if __name__ == '__main__':
    main()
