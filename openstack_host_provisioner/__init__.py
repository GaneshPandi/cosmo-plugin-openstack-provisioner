__author__ = 'idanm'

from celery import Celery

celery = Celery('cosmo.celery',
                broker='amqp://',
                backend='amqp://')
