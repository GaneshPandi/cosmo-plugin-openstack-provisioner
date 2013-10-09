import logging
import random
import string
import sys
import inspect
import time
from nose.tools import *
from novaclient.v1_1 import client
import time
import nova_config
from openstack_host_provisioner import tasks
from openstack_host_provisioner import monitor

__author__ = 'elip'


class TestClass:

    def setUp(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("test_openstack_host_provisioner")
        self.logger.level = logging.DEBUG
        self.logger.info("setUp called")
        self.nova = tasks._init_client(region=nova_config.region_name)
        self.name_prefix = 'cosmo_test_openstack_host_provisioner_{0}_'.format(self._id_generator(3))
        self.logger.info("setup")

    def tearDown(self):
        self.logger.info("tearDown called")
        servers_list = self.nova.servers.list()
        for server in servers_list:
            try:
                if (server.name.startswith(self.name_prefix)):
                    self.logger.info("Deleting server with name " + server.name)
                    server.delete()
                else:
                    self.logger.info("NOT deleting server with name " + server.name)

            except Exception:
                self.logger.warning("Failed to delete server with name " + server.name)

    def test_provision(self):
        self.logger.info("Running " + str(inspect.stack()[0][3] + " : "))
        name = self.name_prefix + "test_provision"

        self.logger.info("Provisioning server with name " + name)
        tasks.provision(region=nova_config.region_name,
                        __cloudify_id=name,
                        image_id=nova_config.image_id,
                        flavor_id=nova_config.flavor_id)

        server = tasks._get_server_by_name(self.nova, name)
        self.logger.info("Successfully provisioned server : " + str(server))
        assert server is not None, "Could not find any servers with name{0} after provisioning".format(name)
        assert_equals(server.name, name, "Server lookup was incorrect")
        assert_equals(str(server.image['id']), str(nova_config.image_id))
        assert_equals(str(server.flavor['id']), str(nova_config.flavor_id))
        self._wait_for_machine_state(name, u'ACTIVE')

    def test_terminate(self):
        self.logger.info("Running " + str(inspect.stack()[0][3] + " : "))
        name = self.name_prefix + "test_provision"

        self.logger.info("Provisioning server with name " + name)
        tasks.provision(region=nova_config.region_name,
                        __cloudify_id=name,
                        image_id=nova_config.image_id,
                        flavor_id=nova_config.flavor_id)

        self.logger.info("Terminating server with name " + name)
        tasks.terminate(__cloudify_id=name, region=nova_config.region_name)

        expire = time.time() + 10
        while time.time() < expire:
            self.logger.info("Querying server by name " + name)
            try:
                tasks._get_server_by_name(nova, name)
                self.logger.info("Server has not yet terminated. sleeping...")
                time.sleep(0.5)
            except Exception:
                self.logger.info("Server has terminated. All good")
                return
        raise Exception("Server with name " + name + " was not terminated after 10 seconds")

    def _id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def _wait_for_machine_state(self, name, expected_state):        
        while True:
            actual_state = self._get_machine_state(name)
            if (actual_state == expected_state):
                break
            self.logger.info('waiting for machine {0} expected state:{1} current state:{2}'.format(name,expected_state, actual_state))
            time.sleep(10)

        self.logger.info('machine {0} reached expected machine state {1}'.format(name,expected_state))

    def _get_machine_state(self, name):
        ttl = 0
        events = monitor._probe(self.nova, ttl)
        tags='name={0}'.format(name)
        return next((e['state'] for e in events if e['tags']==tags), None)
        
