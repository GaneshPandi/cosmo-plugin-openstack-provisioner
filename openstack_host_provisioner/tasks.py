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
    nova.servers.create(name=__cloudify_id, image=image_id, flavor=flavor_id, key_name=key_name)

@task
def start(__cloudify_id, region=None, **kwargs):

    nova = _init_client(region=region)
    try:
        server = _get_server_by_name(nova, __cloudify_id)
    except IndexError, e:
        _raise_server_not_found(__cloudify_id, e)

    # ACTIVE - already started
    # BUILD - is building and will start automatically after the build

    if server.status in ('ACTIVE', 'BUILD'):
        return

    # Rackspace: stop, start, pause, unpause, suspend - not implemented. Maybe other methods too.

    # SHUTOFF - powered off
    if server.status == 'SHUTOFF':
        server.reboot()
    else:
        raise ValueError("openstack_host_provisioner: Can not start() server in state {0}".format(server.status))

    start_monitor(region)

@task
def stop(__cloudify_id, region=None, **kwargs):

    nova = _init_client(region=region)
    try:
        server = _get_server_by_name(nova, __cloudify_id)
        server.stop()
    except IndexError, e:
        _raise_server_not_found(__cloudify_id, e)

@task
def terminate(__cloudify_id, region=None, **kwargs):

    nova = _init_client(region=region)
    try:
        server = _get_server_by_name(nova, __cloudify_id)
        server.delete()
    except IndexError, e:
        _raise_server_not_found(__cloudify_id, e)

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
    return nova.servers.list(True, {'name': name}).pop()

def _raise_server_not_found(name, e):
    raise ValueError("Could not find a server with name {0}. Details: {1}".format(name, str(e)))
