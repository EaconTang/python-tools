#!/usr/bin/env python3
'''Remote is a Python module for automating applications which interactive with the remote hosts.

Features:
1) A plain-text password database implementation:
PasswordXmlDb
2)  Automatically enter password when necessary. It's designed for SSH based commands: scp/rsync(uses ssh for its communications)/ssh(executing a command on the remote host instead of a login shell).
auto_password()
3) A library for interactiving with the remote shell (SSH/RSH/TELNET). There is a SSH wrapper, named pxssh, in the pexpect module, but its features are limited.
RemoteShell, SshHost, TelnetHost, Multihop
4) Wrappers for FTP related commands (lftp, sftp):
AbstractFtp, Lftp, Sftp
Princple of error handling in this module:
1) Synchronize to the shell prompt after an failed action in order to avoid losing the way.
2) Don't raise exception for normal errors such as incorrect password and timeout. Return values are easier to handle than exceptions.
'''
import os.path
import re
import sys

import pexpect


class PasswordXmlDb(object):
    '''This is a plain-text password database implementation at my will. The database is a XML file which looks like following::
        <xml>
            <host name='probe'>
                <user name='geo' passwd='geo.geo'/>
                <user name='root' passwd='inetinet'/>
                <host name='node'>
                    <user name='geo' passwd='geo.geo'/>
                    <user name='root' passwd='inetinet'/>
                </host>
                <host name='switch'>
                    <user name='root' passwd='inetinet'/>
                </host>
            </host>
            <host name='genet'>
                <user name='zhichyu' passwd='ABCDE'/>
                <user name='root' passwd='inetinet'/>
            </host>
        </xml>
    Note that 1) The hierarchy of hosts should be constant with the login order. 2) The XML file's mode should be 600 for security.
    There are several XML/XPath libraries in Python. Lxml (http://codespeak.net/lxml/) seems to be the best one among non-standard libraries. However ElementTree is very simple (a stand Python library) and good enough for my case. Here's comparison of those libraries: http://www.oreillynet.com/onlamp/blog/2005/01/code_respecting_xpath_xml_pyth.html
    Examples
    ========
    Initialize the password database, and query it::
        passwd_db = PasswordXmlDb.parse('/tmp/passwd.xml')
        passwd = passwd_db.query('probe/switch','root')
    '''

    def __init__(self, passwd_db):
        self.db = passwd_db

    @staticmethod
    def parse(passwd_db_file):
        # ElementTree is introduced in by Python 2.5.
        from xml.etree import ElementTree
        assert (os.path.isfile(passwd_db_file))
        passwd_db = ElementTree.parse(passwd_db_file)
        return PasswordXmlDb(passwd_db)

    def query(self, host_path, username):
        host_path = host_path.strip().strip('/')
        hosts = host_path.split('/')
        assert (len(hosts) >= 1)
        assert (self.db != None)
        e_curr = self.db.getroot()
        for host in hosts:
            e_host = None
            for e in e_curr.findall('host'):
                if (e.get('name') == host):
                    e_host = e
                    break
            if (e_host == None):
                return None
            e_curr = e_host
        e_user = None
        for e in e_curr.findall('user'):
            if (e.get('name') == username):
                e_user = e
                break
        if (e_user == None):
            return None
        return e_user.get('passwd')


