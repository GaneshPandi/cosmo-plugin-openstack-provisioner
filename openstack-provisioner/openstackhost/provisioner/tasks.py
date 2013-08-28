from novaclient.v1_1 import client

__author__ = 'elip'


def provision(openstack_credentials, __cloudify_id=None, region=None, image_id=None, flavor_id=None,
              key_name=None, **kwargs):

    nova = _init_client(openstack_credentials=openstack_credentials, region=region)
    nova.servers.create(name=__cloudify_id, image=image_id, flavor=flavor_id, key_name=key_name)

def terminate(openstack_credentials=None, __cloudify_id=None, region=None, **kwargs):

    nova = _init_client(openstack_credentials=openstack_credentials, region=region)
    try:
        server = get_server_by_name(nova, __cloudify_id)
        server.delete()
    except IndexError:
        raise_server_not_found(__cloudify_id)

def start(openstack_credentials=None, __cloudify_id=None, region=None, **kwargs):

    nova = _init_client(openstack_credentials=openstack_credentials, region=region)
    try:
        server = get_server_by_name(nova, __cloudify_id)
        server.start()
    except IndexError:
        raise_server_not_found(__cloudify_id)

def pause(openstack_credentials=None, __cloudify_id=None, region=None, **kwargs):

    nova = _init_client(openstack_credentials=openstack_credentials, region=region)
    try:
        server = get_server_by_name(nova, __cloudify_id)
        server.pause()
    except IndexError:
        raise_server_not_found(__cloudify_id)


def restart(openstack_credentials=None, __cloudify_id=None, region=None, **kwargs):

    nova = _init_client(openstack_credentials=openstack_credentials, region=region)
    try:
        server = get_server_by_name(nova, __cloudify_id)
        server.reboot()
    except IndexError:
        raise_server_not_found(__cloudify_id)


def _init_client(openstack_credentials, region=None):
    username = openstack_credentials['username']
    password = openstack_credentials['password']
    auth_url = openstack_credentials['auth_url']
    tenantName = openstack_credentials['tenant']
    return client.Client(username,
                         password,
                         tenantName,
                         auth_url=auth_url,
                         region_name=region)

def get_server_by_name(nova, name):
    return nova.servers.list(True, {'name': name}).pop()

def raise_server_not_found(name):
    raise Exception("Could not find a server with name {0}".format(name))
