#!/usr/bin/env python
"""

"""
import os
import json
from optparse import OptionParser
from threading import Timer
import re
import time
import sys
import atexit
import signal
import logging

# make sure the access right
CONFIG_FILE = '/Users/eacon/github/python-tools/clock/clock.json'
PID_FILE = '/tmp/eacon-alarm.pid'
LOG_FILE = '/var/log/eacon-alarm.log'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)-15s [pid:%(process)d] [thread:%(threadName)s] [%(filename)s] [%(levelname)s] %(message)s",
)
LOG = logging.getLogger(__name__)


def main():
    """"""
    try:
        from apscheduler_alarm import SchedClocks
        if SchedClocks.is_available():
            # redirect _run_clocks() method
            _run_clocks = SchedClocks.run_clocks
        else:
            raise NotImplementedError
    except (ImportError, NotImplementedError):
        _run_clocks = run_clocks

    options = parse_args()
    if options.list_clock:
        LOG.info('List all alarm...')
        list_clocks()
    if options.status:
        show_status()

    if options.reload_conf:
        LOG.info('Reload...')
        stop_clocks()
        # defaults to daemon
        if not options.daemonize:
            options.daemonize = True
        # if not specified, defaults to run all
        if not options.run_all_clock and options.run_label is None:
            options.run_all_clock = True

    if options.daemonize:
        daemonize()
    if options.kill_ringtones:
        LOG.info('Stop music...')
        stop_music()
        return
    if options.kill_clocks:
        LOG.info('Stop all clocks...')
        stop_clocks()
        return
    save_pid(PID_FILE)
    if options.run_all_clock:
        LOG.info('Run all alarm...')
        loop_forever(24 * 60 * 60, _run_clocks, func_args=['all'])
        return
    if options.run_label is not None:
        LOG.info('Run alarm with label: {}'.format(options.run_label))
        loop_forever(24 * 60 * 60, _run_clocks, func_args=[str(options.run_label)])
        return


def parse_args():
    """"""
    parser = OptionParser(usage="\n\tpython alarm.py [options]",
                          prog="alarm",
                          description="Simple Alarm Clock",
                          add_help_option=True)
    parser.add_option('-l', '--list', dest='list_clock', action='store_true', default=False,
                      help='list all alarm clocks')
    parser.add_option('-a', '--all-run', dest='run_all_clock', action='store_true', default=False,
                      help='run all alarm clocks')
    parser.add_option('-t', '--tag-only', dest='run_label',
                      help='run alarm clocks by label')
    parser.add_option('-k', '--kill-clock', dest='kill_clocks', action='store_true', default=False,
                      help='kill all clocks')
    parser.add_option('--kill-music', dest='kill_ringtones', action='store_true', default=False,
                      help='kill ringing tones')
    parser.add_option('-r', '--reload', dest='reload_conf', action='store_true', default=False,
                      help='reload config from file: clock.json')
    parser.add_option('-d', '--daemon', dest='daemonize', action='store_true', default=False,
                      help='run as daemon')
    parser.add_option('--status', dest='status', action='store_true', default=False,
                      help='show status')
    (options, args) = parser.parse_args()
    return options


def load_conf():
    """"""
    with open(CONFIG_FILE) as f:
        clock_dict = json.load(f)
        return clock_dict


def list_clocks():
    """"""
    clocks = load_conf()
    print json.dumps(clocks, indent=4)


def loop_forever(interval, func, func_args=None, func_kwargs=None, callback=None):
    """
    Mainloop
    :param interval: loop interval, 1 day in this script
    :param func:
    :param func_args:
    :param func_kwargs:
    :param callback: callback function after loop function is executed
    :type callback: dict
        {func_name: , func_args: , func_kwargs: }
    :return:
    """
    func_args = func_args if func_args else []
    func_kwargs = func_kwargs if func_kwargs else {}
    error_count = 0
    # while True:
    if True:
        try:
            LOG.info('Start a new loop...')
            func(*func_args, **func_kwargs)
            time.sleep(interval)
            LOG.info('Finish one loop...')
            if callback:
                eval(callback['func_name'])(*callback.get('func_args', []), **callback.get('func_kwargs', {}))
        except Exception as e:
            LOG.error(e.message)
            # error_count += 1
            # if error_count <= 3:
            #    continue
            #else:
            #    LOG.error('Too many errors, we will exit the loop.')
            #    break


def run_clocks(label='all'):
    """
    start all clocks
    :param label: specified label, as a filter
    :return:
    """
    conf = load_conf()
    clocks = [Clock(clock, conf) for clock in conf['clocks']]
    clocks = [c for c in clocks if c.status == 'on']
    if label.lower() != 'all':
        clocks = [c for c in clocks if c.label.lower() == label.lower()]
    for c in clocks:
        c.start()


