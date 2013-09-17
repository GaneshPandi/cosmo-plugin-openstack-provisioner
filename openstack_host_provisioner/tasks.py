import os
import subprocess
import sys

from novaclient.v1_1 import client
from celery import task
import keystone_config

from celery.utils.log import get_task_logger

__author__ = 'elip'

logger = get_task_logger(__name__)

@task
def provision(__cloudify_id, region=None, image_id=None, flavor_id=None,
              key_name=None, **kwargs):

    nova = _init_client(region=region)
    if _get_server_by_name(nova, __cloudify_id):
        raise RuntimeError("Can not provision server with name '{0}' because server with such name already exists".format(__cloudify_id))
    logger.debug("Server with name {0} does not exist, proceeding to call nova to create the server")
    nova.servers.create(name=__cloudify_id, image=image_id, flavor=flavor_id, key_name=key_name)

@task
def start(__cloudify_id, region=None, **kwargs):

    nova = _init_client(region=region)
    server = _get_server_by_name_or_fail(nova, __cloudify_id)

    # ACTIVE - already started
    # BUILD - is building and will start automatically after the build

    if server.status == 'ACTIVE' or server.status.startswith('BUILD'):
        start_monitor(region)
        return

    # Rackspace: stop, start, pause, unpause, suspend - not implemented. Maybe other methods too.

    # SHUTOFF - powered off
    if server.status == 'SHUTOFF':
        server.reboot()
        start_monitor(region)
        return

    raise ValueError("openstack_host_provisioner: Can not start() server in state {0}".format(server.status))


@task
def stop(__cloudify_id, region=None, **kwargs):

    server = _get_server_by_name_or_fail(nova, __cloudify_id)
    server.stop()

@task
def terminate(__cloudify_id, region=None, **kwargs):

    nova = _init_client(region=region)
    server = _get_server_by_name_or_fail(nova, __cloudify_id)
    server.delete()

@task
def start_monitor(region = None):
    # WARNING: hard coded UNIX-specific pid file path
    command = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "monitor.py"),
        "--pid_file={0}".format(os.path.join("/var/run/cosmo-openstack-monitor.pid"))
    ]
    if region:
        command.append("--region_name={0}".format(region))
        
    logger.info('starting openstack monitoring [cmd=%s]', command)
    subprocess.Popen(command)

def _init_client(region=None):
    return client.Client(username=keystone_config.username,
                         api_key=keystone_config.password,
                         project_id=keystone_config.tenant_name,
                         auth_url=keystone_config.auth_url,
                         region_name=region,
                         http_log_debug=True)

def _get_server_by_name(nova, name):
    matching_servers = nova.servers.list(True, {'name': name})
    if len(matching_servers) == 0:
        return None
    if len(matching_servers) == 1:
        return matching_servers[0]
    raise RuntimeError("Lookup of server by name failed. There are {0} servers named '{1}'".format(len(matching_servers), name))

def _get_server_by_name_or_fail(nova, name):
    server = _get_server_by_name(nova, name)
    if server:
        return server
    raise ValueError("Lookup of server by name failed. Could not find a server with name {0}")