def auto_password(pexpect_session, password, context_shell=None):
    '''Automatically enter password when necessary. It's designed for SSH based commands: scp/rsync(uses ssh for its communications)/ssh(executing a command on the remote host instead of a login shell).

    The comman things of above commmands:
    1) Running program will not go into a login shell. So that I CANN'T REUSE this function in SshHost.login().
    2) The password/passphrase prompt may or may not occur.
    3) If password/passphrase is incorrect, the password/passphrase prompt will occur again.
    Return value is (status, part_output). status::
        0  - authentication succeeded, or been skipped
        -1 - command not found, or connection failed
        -2 - authentication failed
    part_output::
        The output before authentication readed so far when status is 0. None when status is not 0.
    If the status is not 0, the pexpect session has been closeed appropriately after the function quit.
    An example of passphase:
        zhichyu@w-shpd-zcyu:~$ ssh zhichyu@genet
        Enter passphrase for key '/home/zhichyu/.ssh/id_rsa':
        Enter passphrase for key '/home/zhichyu/.ssh/id_rsa':
        Enter passphrase for key '/home/zhichyu/.ssh/id_rsa':
        zhichyu@192.158.124.249's password:
        Permission denied, please try again.
        zhichyu@192.158.124.249's password:
        Last login: Wed Dec 16 10:37:32 2009 from w-shpd-zcyu.global.tektronix.net
        zhichyu@sh-plat-genet:~>
    '''
    patt_end = None
    if (context_shell == None):
        patt_end = pexpect.EOF
    else:
        patt_end = context_shell.prompt
    r = pexpect_session.expect(
        ['(?mi)command not found', '(?mi)No route to host', '(?mi)Name or service not known', '(?mi)Connection refused',
         '(?i)Host key verification failed', 'continue connecting.*\? ', '(?i)password: |passphrase for key', patt_end])
    if (r == 0 or r == 1 or r == 2 or r == 3 or r == 4):
        _close_session(pexpect_session, context_shell, 0)
        return (-1, None)
    if (r == 7):
        # Running program exited before prompting for the password.
        return (0, pexpect_session.before)
    elif (r == 5):
        pexpect_session.sendline('yes')
        # The 'continue connecting.*\? ' may occur zero to two times.
        r = pexpect_session.expect(['(?i)password: |passphrase for key', patt_end, 'continue connecting.*\? '])
        if (r == 2):
            pexpect_session.sendline('yes')
            r = pexpect_session.expect(['(?i)password: |passphrase for key', patt_end])
        if (r == 1):
            return (0, pexpect_session.before)
    # Reachs the password/passphrase prompt
    _send_pass(pexpect_session, password)
    # Consumes '\r\n' caused by _send_pass()
    pexpect_session.expect('\r\n')
    # The line "Permission denied, please try again." may or may not occur before the password/passphrase prompt.
    r = pexpect_session.expect(['(?i)password: $|passphrase for key', 'please try again', '\r\n', patt_end])
    if (r == 1):
        # Consumes '\r\n' of the line "please try again."
        pexpect_session.expect('\r\n')
        r = pexpect_session.expect(['(?i)password: $|passphrase for key'])
    if (r == 0):
        # The password/passphrase prompt occurs again.
        _close_session(pexpect_session, context_shell, 1)
        return (-2, None)
    part_output = pexpect_session.before
    if (r == 2):
        part_output += '\r\n'
    return (0, part_output)


def _close_session(pexpect_session, context_shell, session_state=2):
    '''End the session.
    session_state::
        0 - At the context shell prompt, and the prompt can be expected.
        1 - At authentication stage, has not reach the remote shell prompt.
        2 - At the remote shell prompt.
    '''
    assert (pexpect_session != None)
    if (context_shell != None):
        assert (pexpect_session == context_shell.s)
    if (session_state == 0):
        pass
    elif (session_state == 1):
        # Note that sendline('\x03') outputs the prompt exactly two times.
        pexpect_session.sendcontrol('C')
    elif (session_state == 2):
        pexpect_session.sendline('exit')
        '''
        Make sure we really exited in order not to lose the way.
        Sometimes the remote shell outputs its prompt again just before exit:
geouser@chinalab /home/geouser 2 > exit
geouser@chinalab /home/geouser 3 > logout
Connection to sunfire closed.
        # Connection to genet closed.
        # Connection closed by foreign host.
        # Connection to xxx closed by foreign host.
        Note that there may be some control characters before and/or after the message.
        So don't place '^' at the begining of the pattern!
        '''
        pexpect_session.expect('(?mi)Connection .*closed')
    if (context_shell == None):
        pexpect_session.read()
        pexpect_session.close()
    else:
        pexpect_session.expect(context_shell.prompt)


def _send_pass(s, password=None):
    '''Send password but don't log this action. Note that pexpect.spawn.setecho(False) doesn't help.'''
    if (password is None):
        raise Exception('password is None!')
    logfile = s.logfile
    s.logfile = None
    s.sendline(password)
    s.logfile = logfile