def stop_clocks():
    """
    actually kill the process
    :return:
    """
    LOG.info('Start killing process...')
    with open(PID_FILE) as f:
        os.kill(int(f.read()), signal.SIGKILL)
    LOG.info('Removing pid file...')
    os.remove(PID_FILE)
    LOG.info('Process is killed!')


def show_status():
    """
    see whether the clock is on
    :return:
    """
    if os.path.exists(PID_FILE):
        print 'Alarm is active.'
    else:
        print 'Alarm is inactive.'


def stop_music():
    """
    stop ringing music
    :return:
    """
    LOG.info('Kill playing music...')
    CMD = """ps aux|grep afplay|grep -v "grep"|awk '{print $2}'|xargs kill -9"""
    os.system(CMD)


def daemonize():
    """
    make it daemon process
    :return:
    """
    LOG.info('Start as daemon process...')
    pid = os.fork()
    if pid:
        sys.exit(0)

    os.chdir('/')
    os.umask(0)
    os.setsid()

    _pid = os.fork()
    if _pid:
        sys.exit(0)

    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null') as read_null, open('/dev/null', 'w') as write_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())


def save_pid(pid_file):
    if pid_file:
        LOG.info("pid saved to file: {}".format(pid_file))
        with open(pid_file, 'w+') as f:
            f.write(str(os.getpid()))
        atexit.register(os.remove, pid_file)


class Clock(object):
    """
    Each clock instance as a thread
    """

    def __init__(self, clock, defaults):
        self._ringtone_folder = clock.get('ringtone_folder', defaults['default_ringtone_folder'])
        self._ringtone = clock.get('ringtone', defaults['default_ringtone'])
        self._filter = clock.get('filter', defaults['default_filter'])
        self._status = clock.get('status', defaults['default_status'])
        self._label = clock.get('label', defaults['default_label'])
        self._time = clock.get('time', None)
        self._name = clock.get('name', None)

    def start(self):
        """start a new thread(Timer)"""
        countdown, next_day = self.get_count_down(self._time)
        music_path = os.path.join(self._ringtone_folder, self._ringtone)
        if self.filter_day(next_day=next_day):
            t = Timer(countdown, self.play_music, [music_path])  # new thread
            if self._name:
                t.setName(str(self._name))  # custom name
            else:
                t.setName(str(self._time))  # named by its clock time
            t.setDaemon(True)  # make sure it die with MainThread
            LOG.debug(
                'Clock(id:{})-Thread: name:{}, ident:{}, interval:{}, isAlive:{}, isDaemon:{}, '.format(
                    id(self), t.getName(), t.ident, t.interval, t.isAlive(), t.isDaemon()
                )
            )
            t.start()
            LOG.info('A new clock(id:{}) is started! Clock time:{}, ringtone: {}'.format(
                id(self), self._time, music_path
            ))
        else:
            LOG.info('Clock(id:{}) is ignored!'.format(id(self)))

    @property
    def label(self):
        return self._label

    @property
    def status(self):
        return self._status

    def filter_day(self, next_day=False):
        """filter day"""
        _, _, _, _, _, _, tm_wday, _, _ = time.localtime()
        if next_day:
            tm_wday += 1
            tm_wday %= tm_wday
        d = {
            'mon': [0],
            'tue': [1],
            'wed': [2],
            'thu': [3],
            'fri': [4],
            'sat': [5],
            'sun': [6],
            'weekday': range(5),
            'weekend': range(5, 7),
            'everyday': range(7),
        }
        for _ in self._filter:
            if tm_wday in d.get(_.lower(), []):
                return True
        return False

    def get_count_down(self, time_str):
        """
        count alarm time from now
        :param time_str:
        :type time_str: str
        :return:
        """
        _, _, _, tm_hour, tm_min, tm_sec, _, _, _ = time.localtime()
        now_timestamp = sum((tm_sec, tm_min * 60, tm_hour * 60 * 60))

        if re.match(r'\d+:\d+:\d+', time_str):
            h, m, s = time_str.split(':')
        elif re.match(r'\d+:\d+', time_str):
            h, m = time_str.split(':')
            s = 0
        else:
            raise TypeError("Wrong type for time:" + str(time_str))
        clock_timestamp = sum((int(s), int(m) * 60, int(h) * 60 * 60))

        if clock_timestamp >= now_timestamp:
            countdown = clock_timestamp - now_timestamp
            next_day = False
        else:
            # that means clock time is passed today, will count to next day
            countdown = 24 * 60 * 60 - (now_timestamp - clock_timestamp)
            next_day = True
        LOG.debug('Clock(id:{}) countdown seconds: {}'.format(id(self), countdown))
        return countdown, next_day

    def play_music(self, music_path):
        """
        actually play music, by "afplay"
        :param music_path:
        :return:
        """
        os.system("afplay {_musix_path} &".format(_musix_path=music_path))
        LOG.info('Clock(id:{}) is playing music: {}'.format(id(self), music_path))


if __name__ == '__main__':
    main()
