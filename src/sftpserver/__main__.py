###############################################################################
#
# Copyright (c) 2011-2017 Ruslan Spivak
# Copyright (c) 2020 Steven Fernandez <steve@lonetwin.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

__author__ = 'Steven Fernandez <steve@lonetwin.net>'

import argparse
import getpass
import logging
import os
import pwd
import socket
import sys

import paramiko

from sftpserver.stub_sftp import StubSFTPServer, ssh_server

# - Defaults
HOST, PORT = 'localhost', 3373
ROOT = StubSFTPServer.ROOT
LOG_LEVEL = logging.getLevelName(logging.INFO)
MODE = 'threaded'

BACKLOG = 10


def setup_logging(level, mode):
    if mode == 'threaded':
        log_format = logging.BASIC_FORMAT
    else:
        log_format = '%(process)d:' + logging.BASIC_FORMAT

    logging.basicConfig(format=log_format)

    # - setup paramiko logging
    paramiko_logger = logging.getLogger('paramiko')
    paramiko_logger.setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    return logger


def setup_transport(connection):
    transport = paramiko.Transport(connection)
    transport.add_server_key(StubSFTPServer.KEY)
    transport.set_subsystem_handler('sftp', paramiko.SFTPServer, StubSFTPServer)
    transport.start_server(server=ssh_server)
    return transport


def start_server(host=HOST, port=PORT, root=ROOT, keyfile=None, password=None, level=LOG_LEVEL, mode=MODE):
    logger = setup_logging(level, mode)

    if keyfile is None:
        server_key = paramiko.RSAKey.generate(bits=1024)
    else:
        server_key = paramiko.RSAKey.from_private_key_file(keyfile, password=password)

    StubSFTPServer.ROOT = root
    StubSFTPServer.KEY = server_key

    logger.debug('Serving %s over sftp at %s:%s', root, host, port)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    server_socket.bind((host, port))
    server_socket.listen(BACKLOG)

    sessions = []
    while True:
        connection, _ = server_socket.accept()
        if mode == 'forked':
            logger.debug('Starting a new process')
            pid = os.fork()
            if pid == 0:
                transport = setup_transport(connection)
                channel = transport.accept()
                if os.geteuid() == 0:
                    user = pwd.getpwnam(transport.get_username())
                    logger.debug('Dropping privileges, will run as %s', user.pw_name)
                    os.setgid(user.pw_gid)
                    os.setuid(user.pw_uid)
                transport.join()
                logger.debug("session for %s has ended. Exiting", user.pw_name)
                sys.exit()
            else:
                sessions.append(pid)
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid:
                    sessions.remove(pid)
        else:
            logger.debug('Starting a new thread')
            transport = setup_transport(connection)
            channel = transport.accept()
            sessions.append(channel)

        logger.debug('%s active sessions', len(sessions))


def main():
    usage = """usage: sftpserver [options]"""
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument(
        '--host', dest='host', default=HOST,
        help='listen on HOST [default: %(default)s]'
    )
    parser.add_argument(
        '-p', '--port', dest='port', type=int, default=PORT,
        help='listen on PORT [default: %(default)d]'
    )
    parser.add_argument(
        '-l', '--level', dest='level', default=LOG_LEVEL,
        help='Debug level: WARNING, INFO, DEBUG [default: %(default)s]'
    )
    parser.add_argument(
        '-k', '--keyfile', dest='keyfile', metavar='FILE',
        help='Path to private key, for example /tmp/test_rsa.key'
    )
    parser.add_argument(
        '-P', '--password', help='Prompt for keyfile password', action="store_true"
    )

    parser.add_argument(
        '-r', '--root', dest='root', default=ROOT,
        help='Directory to serve as root for the server'
    )
    parser.add_argument(
        '-m', '--mode', default=MODE, const=MODE, nargs='?', choices=('threaded', 'forked'),
        help='Mode to run server in [default: %(default)s]'
    )

    args = parser.parse_args()

    if not os.path.isdir(args.root):
        parser.print_help()
        sys.exit(-1)

    password = None
    if args.password:
        password = getpass.getpass("Password: ")

    start_server(args.host, args.port, args.root, args.keyfile, password, args.level, args.mode)


if __name__ == '__main__':
    main()