def _strip_term_output(output):
    '''Strip things caused by the terminal and get the real output of the command.
    The first line is the echoed input by the pty created by pepexct. It ends with '\\r\\n' and may contains '\\r' if it's length is over 80. Other lines are the exact output of the command. The '\\r\\n' of the last line is also stripped.
    Notes:
    (1) splitlines() treats '\\r\\n', '\\r' and '\\n' as line end. However split('\\r\\n') treats "\\r\\n" as line end.
    (2) 'a\\r\\n'.split('\\r\\n')==>['a','']
    '''
    output = output.strip()
    first_n = output.find('\n')
    if (first_n == -1):
        return ''
    return output[first_n + 1:]


class UserInfo:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password


# Use new-style classes (deriving directly or indirectly from object) for all new code.
class RemoteShell(object):
    '''Base class for all remote shell wrappers.
    '''
    GENERIC_PATT_PROMPT = re.compile('(?m)^[^\n]*[\$>#] ')

    def __init__(self, host, user, password, context_shell=None):
        self.userinfo = UserInfo(host, user, password)
        self.context_shell = context_shell
        self.s = None
        self.prompt = None
        self.prompt_stack = list()
        self.user_stack = list()
        self._bash_path = None
        self._hostname = None

    def _push_prompt(self, prompt):
        self.prompt_stack.append(prompt)
        self.prompt = prompt

    def _pop_prompt(self):
        del self.prompt_stack[-1:]
        if (len(self.prompt_stack) > 0):
            self.prompt = self.prompt_stack[-1]
        else:
            self.prompt = None

    def _close_session(self, session_state=2):
        '''session_state::
            0 - At the context shell prompt.
            1 - At authentication stage, has not reach the remote shell prompt.
            2 - At the remote shell prompt.
        '''
        _close_session(self.s, self.context_shell, session_state)
        self.s = None
        self.prompt = None
        del self.prompt_stack[:]
        del self.user_stack[:]

    def docmd(self, cmd, timeout=60):
        '''Execute cmd in the remote shell and return its output.
        Return None if it's still running when timeout expired.
        timeout None means no timeout limit, -1 means self.s.timeout.
        '''
        assert self.s != None
        try:
            self.s.sendline(cmd)
            self.s.expect(self.prompt, timeout=timeout)
            output = _strip_term_output(self.s.before)
            return output
        except pexpect.TIMEOUT:
            self.s.sendcontrol('C')
            self.s.expect(self.prompt)
            return None

    def interactive(self):
        """"""
        assert self.s != None
        try:
            self.s.interact()
        except pexpect.ExceptionPexpect as e:
            print('Exception occur: \n\t' + str(e))
            sys.exit('######## Logout! ########')

    def _login_timely(self):
        raise NotImplementedError('RemoteShell._login_timely is an abstract method.')

    def login(self, robust=False):
        '''Return value:
            0  - OK
            -1 - command not found
            -2 - connection failed or refused
            -3 - authentication failed
            -4 - robust steps failed. This error can occur only when robust is True.
            -5 - timeout. ssh and telnet may get blocked forever before authentication if the remote host is at a strange state.
        '''
        session_state = 0
        try:
            session_state = 1
            iret = self._login_timely()
            if (iret < 0):
                return iret
            self._push_prompt(self.GENERIC_PATT_PROMPT)
            self.user_stack.append(self.userinfo.user)
            session_state = 2
            if (robust):
                iret = self.robust_steps()
                if (iret < 0):
                    self._pop_prompt()
                    del self.user_stack[-1:]
                    return -4
        except pexpect.TIMEOUT:
            # import traceback
            # traceback.print_exc()
            self._close_session(session_state)
            return -5
        return 0

    def logout(self):
        assert (self.s != None)
        # Quit users automatically. Cool? :)
        for i in range(0, len(self.prompt_stack) - 1):
            self.quit_user()
        assert (len(self.prompt_stack) == 1)
        assert (len(self.user_stack) == 1)
        self._close_session()

    def switch_user(self, other_user, other_pass, robust=False):
        '''Return value:
            0  - OK
            -1 - unknown id
            -2 - incorrect password
            -3 - robust steps failed. This error can occur only when robust is True.
        '''
        assert self.s != None
        self.s.sendline('su - %s' % other_user)
        r = self.s.expect(['(?i)Unknown id:', '(?i)password: ', self.GENERIC_PATT_PROMPT])
        if (r == 0):
            self.s.expect(self.prompt)
            return -1
        elif (r == 2):
            self._push_prompt(self.GENERIC_PATT_PROMPT)
            self.user_stack.append(other_user)
            if (robust):
                iret = self.robust_steps()
                if (iret < 0):
                    self._pop_prompt()
                    del self.user_stack[-1:]
                    return -3
            return 0
        # Reachs the password prompt.
        _send_pass(self.s, other_pass)
        r = self.s.expect(['(?i)authentication failure', '(?i)su: Sorry', self.GENERIC_PATT_PROMPT])
        if (r == 0 or r == 1):
            self.s.expect(self.prompt)
            return -2
        self._push_prompt(self.GENERIC_PATT_PROMPT)
        self.user_stack.append(other_user)
        if (robust):
            iret = self.robust_steps()
            if (iret < 0):
                self._pop_prompt()
                del self.user_stack[-1:]
                return -3
        return 0

    def quit_user(self):
        assert self.s != None
        assert (len(self.prompt_stack) > 1)
        self.s.sendline('exit')
        self._pop_prompt()
        self.sync_prompt()
        del self.user_stack[-1]

    def robust_steps(self):
        '''Make the session more robust:
        1) Switch to Bash if current shell is not Bash. Csh and other shells are hard to use. Bash is widely available on nowadays UNIX-like systems.

        2) Force sending SIGHUP to jobs when logout. See https://bugzilla.mindrot.org/show_bug.cgi?id=52(Comment 23,35,43 => OpenSSH-4.6p1), http://www.snailbook.com/faq/background-jobs.auto.html(shopt can not fix the xterm example, I have to do "jobs -p | xargs kill -9" before logoout). FYI, on the other side, disown can be used to mark some jobs so that SIGHUP is not sent to the job if the shell receives a SIGHUP.
        3) Make sure all commands' output are in English. Otherwise pexpect is very likely to be stuck.
        4) Set the shell prompt to something more unique than # or $. This makes it easier for the sync_prompt() method to match the shell prompt unambiguously.
        '''
        assert (self.s != None)
        # Solaris is strange:
        # 1) The default shell is the outdated Csh.
        # 2) Neither /sbin/sh nor /usr/bin/bash doesn't support export.
        # 3) whoami, bash are not at the standard location.
        # So use Bash whenever possible!
        shell_name = self.docmd('echo $0')
        if (not shell_name.endswith('/bash')):
            if (self._bash_path == None):
                bash_path = self.docmd('which bash')
                if (bash_path == '' or bash_path.find(' ') >= 0):
                    return -1
                self._bash_path = bash_path
            cmd_bash = 'exec %s --login' % self._bash_path
            self.s.sendline(cmd_bash)
            self.s.expect(self.GENERIC_PATT_PROMPT)
            self._pop_prompt()
            self._push_prompt(self.GENERIC_PATT_PROMPT)
        # Force sending SIGHUP to jobs when logout.
        self.docmd('shopt -s huponexit')
        # Make sure all commands/applications' output are in English.
        self.docmd('export LC_MESSAGES="POSIX"')
        # Set unique prompt
        if (self._hostname == None):
            hostname = self.docmd('hostname')
            self._hostname = hostname
        unique_prompt = '%s@%s_PEXPECT> ' % (self.user_stack[-1], self._hostname)
        patt_unique_prompt = re.compile('(?m)^' + re.escape(unique_prompt))
        self.docmd('unset PROMPT_COMMAND')
        cmd_set_sh = 'PS1="%s"' % unique_prompt
        self.s.sendline(cmd_set_sh)
        # Note that the echoed input also matchs the unique_prompt.
        self.s.expect('PS1=.*\r\n')
        self.s.expect(patt_unique_prompt)
        self._pop_prompt()
        self._push_prompt(patt_unique_prompt)
        return 0

    def sync_prompt(self):
        assert (self.s != None)
        self.s.expect(self.prompt)


