from __future__ import print_function

import asyncore, asynchat, enum, json, logging, socket, sys
import sched, time
from ConfigParser import ConfigParser
from policy_server import PS

class PolicyServer(asyncore.dispatcher):

    def __init__(self, config, ps_logic):
	asyncore.dispatcher.__init__(self)

	self.logger = logging.getLogger(self.__class__.__name__)
        self.handler = GenericHandler
        self.ps_logic = ps_logic
        self.config = config


    def handle_accept(self):
        connection, address = self.accept()
        self.logger.debug('accept -> %s', address)
        self.handler(connection, self.config, self.ps_logic)
        

    def handle_close(self):
        self.logger.debug('close')
        self.close()


    def _construct_socket(self, address):
	self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
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

    def __init__(self, sock, config, ps_logic, terminator):
        asynchat.async_chat.__init__(self, sock=sock)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.buffer = []
        self.ps_logic = ps_logic
        self.peer = Peer.Generic
        self.config = config

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

def getJsonProtocolType(s):
    if s == "PS_INIT":
        return JsonProtocolType.PS_INIT
    elif s == "MS_INIT":
        return JsonProtocolType.MS_INIT
    elif s == "TR":
        return JsonProtocolType.TR
    elif s == "RESP":
        return JsonProtocolType.RESP
    elif s == "GS":
        return JsonProtocolType.GS
    elif s == "CANCEL":
        return JsonProtocolType.CANCEL
    elif s == "ORIGIN":
        return JsonProtocolType.ORIGIN
    elif s == "ORIGIN_RESP":
        return JsonProtocolType.ORIGIN_RESP

class JsonHandler(GenericHandler):

    def __init__(self, sock, config, ps_logic):
        GenericHandler.__init__(self, sock, config, ps_logic, '\n')

        self._handle_by_msg_type = self._handle_by_msg_type_init



    def found_terminator(self):
        msg = ''.join(self.buffer)
        self.buffer = []

        parse_tup = self._parse_message(msg)

        if parse_tup is None:
            return
        
        resps = self._handle_by_msg_type(*parse_tup)

        for dst, data in resps:
            if isinstance(dst, JsonHandler):
                dst.push_json(data)
            else:
                print("Strings not yet implemented")

	return


    def push_json(self, data):
        self.logger.debug("Sending json object to policy server")
        self.logger.debug(data)
        self.push(json.dumps(data) + '\n')


    def _send_data(self, dst, data):
        if isinstance(dst, str):
            raise Exception("Not yet implemented")
        else:
            dst.push_json(data)


    def send_ps_metadata(self):
        msg = {'type': JsonProtocolType.PS_INIT.name, 
               'psID': self.config.get('server', 'id'),
               'name': self.config.get('server', 'name')}

        self.push_json(msg)


    def _parse_message(self, msg):
        try:
            json_dict = json.loads(msg)
        except ValueError as e:
            self._log_failure(e, "Failed to parse JSON message")
            return None

        try:
            message_type = getJsonProtocolType(json_dict['type'])
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
            return self._handle_PS_INIT(data)
        elif message_type == JsonProtocolType.MS_INIT:
            return self._handle_MS_INIT(data)
        else:
            raise ValueError('No handler for %s' % message_type)



    def _handle_by_msg_type_ps(self, message_type, data):
        if message_type == JsonProtocolType.TR:
            return self._handle_TR(data)
        elif message_type == JsonProtocolType.RESP:
            return self._handle_FWD_RESP(data)
        elif message_type == JsonProtocolType.GS:
            return self.ps_logic.fwd_stripped_gs_metadata(data, self)
        elif message_type == JsonProtocolType.CANCEL:
            return self.ps_logic.fwd_cancel_to_ms(data)
        elif message_type == JsonProtocolType.PS_INIT:
            return []
        else:
            raise ValueError('No handler for %s' % message_type)


    def _handle_by_msg_type_ms(self, message_type, data):
        if message_type == JsonProtocolType.TR:
            return self._handle_TR(data)
        elif message_type == JsonProtocolType.RESP:
            return [] #should never occur
        elif message_type == JsonProtocolType.CANCEL:
            return [] #should never occur
        elif message_type == JsonProtocolType.MS_INIT:
            return []
        else:
            raise ValueError('No handler for %s' % message_type)


    def _handle_TR(self, data):
        resps = self.ps_logic.handle_requests(data['trList'], self)

        send_tuples = []
        for dst, packets in resps.iteritems():
            for packet in packets:
                send_tuples.append((dst, packet))

        return send_tuples

    def _handle_FWD_RESP(self, data):
        resps = self.ps_logic.fwd_responses_to_ms(data['respList'])

        send_tuples = []
        for dst, packets in resps.iteritems():
            for packet in packets:
                send_tuples.append((dst, packet))

        return send_tuples


    def _handle_PS_INIT(self, data):

        self.logger.debug("Converting %s to %s", self.peer, Peer.PolicyServer)
        gs_data = self.ps_logic.ps_init(data, self)
        self.peer = Peer.PolicyServer
        self.ps_handler_roster[data['psID']] = self
        self._handle_by_msg_type = self._handle_by_msg_type_ps
        self.send_ps_metadata()
        
        send_tuples = []

        for dst, packets in gs_data.iteritems():
            for packet in packets:
                send_tuples.append((dst, packet))

        return send_tuples


    def _handle_MS_INIT(self, data):

        psk = self.config.get('security', 'psk')
        if psk != data['psk']:
            self.logger.error('Bad psk, killing mission server connection')
            self.close()

        self.logger.debug("Converting %s to %s", self.peer, Peer.MissionServer)
        self.peer = Peer.MissionServer
        self.ms_handler_roster[data['msID']] = self
        self._handle_by_msg_type = self._handle_by_msg_type_ms
        
        gs_data = self.ps_logic.ms_init(data, self)

        send_tuples = []

        for dst, packets in gs_data.iteritems():
            for packet in packets:
                send_tuples.append((dst, packet))

        return send_tuples



