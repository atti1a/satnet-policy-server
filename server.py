from __future__ import print_function

import select, socket
from ConfigParser import ConfigParser

def get_client_socket(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    return s

def get_server_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', port))
    s.listen(5)
    return s

def main():
    config = ConfigParser()
    config.read('config.ini')

    for ms in config.get('servers', 'mission_servers').split(' '):
        print("I should connect to {}".format(ms))

    # while True:
    #     pass

if __name__ == '__main__':
    main()