class SshHost(RemoteShell):
    def __init__(self, host, user, password, context_shell=None, logfile=None, ssh_path=None):
        # Note: super() only return the first parent class!!!
        super(SshHost, self).__init__(host, user, password, context_shell)
        self.logfile = logfile
        if (ssh_path != None):
            self.ssh_path = ssh_path
        else:
            self.ssh_path = 'ssh'
        if (context_shell != None):
            assert (logfile == None)

    def _login_timely(self):
        assert (self.s == None)
        if self.userinfo.user == '':
            userhost = self.userinfo.host
        else:
            userhost = self.userinfo.user + '@' + self.userinfo.host
        if (self.context_shell == None):
            # Attention: pexpect.run(cmd) will execute only the first commond in cmd.
            self.s = pexpect.spawn('%s %s' % (self.ssh_path, userhost), logfile=self.logfile)
        else:
            self.s = self.context_shell.s
            self.s.sendline('%s %s' % (self.ssh_path, userhost))
        # s.setecho(False) doesn't make sence
        # Some hosts don't output "Last login: ".
        r = self.s.expect(
            ['(?mi)not found', '(?mi)No route to host', '(?mi)Name or service not known', '(?mi)Connection refused',
             '(?i)Host key verification failed', 'continue connecting.*\? ', '(?i)password: |passphrase for key',
             self.GENERIC_PATT_PROMPT])
        if (r == 0 or r == 1 or r == 2 or r == 3 or r == 4):
            self._close_session(0)
            if (r == 0):
                iret = -1
            else:
                iret = -2
            return iret
        elif (r == 7):
            return 0
        elif (r == 5):
            self.s.sendline('yes')
            # The 'continue connecting.*\? ' may occur zero to two times.
            r = self.s.expect(
                ['(?i)password: |passphrase for key', self.GENERIC_PATT_PROMPT, 'continue connecting.*\? '])
            if (r == 2):
                self.s.sendline('yes')
                r = self.s.expect(['(?i)password: |passphrase for key', self.GENERIC_PATT_PROMPT])
            if (r == 1):
                return 0
        # Reachs the password/passphrase prompt
        _send_pass(self.s, self.userinfo.password)
        r = self.s.expect(['(?i)password: |passphrase for key', self.GENERIC_PATT_PROMPT])
        if (r == 0):
            self._close_session(1)
            return -3
        return 0


