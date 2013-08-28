import logging
import random
import string
import sys
import inspect

from novaclient.v1_1 import client
import time
import nova_config
import keystone_config
from openstack_host_provisioner import tasks
from nose.tools import *

__author__ = 'elip'


class TestClass:

    def setUp(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("test_openstack_host_provisioner")
        self.logger.level = logging.DEBUG
        self.logger.info("setUp called")
        self.openstack_credentials = {k:v for k,v in keystone_config.__dict__.iteritems() if not k.startswith('_')}
        self.nova = tasks._init_client(self.openstack_credentials, region=nova_config.region_name)
        self.logger.info(self.nova.flavors.list())
        self.name_prefix = 'cosmo_test_openstack_host_provisioner_{0}_'.format(_id_generator(3))
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
        tasks.provision(openstack_credentials=self.openstack_credentials,
                        region=nova_config.region_name,
                        __cloudify_id=name,
                        image_id=nova_config.image_id,
                        flavor_id=nova_config.flavor_id)

        server = tasks._get_server_by_name(self.nova, name)
        self.logger.info("Successfully provisioned server : " + str(server))
        assert server is not None, "Could not find any servers with name{0} after provisioning".format(name)
        assert_equals(server.name, name, "Server lookup was incorrect")
        assert_equals(int(server.image['id']), nova_config.image_id)
        assert_equals(int(server.flavor['id']), nova_config.flavor_id)


    def test_terminate(self):
        self.logger.info("Running " + str(inspect.stack()[0][3] + " : "))
        name = self.name_prefix + "test_provision"

        self.logger.info("Provisioning server with name " + name)
        tasks.provision(openstack_credentials=self.openstack_credentials,
                        region=nova_config.region_name,
                        __cloudify_id=name,
                        image_id=nova_config.image_id,
                        flavor_id=nova_config.flavor_id)

        self.logger.info("Terminating server with name " + name)
        tasks.terminate(openstack_credentials=self.openstack_credentials,
                        __cloudify_id=name)

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


