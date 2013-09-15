#/*******************************************************************************
# * Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *       http://www.apache.org/licenses/LICENSE.txt-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
# *******************************************************************************/

import argparse
import threading
import time
import sys
import signal
import os
import logging

import bernhard
import tasks
from openstack_host_provisioner import tasks

class OpenstackStatusMonitor(object):

    def __init__(self, args):
        print args
        self.timer = None
        self.interval = args.monitor_interval
        self.riemann = self.create_riemann_client(args.riemann_host,
                                                  args.riemann_port,
                                                  args.riemann_transport)
        self.nova = tasks._init_client(region=args.region_name)
        self.register_signal_handlers()
        self.monitor()

    def monitor(self):
        self.probe_and_publish()
        self.timer = threading.Timer(self.interval, self.monitor)
        self.timer.start()

    def probe_and_publish(self):
        ttl = self.interval * 3
        try:
            for event in _probe(self.nova, ttl):
                # print event
                self.riemann.send(event)
        except Exception, e:
            sys.stderr.write("Openstack monitor error: {0}\n".format(e))

        

    def create_riemann_client(self, host, port, transport):
        if transport == 'tcp':
            transport_cls = bernhard.TCPTransport
        else:
            transport_cls = bernhard.UDPTransport
        return bernhard.Client(host, port, transport_cls)

    def register_signal_handlers(self):
        def handle(signum, frame):
            self.close()
        signal.signal(signal.SIGTERM, handle)
        signal.signal(signal.SIGINT, handle)
        signal.signal(signal.SIGQUIT, handle)

    def close(self):
        sys.stdout.write("Trying to shutdown monitor process")
        self.riemann.disconnect()
        if self.timer:
            self.timer.cancel()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description= 'Monitors a given Vagrantfile status and sends it to a riemann server'
    )
    parser.add_argument(
        '--riemann_host',
        help        = 'The riemann host',
        default     = 'localhost'
    )
    parser.add_argument(
        '--riemann_port',
        help        = 'The riemann port',
        default     = 5555,
        type        = int
    )
    parser.add_argument(
        '--riemann_transport',
        help        = 'The riemann transport',
        default     = 'tcp',
        choices     = ['tcp', 'udp']
    )
    parser.add_argument(
        '--monitor_interval',
        help        = 'The interval in seconds to wait between each probe',
        default     = 5,
        type        = int
    )
    parser.add_argument(
        '--region_name',
        help        = 'The openstack region name',
        default     = None
    )
    parser.add_argument(
        '--pid_file',
        help        = 'Path to a filename that should contain the monitor process id'
    )
    return parser.parse_args()


def write_pid_file(pid_file):
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))

def _probe(nova, ttl):
    now = int(time.time())
    return [ _event(host, ttl, now) for host in nova.servers.list() if host.addresses.get('private',None) ]
    

def _event(host, ttl, now):
    
    return {
        'host': host.addresses['private'][0]['addr'],
        'service': 'openstack machine status',
        'time': now,
        'state': host.status,
        'tags': ['name={0}'.format(host.name)],
        'ttl': ttl }

def main():
    logging.basicConfig()
    args = parse_arguments()
    if args.pid_file:
        write_pid_file(args.pid_file)
    OpenstackStatusMonitor(args)
    # to respond to signals promptly
    signal.pause()


if __name__ == '__main__':
    main()