class TelnetHost(RemoteShell):
    def __init__(self, host, user, password, context_shell=None, logfile=None, telnet_path=None):
        super(TelnetHost, self).__init__(host, user, password, context_shell)
        self.logfile = logfile
        if (telnet_path != None):
            self.telnet_path = telnet_path
        else:
            self.telnet_path = 'telnet'
        if (context_shell != None):
            assert (logfile == None)

    def _login_timely(self):
        assert (self.s == None)
        if (self.context_shell == None):
            self.s = pexpect.spawn('%s %s' % (self.telnet_path, self.userinfo.host), logfile=self.logfile)
        else:
            self.s = self.context_shell.s
            self.s.sendline('%s %s' % (self.telnet_path, self.userinfo.host))
        r = self.s.expect(
            ['(?mi)not found', '(?mi)No route to host', '(?mi)Connection refused', '(?mi)Connection .*closed',
             '(?i)(?<!last )login: |Username: '])
        if (r == 0 or r == 1 or r == 2 or r == 3):
            self._close_session(0)
            if (r == 0):
                iret = -1
            else:
                iret = -2
            return iret
        # Reachs the username prompt.
        self.s.sendline(self.userinfo.user)
        r = self.s.expect(['(?mi)Connection .*closed', '(?i)password: '])
        if (r == 0):
            self._close_session(0)
            return -2
        # Reachs the password prompt.
        _send_pass(self.s, self.userinfo.password)
        r = self.s.expect(['(?mi)Connection .*closed', '(?i)(?<!last )login: |Username: ', self.GENERIC_PATT_PROMPT])
        if (r == 0):
            self._close_session(0)
            return -2
        elif (r == 1):
            # Solaris is strange: Not Ctrl-C but Ctrl-D causes the telnet server close the connection.
            # self._close_session(1) doesn't work if the telnet server is on Solaris.
            while (1):
                self.s.sendline(self.userinfo.user)
                self.s.expect(['(?i)password: '])
                _send_pass(self.s, self.userinfo.password)
                r = self.s.expect(['(?mi)Connection .*closed', '(?i)(?<!last )login: |Username: '])
                if (r == 0):
                    break
            self._close_session(0)
            return -3
        return 0


