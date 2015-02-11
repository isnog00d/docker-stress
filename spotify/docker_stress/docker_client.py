import logging
from json import loads
from os import environ
from subprocess import Popen, PIPE


log = logging.getLogger(__name__)


DEFAULT_DOCKER_ENDPOINT = environ.get('DOCKER_HOST', 'unix:///var/run/docker.sock')

try:
    p = Popen('which docker', stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    if p.returncode:
        raise Exception()
    DEFAULT_DOCKER_CLI = out.strip()
except:
    DEFAULT_DOCKER_CLI = '/usr/bin/docker'


def escape(word):
    if ' ' in word:
        return "'%s'" % (word, )
    else:
        return word


class DockerClientError(Exception):
    pass


class CliDockerClientError(DockerClientError):
    def __init__(self, command, code, out, err):
        super(CliDockerClientError, self).__init__()
        self.command = command
        self.code = code
        self.out = out
        self.err = err

    def __str__(self):
        return 'docker command failed: %s (%d) out=(%s) err=(%s)' % (self.command, self.code, self.out, self.err)


class CliDockerClient(object):
    def __init__(self, docker=None, endpoint=None):
        super(CliDockerClient, self).__init__()
        self.docker = docker or DEFAULT_DOCKER_CLI
        self.endpoint = endpoint or DEFAULT_DOCKER_ENDPOINT

    def cli(self, *args):
        command = (self.docker, '-H=%s' % self.endpoint) + tuple(args)
        log.debug('cli: %s', command)
        log.debug('cli: shell style: %s', ' '.join(escape(word) for word in command))
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        log.debug('%d %s %s', p.returncode, out, err)
        return p.returncode, out, err

    def cli_check(self, *args):
        code, out, err = self.cli(*args)
        if code:
            raise CliDockerClientError(args, code, out, err)
        return out

    def inspect_container(self, container_id):
        log.debug('inspect_container %s', container_id)
        code, out, err = self.cli('inspect', container_id)
        return loads(out)

    def start_new(self, image=None, command=None, ports=None, name=None):
        log.debug('start_new %s', image)
        assert image
        ports = ports or []
        command = command or []
        args = []
        args.extend('-p=%d' % port for port in ports)
        if name:
            args.append('--name=%s' % (name, ))
        args.append(image)
        args.extend(command)
        return self.cli_check('run', '-d', *args).strip()

    def start(self, container_id):
        log.debug('start %s', container_id)
        self.cli_check('start', container_id)

    def stop(self, container_id):
        log.debug('stop %s', container_id)
        self.cli_check('stop', container_id)

    def kill(self, container_id):
        log.debug('kill %s', container_id)
        self.cli_check('kill', container_id)

    def destroy(self, container_id):
        log.debug('destroy %s', container_id)
        self.cli_check('rm', container_id)

    def list_containers(self, needle='', _all=False):
        if not needle:
            return self.cli_check('ps', '-q').splitlines()
        else:
            if _all:
                lines = self.cli_check('ps', '-a').splitlines()[1:]
            else:
                lines = self.cli_check('ps').splitlines()[1:]
            matches = [word for line in lines for word in line.split() if needle in word]
            log.debug('list_containers: needle=%s, matches=%s', needle, matches)
            return matches

    def list_all_exited(self, needle):
	lines = self.cli_check('ps', '-a').splitlines()[1:]
	lines = [line for line in lines if 'Exited' in line]
	matches = [word for line in lines for word in line.split() if needle in word]
	return matches
