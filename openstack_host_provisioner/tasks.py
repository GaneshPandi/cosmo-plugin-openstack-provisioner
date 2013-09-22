import copy
import inspect
import itertools
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
def provision(__cloudify_id, nova, **kwargs):

    """
    Creates a server. Exposes the parameters mentioned in
    http://docs.openstack.org/developer/python-novaclient/api/novaclient.v1_1.servers.html#novaclient.v1_1.servers.ServerManager.create
    Userdata:
        In all cases, note that userdata should not be base64 encoded, novaclient expects it raw.
        The 'userdata' argument under nova.instance can be one of the following:
        1. A string
        2. A hash with 'type: file' and 'path: ...'
        2. A hash with 'type: url' and 'url: ...'

    """

    _fail_on_missing_required_parameters(nova, ('region', 'instance'), 'nova')

    nova_instance = copy.deepcopy(nova['instance']) # For possible changes by _maybe_transform_userdata()
    _maybe_transform_userdata(nova_instance)

    _fail_on_missing_required_parameters(nova_instance, ('flavor', 'image', 'key_name'), 'nova.instance')

    nova_client = _init_client(region=nova['region'])

    params_names = inspect.getargspec(nova_client.servers.create).args[1:] # First parameter is 'self', skipping
    params_default_values = inspect.getargspec(nova_client.servers.create).defaults
    params = dict(itertools.izip(params_names, params_default_values))

    del params['name'] # We pass this one outside **params so it must not be present here

    # Fail on unsupported parameters
    for k in nova_instance:
        if k not in params:
            raise ValueError("Parameter with name '{0}' must not be passed to openstack provisioner (under host's properties.nova.instance)".format(k))

    for k in params:
        if k in nova_instance:
            params[k] = nova_instance[k]

    if _get_server_by_name(nova_client, __cloudify_id):
        raise RuntimeError("Can not provision server with name '{0}' because server with such name already exists".format(__cloudify_id))

    logger.info("Asking Nova to create server. Parameters: {0}".format(str(params)))
    logger.debug("Asking Nova to create server. All possible parameters are: {0})".format(','.join(params.keys())))

    nova_client.servers.create(name=__cloudify_id, **params)

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
                         http_log_debug=False)

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

def _fail_on_missing_required_parameters(obj, required_parameters, hint_where):
    for k in required_parameters:
        if k not in obj:
            raise ValueError("Required parameter '{0}' is missing (under host's properties.{1}). Required parameters are: {2}".format(k, hint_where, required_parameters))

# *** userdata handlig - start ***
userdata_handlers = {}
def userdata_handler(type_):
    def f(x):
        userdata_handlers[type_] = x
        return x
    return f

def _maybe_transform_userdata(nova_instance):
    """Allows userdata to be read from a file, etc, not just be a string"""
    if 'userdata' not in nova_instance:
        return
    if not isinstance(nova_instance['userdata'], dict):
        return
    ud = nova_instance['userdata']

    _fail_on_missing_required_parameters(ud, ('type',), 'nova.instance.userdata')

    if ud['type'] not in userdata_handlers:
        raise ValueError("Invalid type '{0}' (under host's properties.nova.instance.userdata)".format(ud['type']))

    nova_instance['userdata'] = userdata_handlers[ud['type']](ud)

@userdata_handler('file')
def ud_file(params):
    """ Reads userdata from a file (absolute path) """
    _fail_on_missing_required_parameters(params, ('path',), "nova.instance.userdata when using type 'file'")
    logger.info("Using userdata in file {0}".format(params['path']))
    with open(params['path'], 'r') as f:
        return f.read()

@userdata_handler('http')
def ud_http(params):
    """ Fetches userdata using HTTP """
    import requests
    _fail_on_missing_required_parameters(params, ('url',), "nova.instance.userdata when using type 'http'")
    logger.info("Using userdata from URL {0}".format(params['url']))
    return requests.get(params['url']).text
# *** userdata handlig - end ***
