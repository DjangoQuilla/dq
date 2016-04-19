from contextlib import contextmanager as _contextmanager
from fabric.context_managers import prefix
from fabric.operations import get, run, sudo
from fabric.state import env
from fabric.contrib import django
import boto3

django.project('dq')
from django.conf import settings

running_instances = []
s = boto3.session.Session(profile_name='dq')
ec2 = s.resource("ec2")

def get_ec2_instances():
    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    for i in instances:
        ssh_access = "ubuntu@{0}".format(i.public_ip_address)
        print 'servers >', ssh_access
        running_instances.append(ssh_access)

get_ec2_instances()

environments = {
    'production': {
        'hosts': running_instances,
        'source_code': '/home/ubuntu/www/dq.com/dq',
        'supervisor_commands': [
            'supervisorctl restart dq'
        ],
        'virtualenv': {
            'virtualenv_name': 'dq',
            'virtualenv_sh': '/usr/local/bin/virtualenvwrapper.sh',
        },
        'git': {
            'parent': 'origin',
            'branch': 'master',
        }
    }
}


# Utils
@_contextmanager
def virtualenv():
    """ Wrapper to run commands in the virtual env context """
    environment = environments['default']
    workon_home = environment['virtualenv'].get('workon_home',
                                                '~/.virtualenvs')
    with prefix('export WORKON_HOME={0}'.format(workon_home)):
        virtualenv_sh = environment['virtualenv'].get('virtualenv_sh',
                                                      '/etc/bash_completion.d/virtualenvwrapper')
        with prefix('source {0}'.format(virtualenv_sh)):
            virtualenv_name = environment['virtualenv'].get('virtualenv_name')
            with prefix('workon {0}'.format(virtualenv_name)):
                source_code = environment['source_code']
                with prefix('cd {0}'.format(source_code)):
                    yield


def django(command):
    with virtualenv():
        full_command = 'python manage.py {0}'.format(command)
        run(full_command)


# setup
def production():
    environments['default'] = environments['production']
    env.hosts = environments['production']['hosts']
    env.key_filename = 'djangoquilla.pem'

#tasks
def test_connection():
    run('free -m')


def git_pull():
    with virtualenv():
        run('git pull %s %s' % (environments['default']['git']['parent'],
                                environments['default']['git']['branch']))
        #run('git pull')


def pip_install():
    with virtualenv():
        run('pip install -r requirements.txt')


def pyclean():
    with virtualenv():
        run('find . -type f -name "*.py[co]" -exec rm -f \{\} \;')


def supervisor_restart():
    for supervisor in environments['default']['supervisor_commands']:
        sudo(supervisor)


def deploy():
    git_pull()
    pyclean()
    supervisor_restart()


"""
Filters=[
        {'Name': 'tag-key', 'Values': ['env']},
        {'Name': 'tag-value', 'Values': ['qa']},
        ]
"""