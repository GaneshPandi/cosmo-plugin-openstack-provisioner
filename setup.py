__author__ = 'elip'

import setuptools

setuptools.setup(
    zip_safe=True,
    name='cosmovagrant',
    version='0.1.0',
    author='elip',
    author_email='elip@gigaspaces.com',
    packages=['vagrant_host_provisioner'],
    license='LICENSE.txt',
    description='Plugin for provisioning vagrant hosts',
    install_requires=[
        "python-vagrant>=0.3.1",
        "billiard==2.7.3.28",
        "celery==3.0.19",
        "fabric",
        "bernhard"
    ],
    tests_require=['nose']
)