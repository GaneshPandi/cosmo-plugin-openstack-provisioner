__author__ = 'elip'

import setuptools

setuptools.setup(
    zip_safe=True,
    name='cosmoopenstack',
    version='0.1.0',
    author='elip',
    author_email='itaifgigaspaces.com',
    packages=['openstack_host_provisioner'],
    license='LICENSE.txt',
    description='Plugin for provisioning openstack nova hosts',
    install_requires=[
        "python-novaclient",
        "billiard==2.7.3.28",
        "celery==3.0.19",
        "bernhard"
    ],
    tests_require=['nose']
)