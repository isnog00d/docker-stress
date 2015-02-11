import os
import logging
from socket import create_connection
from time import time, sleep
from urlparse import urlparse

from docker_client import DockerClientError


log = logging.getLogger(__name__)


def running(client, container_id):
    container_info = client.inspect_container(container_id)
    return container_info and container_info[0]['State']['Running']


def successfully_destroyed(client, container_id):
    try:
        client.destroy(container_id)
        return True
    except DockerClientError, e:
        log.debug('failed to destroy container: %s', e)
        sleep(0.5)
        return False


def connectable(client, container_id, hostname, ports):
    infos = client.inspect_container(container_id)
    info = infos and infos[0]
    settings = info and info.get('NetworkSettings')
    port_settings = settings and settings.get('Ports')
    for port in ports:
        mappings = port_settings and port_settings.get('%d/tcp' % (port, ))
        if not mappings:
            return False
        for mapping in mappings:
            external = int(mapping['HostPort'])
            try:
                address = (hostname, external)
                log.debug('connecting: %s:%d', *address)
                conn = create_connection(address, 5)
                log.debug('connected: %s:%d', *address)
            except IOError, e:
                log.debug('failed to connect: %s', e)
                return False
            else:
                conn.close()
    return True


def destroy_containers(client, nametag):
    timeout = time() + 60 * 60
    try:
        if os.fork():
            return
    except OSError, e:
        log.debug('failed to fork: %s', e)
        return

    while time() < timeout:
        sleep(1)
        containers = client.list_containers(needle=nametag, _all=True)
        if not containers:
            break
        containers = client.list_containers(needle=nametag)
        for container in containers:
            try:
                client.kill(container)
            except Exception, e:
                log.debug('kill failed: %s', e)
        containers = client.list_all_exited(needle=nametag)
        for container in containers:
            try:
                client.destroy(container)
            except Exception, e:
                log.debug('destroy failed: %s', e)
        sleep(99)
    if time() > timeout:
        log.debug('Reached timeout for container destroy')

def endpoint_address(endpoint):
    if '://' not in endpoint:
        endpoint = 'tcp://' + endpoint
    return urlparse(endpoint).hostname or 'localhost'