class Multihop(RemoteShell):
    '''The wrapper for the remote shell of a host between which and localhost are multi hops and each hop is a SSH/Telnet server.
    TODO: Ssh/Telnet outputs "Connection closed by foreign host." when the remote host crashed. How to determine which hop crashed in Multihop? Or is it possible?
    Examples
    ========
    The switch 192.168.1.15 is only reachable from x2. Run "upname" on switch::
        log_file = open('remote.log','wb')
        x2 = dict(host='x2',user='geo',password='geo.geo',type='telnet')
        switch = dict(host='192.168.1.15',user='root',password='inetinet',type='ssh')
        hops_info = (x2,switch)
        shell = Multihop(hops_info, logfile=log_file)
        shell.login()
        shell.docmd('uname -a')
        shell.logout()
        log_file.close()
    '''

    def __init__(self, hops_info, context_shell=None, logfile=None):
        '''Multihop is intentionally designed to be a proxy of the last hop. Multihop's data and method members:
        1) login()/logout()/hops,
        2) All method members of RemoteShell,
        3) Access to other members are dispatched to the last hop.
        So it's not appropriate to initialize any base class here.
        '''
        assert (len(hops_info) >= 1)
        if (context_shell != None):
            assert (logfile == None)
        self.hops = list()
        curr_context = context_shell
        for hop in hops_info:
            hop_type = hop['type']
            assert (hop_type == 'ssh' or hop_type == 'telnet')
            if (hop['type'] == 'ssh'):
                shell = SshHost(hop['host'], hop['user'], hop['password'], curr_context, logfile)
            elif (hop['type'] == 'telnet'):
                shell = TelnetHost(hop['host'], hop['user'], hop['password'], curr_context, logfile)
            else:
                pass
            self.hops.append(shell)
            curr_context = shell
            logfile = None

    def login(self, robust=False):
        # Don't need assertion here since there are some of them in every hop.
        b_robust = False
        for ind in range(0, len(self.hops)):
            # Doing robust steps on intermediate hops doesn't make sence.
            if (ind == len(self.hops) - 1):
                b_robust = robust
            iret = self.hops[ind].login(robust=b_robust)
            if (iret != 0):
                for ind2 in range(ind - 1, -1, -1):
                    self.hops[ind2].logout()
                return iret
        return 0

    def logout(self):
        # Don't need assertion here since there are some of them in every hop.
        for hop in reversed(self.hops):
            hop.logout()

    def __getattr__(self, name):
        # Member access dispatching.
        # print('Multihop::__getattr__(self, %s)'%str(name))
        return self.hops[-1].__getattribute__(name)


class AbstractFtp(object):
    def __init__(self, host, user, password, context_shell=None, logfile=None):
        if (context_shell != None):
            assert (logfile == None)
        self.context_shell = context_shell
        self.userinfo = UserInfo(host, user, password)
        self.logfile = logfile
        self.s = None
        self.prompt = re.compile('(?m)^[^\n]*[\$>#] ')

    def _close_session(self, session_state=2):
        '''
        session_state:
        0 - At the context shell prompt.
        1 - At authentication stage, has not reach the remote shell prompt.
        2 - At the remote shell prompt.
        '''
        _close_session(self.s, self.context_shell, session_state)
        self.s = None

    def login(self):
        raise Exception('Not impl.')

    def logout(self):
        assert self.s != None
        self.s.sendline('exit')
        if (self.context_shell == None):
            self.s.readlines()
            self.s.close()
        else:
            self.s.expect(self.context_shell.prompt)
        self.s = None

    def _docmd(self, cmd, timeout):
        assert self.s != None
        self.s.sendline(cmd)
        self.s.expect(self.prompt, timeout=timeout)
        output = _strip_term_output(self.s.before)
        return output

    def put(self, lfile, rfile, timeout=60 * 3):
        # Note: Every lines of Lftp/Sftp get/put's output are progress related and ends with '\r'.
        cmd = 'put %s %s' % (lfile, rfile)
        self._docmd(cmd, timeout)

    def get(self, rfile, lfile, timeout=60 * 3):
        cmd = 'get %s %s' % (rfile, lfile)
        self._docmd(cmd, timeout)


