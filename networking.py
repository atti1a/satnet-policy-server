from __future__ import print_function

import asyncore, asynchat, enum, json, logging, socket
import sched, time
from ConfigParser import ConfigParser
from policy_server import PS

class PolicyServer(asyncore.dispatcher):

    def __init__(self, ps_logic):
	asyncore.dispatcher.__init__(self)

	self.logger = logging.getLogger(self.__class__.__name__)
        self.handler = GenericHandler
        self.ps_logic = ps_logic


    def handle_accept(self):
        connection, address = self.accept()
        self.logger.debug('accept -> %s', address)
        self.handler(connection, self.ps_logic)
        

    def handle_close(self):
        self.logger.debug('close')
        self.close()


    def _construct_socket(self, address):
	self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
	self.bind(address)
	self.address = self.socket.getsockname()
	self.logger.debug('binding to %s', self.address)
	self.listen(5)

class Peer(enum.Enum):
    Generic         = 0
    Groundstaion    = 1
    PolicyServer    = 2
    MissionServer   = 3

class GenericHandler(asynchat.async_chat):

    gs_handler_roster = {}
    ms_handler_roster = {}
    ps_handler_roster = {}

    def __init__(self, sock, ps_logic, terminator):
        asynchat.async_chat.__init__(self, sock=sock)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.buffer = []
        self.ps_logic = ps_logic
        self.peer = Peer.Generic

        self.set_terminator(terminator)

    def collect_incoming_data(self, data):
        self.logger.debug('collect_incoming_data() -> (%d bytes)\n"""%s"""',
                          len(data),
                          data)
        self.buffer.append(data)

    def _log_failure(self, e, msg):
        self.logger.error(msg)
        self.logger.debug(str(e))
        self.logger.debug(msg)
        self.close()


class JsonProtocolType(enum.Enum):
    PS_INIT     = 0
    MS_INIT     = 1
    TR          = 2
    RESP        = 3
    GS          = 4
    CANCEL      = 5
    ORIGIN      = 6
    ORIGIN_RESP = 7

class JsonHandler(GenericHandler):

    def __init__(self, sock, ps_logic):
        GenericHandler.__init__(self, sock, ps_logic, '\n')

        self._handle_by_msg_type = self._handle_by_msg_type_init


    def found_terminator(self):
        msg = ''.join(self.buffer)
        self.buffer = []

        parse_tup = self._parse_message(msg)

        if parse_tup is None:
            return

        resps = self._handle_by_msg_type(*parse_tup)

        for (dst, data) in resps:
            self.logger.debug('Gotta send something to %s', dst)

        return


    def _parse_message(self, msg):
        try:
            json_dict = json.loads(msg)
        except ValueError as e:
            self._log_failure(e, "Failed to parse JSON message")
            return None

        try:
            message_type = JsonProtocolType[json_dict['type']]
        except KeyError as e:
            self._log_failure(e, "Invalid message type")
            return None

        data = dict(json_dict)
        del data['type']

        self.logger.debug('succesfully parsed json\n"""%s"""\n"""%s"""',
                          message_type,
                          data)

        return message_type, data


    def _handle_by_msg_type_init(self, message_type, data):
        if message_type == JsonProtocolType.PS_INIT:
            self._handle_PS_INIT(data)
        elif message_type == JsonProtocolType.MS_INIT:
            self._handle_MS_INIT(data)

        return []



    def _handle_by_msg_type_ps(self, message_type, data):
        if message_type == JsonProtocolType.TR:
            # resps = self.ps_logic.handle_request
            pass
        elif message_type == JsonProtocolType.RESP:
            pass
        elif message_type == JsonProtocolType.GS:
            # resps = self.ps_logic.fwd_stripped_gs_metadata(data_field)
            pass
        elif message_type == JsonProtocolType.CANCEL:
            pass

        return []


    def _handle_by_msg_type_ms(self, message_type, data):
        if message_type == JsonProtocolType.TR:
            # resps = self.ps_logic.handle_request
            pass
        elif message_type == JsonProtocolType.RESP:
            pass
        elif message_type == JsonProtocolType.CANCEL:
            pass

        return []

    def _handle_PS_INIT(self, data):
        #TODO Pass through to event ps_init
        self.logger.debug("Converting %s to %s", self.peer, Peer.PolicyServer)
        self.peer = Peer.PolicyServer
        self.ps_handler_roster[data['psID']] = self
        self._handle_by_msg_type = self._handle_by_msg_type_ps


    def _handle_MS_INIT(self, data):

        psk = config.get('security', 'psk')
        if psk != data['psk']:
            self.logger.error('Bad psk, killing mission server connection')
            self.close()

        #TODO Pass through to event ms_init
        self.logger.debug("Converting %s to %s", self.peer, Peer.MissionServer)
        self.peer = Peer.MissionServer
        self.ms_handler_roster[data['msID']] = self
        self._handle_by_msg_type = self._handle_by_msg_type_ms


class LcmHandler(GenericHandler):

    def __init__(self, sock, ps_logic):
        GenericHandler.__init__(self, sock, ps_logic, 0)

    def found_terminator(self):
        msg = ''.join(self.buffer)
        self.buffer = []

        self.logger.debug('%s', msg)

class JsonPolicyServer(PolicyServer):

    def __init__(self, config, ps_logic):
        PolicyServer.__init__(self, ps_logic)

        self.handler = JsonHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'json_port')
        self._construct_socket((ip, port))


class LcmPolicyServer(PolicyServer):

    def __init__(self, config, ps_logic):
        PolicyServer.__init__(self, ps_logic)

        self.handler = LcmHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'lcm_port')
        self._construct_socket((ip, port))


def gmtTime():
    return time.gmtime()

def asyncLoop(t):
    asyncore.loop(timeout=t)

def main():
    config = ConfigParser()
    config.read('config.ini')

    s = sched.scheduler(gmtTime, asyncLoop)
    ps_logic = PS(s)

    logging.basicConfig(level=logging.DEBUG, 
            format='%(name)s: %(levelname)s: %(message)s')

    JsonPolicyServer(config, ps_logic)
    LcmPolicyServer(config, ps_logic)

    while True:
        s.run()

if __name__ == '__main__':
    main()
