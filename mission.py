class TLE: # tleUrl, tleName, tle
    def __init__(self, name, url, params):
        self.name = name
        self.url = url
        self.params = params

class AX25: # ax25_callsign, ax25_ssid
    def __init__(self, callsign, ssid):
        self.callsign = callsign
        self.ssid = ssid

class NetLocation: # (ip_addr, kissTcpPort), (mission_server, mission_server_port)
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

class Mission:
    def __init__(self, name, description, tle, kiss_tcp_port, ax25,
            sat_ip_addr, l2_header_type, l3_header_type, rxParams, txParams,
            tracking_priority, mission_server, is_tracking)