class Lftp(AbstractFtp):
    def __init__(self, host, user, password, context_shell=None, logfile=None):
        AbstractFtp.__init__(self, host, user, password, context_shell, logfile)
        self.prompt = re.compile('(?m)^.+> ')

    def login(self):
        assert (self.s == None)
        lftp_cmd = 'lftp sftp://%s@%s' % (self.userinfo.user, self.userinfo.host)
        if (self.context_shell == None):
            self.s = pexpect.spawn(lftp_cmd, logfile=self.logfile)
        else:
            self.s = self.context_shell.s
            self.s.sendline(lftp_cmd)
        r = self.s.expect('(?i)password: ')
        _send_pass(self.s, self.userinfo.password)
        # Attention: 'ls' output is async with the input and outputs exact prompt two times!
        self.s.sendline('ls')
        r = self.s.expect(['Login failed', '[Done]'])
        if (r == 0):
            self._close_session()
            return -1
        assert r == 1
        self.s.expect(self.prompt)
        return 0

    def get(self, rfile, lfile, timeout=60 * 3):
        cmd = 'pget -c %s -o %s' % (rfile, lfile)
        super(Lftp, self)._docmd(cmd, timeout)


class Sftp(AbstractFtp):
    def __init__(self, host, user, password, context_shell=None, logfile=None):
        AbstractFtp.__init__(self, host, user, password, context_shell, logfile)
        self.prompt = re.compile('(?m)^sftp> ')

    def login(self):
        assert (self.s == None)
        sftp_cmd = 'sftp %s@%s' % (self.userinfo.user, self.userinfo.host)
        if (self.context_shell == None):
            self.s = pexpect.spawn(sftp_cmd, logfile=self.logfile)
        else:
            self.s = self.context_shell.s
            self.s.sendline(sftp_cmd)
        r = self.s.expect(['(?i)password: ', 'continue connecting.*\?'])
        if (r == 1):
            self.s.sendline('yes')
            r = self.s.expect(['(?i)password: '])
        # Reachs the password prompt.
        _send_pass(self.s, self.userinfo.password)
        r = self.s.expect(['(?i)password: ', self.prompt])
        if (r == 0):
            self._close_session(1)
            return -1
        return 0


def _test_passwd_db():
    f = open('/tmp/passwd.xml', 'w')
    f.write('''
<xml>
  <host name='probe'>
    <user name='geo' passwd='geo.geo'/>
    <user name='root' passwd='inetinet'/>
      <host name='node'>
        <user name='geo' passwd='geo.geo'/>
        <user name='root' passwd='inetinet'/>
      </host>
      <host name='switch'>
        <user name='root' passwd='inetinet'/>
      </host>
  </host>
  <host name='genet'>
    <user name='zhichyu' passwd='ABCDE'/>
    <user name='root' passwd='inetinet'/>
  </host>
</xml>
''')
    f.close()
    import stat
    os.chmod('/tmp/passwd.xml', stat.S_IRUSR | stat.S_IWUSR)
    passwd_db = PasswordXmlDb.parse('/tmp/passwd.xml')
    passwd = passwd_db.query('probe/switch', 'root')
    assert (passwd == 'inetinet')
    passwd = passwd_db.query('/genet/', 'zhichyu')
    assert (passwd == 'ABCDE')
    passwd = passwd_db.query('genet', 'cren')
    assert (passwd == None)
    passwd = passwd_db.query('switch', 'root')
    assert (passwd == None)


def _test_auto_password():
    LOG_FILE = 'remote.log'
    import subprocess
    subprocess.getstatusoutput('rm -fr %s' % LOG_FILE)
    log_file = open(LOG_FILE, 'wb+')

    # Good command line:
    rsync_cmd = 'rsync -avzp --include=*/ --include=*.py --exclude=* zhichyu@192.158.124.249:/home/zhichyu/probe/v6/ /home/zhichyu/tmp/'
    # Bad command line:
    #    rsync_cmd = 'rsync -avzp --include=*/ --include=*.py --exclude=* geo@x2:/inet/zhichyu/src/ /home/zhichyu/tmp/'
    #    rsync_cmd = 'rsync -avzp --include=*/ --include=*.py --exclude=* zhichyu@192.158.124.1:/home/zhichyu/probe/v6/ /home/zhichyu/tmp/'
    print(rsync_cmd)
    sess = pexpect.spawn(rsync_cmd, logfile=log_file)
    iret, part_output = auto_password(sess, 'geo.geo', None)
    if (iret != 0):
        # The pexpect session has been closeed appropriately.
        if (iret == -1):
            print('Rsync connection failed!')
        else:
            print('Rsync authentication failed!')
    else:
        sess.read()
        sess.close()
    log_file.close()


