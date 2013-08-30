from novaclient.v1_1 import client
from celery import task
import keystone_config

__author__ = 'elip'

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
        server.start()
    except IndexError, e:
        _raise_server_not_found(__cloudify_id, e)

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
    command = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "monitor.py"),
        "--pid_file={0}".format(os.path.join(v.root, "monitor.pid"))
    ]
    if (region is not None):
        command.insert("--region_name={0}".format(region))
        
    command = filter(lambda s: len(s) > 0, command)

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