class LcmHandler(GenericHandler):

    def __init__(self, sock, config, ps_logic):
        GenericHandler.__init__(self, sock, config, ps_logic, 0)

    def found_terminator(self):
        msg = ''.join(self.buffer)
        self.buffer = []

        self.logger.debug('%s', msg)


class JsonPolicyServer(PolicyServer):

    def __init__(self, config, ps_logic):
        PolicyServer.__init__(self, config, ps_logic)

        self.handler = JsonHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'json_port')
        self._construct_socket((ip, port))


class LcmPolicyServer(PolicyServer):

    def __init__(self, config, ps_logic):
        PolicyServer.__init__(self, config, ps_logic)

        self.handler = LcmHandler

        ip = config.get('server', 'ip_address')
        port = config.getint('server', 'lcm_port')
        self._construct_socket((ip, port))


def gmtTime():
    return time.gmtime()


def scheduleLoop(t):
    asyncore.poll(timeout=t)


def main():
    config = ConfigParser()
    config.read(sys.argv[1])

    s = sched.scheduler(gmtTime, time.sleep)
    ps_logic = PS(s)

    logging.basicConfig(level=logging.DEBUG, 
            format='%(name)s: %(levelname)s: %(message)s')

    lg = logging.getLogger('Networking')

    JsonPolicyServer(config, ps_logic)
    LcmPolicyServer(config, ps_logic)

    for origin in config.get('peers', 'policy_servers').split():
        try:
            ip, port = origin.split(':')
            port = int(port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, port))
            jh = JsonHandler(sock, config, ps_logic)
            jh.send_ps_metadata()
            lg.debug("Connected to %s:%d", ip, port)
        except Exception as e:
            lg.warning("Peer %s:%d is down" % (ip, port))
            lg.debug(e)
            continue

    #TODO this is for testing
    ps_logic.add_groundstation_local(10, 12, 13)
    ps_logic.add_groundstation_local(11, 32, 33)
    ps_logic.add_groundstation_local(12, 4, 11)


    while True:
        if s.empty():
            scheduleLoop(30)
        else:
            s.run()

if __name__ == '__main__':
    main()