def _test_multihop():
    LOG_FILE = 'remote.log'
    import subprocess
    subprocess.getstatusoutput('rm -fr %s' % LOG_FILE)
    log_file = open(LOG_FILE, 'wb+')

    genet = dict(host='192.158.124.249', user='geo', password='geo.geo', type='ssh')
    x2 = dict(host='192.158.124.137', user='geo', password='geo.geo', type='telnet')
    shell = Multihop((genet, x2), logfile=log_file)
    # Verify member access dispatching. Use "identity equality" here.
    assert (id(shell.userinfo) == id(shell.hops[-1].userinfo))
    shell.login(robust=True)
    shell.docmd('uname -a')
    shell.switch_user('root', 'inetinet')
    shell.docmd('ost')
    shell.logout()

    log_file.write(b'done.\n')
    log_file.close()
    print('done.')


def _test_solaris_telnet():
    LOG_FILE = 'remote.log'
    import subprocess
    subprocess.getstatusoutput('rm -fr %s' % LOG_FILE)
    log_file = open(LOG_FILE, 'wb+')
    # Correct password
    h1 = TelnetHost('sunfire', 'geouser', 'geouser', logfile=log_file)
    iret = h1.login(True)
    assert (iret == 0)
    h1.logout()
    # Incorrect password
    h1 = TelnetHost('sunfire', 'geouser', 'geo', logfile=log_file)
    iret = h1.login()
    assert (iret == -3)
    # Root login
    h1 = TelnetHost('sunfire', 'root', 'geouser', logfile=log_file)
    iret = h1.login(True)
    assert (iret == -2)
    log_file.close()


def _test_unique_prompt():
    import time
    time_start = time.time()
    LOG_FILE = 'remote.log'
    import subprocess
    subprocess.getstatusoutput('rm -fr %s' % LOG_FILE)
    log_file = open(LOG_FILE, 'wb+')
    h1 = SshHost('sunfire', 'geouser', 'geouser', logfile=log_file)
    h1.login(True)
    ssh_path = h1.docmd('which ssh')
    h1.switch_user('root', 'geoprobe', True)
    h2 = SshHost('xformer2', 'geo', 'geo.geo', h1)
    iret = h2.login(True)
    if (iret < 0):
        h2 = SshHost('xformer2', 'geo', 'geo.geo', h1, ssh_path=ssh_path)
        iret = h2.login(True)
    h2.switch_user('root', 'inetinet')
    h2.logout()
    h2.login()
    h2.switch_user('root', 'inetinet')
    uptime = h2.docmd('uptime')
    print('uptime of xformer2: ', uptime)
    h2.quit_user()
    h2.logout()
    h2 = TelnetHost('xformer2', 'geo', 'geo.geo', h1)
    h2.login(True)
    h2.logout()
    h1.logout()
    log_file.close()
    time_end = time.time()
    print('done in %s minutes.' % str((time_end - time_start) / 60.0))


'''   h1 = SshHost('127.0.0.1', 'zhichyu', 'sub5f@ct', logfile=log_file)
   h2 = SshHost('127.0.0.1', 'zhichyu', 'sub5f@ct', h1)
   h1.login(True)
   uptime = h1.docmd('uptime')
   print 'uptime: ', uptime
   h1.switch_user('root', 'inetinet')
   uptime = h1.docmd('uptime')
   print 'uptime_root: ', uptime
   h1.quit_user()
   uptime = h1.docmd('uptime')
   print 'uptime: ', uptime
   h2.login()
   h2.logout()
   h1.logout()
'''


def main():
    # _test_passwd_db()
    # _test_auto_password()
    # _test_multihop()
    # _test_unique_prompt()
    _test_solaris_telnet()


if __name__ == '__main__':
    main()
