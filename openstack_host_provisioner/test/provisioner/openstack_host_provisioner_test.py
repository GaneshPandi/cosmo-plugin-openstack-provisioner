import logging
import random
import string
import sys
import inspect
from unittest.case import TestCase

from novaclient.v1_1 import client
import time

from openstackhost.provisioner import tasks


__author__ = 'elip'

import unittest

class OpenstackHostProvisionerTest(unittest.TestCase):

    IMAGE_ID = "78633512-fe61-4f74-8485-f8861ad14929"
    FLAVOR_ID = 2
    OPENSTACK_CREDENTAILS = {
        'username': '${username}',
        'tenant': '${tenant}',
        'password': '${password}',
        'auth_url': '{auth_url}'
    }

    @classmethod
    def setUpClass(cls):
        username = cls.OPENSTACK_CREDENTAILS['username']
        password = cls.OPENSTACK_CREDENTAILS['password']
        auth_url = cls.OPENSTACK_CREDENTAILS['auth_url']
        tenantName = cls.OPENSTACK_CREDENTAILS['tenant']
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger = logging.getLogger("OpenstackHostProvisionerTest")
        logger.level = logging.DEBUG
        cls.logger = logger
        cls.nova = client.Client(username,
                                 password,
                                 tenantName,
                                 auth_url=auth_url)

    @classmethod
    def tearDownClass(cls):
        servers_list = cls.nova.servers.list()
        for server in servers_list:
            try:
                cls.logger.info("Deleting server with name " + server.name)
                server.delete()
            except Exception:
                cls.logger.warning("Failed to delete server with name " + server.name)

    def test_provision(self):

        self.logger.info("Running " + str(inspect.stack()[0][3] + " : "))

        name = "test_provision{0}".format(self._id_generator(3))

        self.logger.info("Provisioning server with name " + name)
        tasks.provision(openstack_credentials=self.OPENSTACK_CREDENTAILS,
                        __cloudify_id=name,
                        image_id=self.IMAGE_ID,
                        flavor_id=self.FLAVOR_ID)

        server = tasks.get_server_by_name(self.nova, name)
        self.logger.info("Successfully provisioned server : " + str(server))
        self.assertIsNotNone(server, msg="Could not find any servers with name{0} after provisioning".format(name))
        self.assertEquals(server.name, name, msg="Server lookup was incorrect")
        self.assertEquals(server.image['id'], self.IMAGE_ID, msg="Image id for server is incorrect")
        self.assertEquals(int(server.flavor['id']), self.FLAVOR_ID, msg="Flavor id for server incorrect")

    def test_terminate(self):

        self.logger.info("Running " + str(inspect.stack()[0][3] + " : "))

        name = "test_terminate{0}".format(self._id_generator(3))

        self.logger.info("Provisioning server with name " + name)
        tasks.provision(openstack_credentials=self.OPENSTACK_CREDENTAILS,
                        __cloudify_id=name,
                        image_id=self.IMAGE_ID,
                        flavor_id=self.FLAVOR_ID)


        self.logger.info("Terminating server with name " + name)
        tasks.terminate(openstack_credentials=self.OPENSTACK_CREDENTAILS,
                        __cloudify_id=name)

        expire = time.time() + 10
        while time.time() < expire:
            self.logger.info("Querying server by name " + name)
            try:
                tasks.get_server_by_name(self.nova, name)
                self.logger.info("Server has not yet terminated. sleeping...")
                time.sleep(0.5)
            except Exception:
                self.logger.info("Server has terminated. All good")
                return
        self.fail(msg="Server with name " + name + " was not terminated after 10 seconds")



    def _id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))


