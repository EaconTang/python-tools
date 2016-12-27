#!/usr/bin/env python
import json
import sys

from pexpect import pxssh
from remote import Multihop


def main():
    args = sys.argv
    if len(args) == 2:
        if args[1] == '-l':
            list_host()
        else:
            ssh(args[1])
    else:
        usage = '\tUsage: pyssh [ -l | <host> | <alias> ]\n'
        print(usage)


def ssh(host):
    config = load_config()
    if host not in config.keys():
        # alias maybe
        for _ in config.keys():
            if host == config.get(_).get('alias'):
                _host = _
                break
    else:
        _host = host

    host_info = config.get(_host)
    user = host_info.get('username', '')
    pwd = host_info.get('password', '')
    proxy = host_info.get('proxy', '')

    if not proxy:
        ssh = pxssh.pxssh()
        if ssh.login(_host, user, pwd):
            print('######## Login Success! ########')
            try:
                ssh.interact()
            except Exception as e:
                print('Exception occur: \n\t' + str(e))
                sys.exit('######## Logout! ########')
            #
            # while True:
            #     _in = raw_input('[{}@{}]: '.format(user, host))
            #     ssh.sendline(_in)
            #     ssh.prompt()
            #     print '\n'.join(ssh.before.split('\n')[1:])
        else:
            raise Exception('Fail to login!')
    else:
        proxy_info = config.get(proxy)
        intermedia = dict(host=proxy, user=proxy_info['username'], password=proxy_info['password'], type='ssh')
        dest = dict(host=_host, user=user, password=pwd, type='ssh')
        ssh = Multihop(hops_info=(intermedia, dest))
        try:
            ssh.login()
            print('######## Login Success! ########')
            ssh.interactive()
        except Exception as e:
            print('Exception occur: \n\t' + str(e))
            sys.exit('######## Logout! ########')


def ssh_input_filter(_in):
    if _in == 'ls':
        return 'ls -l'
    return _in


def ssh_output_filter(_out):
    return _out + '\n'


def load_config():
    with open('/Users/eacon/github/python-tools/ssh/account.json') as f:
        conf = f.read()
    conf_dict = json.loads(conf)
    return conf_dict


def list_host():
    config = load_config()
    _out = '{:^24}|{:^24}|{:^24}'
    record = [_out.format('Host', 'User', 'Alias'), '-' * (24 * 3 + 2)]
    for host, info in config.iteritems():
        record.append(_out.format(host, info.get('username', ''), info.get('alias', '')))
    print('\n'.join(record))


if __name__ == '__main__':
    main()
