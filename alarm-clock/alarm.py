#!/usr/bin/env python
"""

"""
import os
import json
from optparse import OptionParser
from threading import Timer
import re
import time


def main():
    """"""
    options = parse_args()
    if options.daemonize:
        daemonize()
    if options.kill_all_ringtones:
        stop_clocks()
    if options.list_clock:
        list_clocks()
    if options.run_all_clock:
        loop_forever(24 * 60 * 60, run_clocks, label='all')
    if options.run_label is not None:
        loop_forever(24 * 60 * 60, run_clocks, label=str(options.run_label))


def parse_args():
    """"""
    parser = OptionParser(usage="\n\tpython alarm.py [-r] [-l]",
                          prog="alarm",
                          description="Simple Alarm Clock",
                          add_help_option=True)
    parser.add_option('-l', '--list', dest='list_clock', action='store_true', default=False,
                      help='list all alarm clocks')
    parser.add_option('-a', '--all', dest='run_all_clock', action='store_true', default=False,
                      help='run all alarm clocks')
    parser.add_option('-t', '--tag', dest='run_label', help='run alarm clocks by label')
    parser.add_option('-k', '--kill', dest='kill_all_ringtones', action='store_true', default=False,
                      help='kill all ringing tones')
    parser.add_option('-d', '--daemon', dest='daemonize', action='store_true', default=False,
                      help='run as daemon')
    (options, args) = parser.parse_args()
    return options


def load_conf():
    """"""
    with open('/Users/eacon/github/python-tools/alarm-clock/clock.json') as f:
        clock_dict = json.load(f)
        return clock_dict


def list_clocks():
    """"""
    clocks = load_conf()
    print json.dumps(clocks, indent=4)


def loop_forever(interval, func, *args, **kwargs):
    """
    :param interval:
    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    while True:
        try:
            func(*args, **kwargs)
            time.sleep(interval)
        except KeyboardInterrupt:
            break


def run_clocks(label='all'):
    """"""
    conf = load_conf()
    clocks = [Clock(clock, conf) for clock in conf['clocks']]
    clocks = [c for c in clocks if c.status == 'on' and c.istoday]
    if label.lower() == 'all':
        pass
    else:
        clocks = [c for c in clocks if c.label.lower() == label.lower()]
    for c in clocks:
        c.start()


class Clock(object):
    def __init__(self, clock, defaults):
        self._ringtone_folder = clock.get('ringtone_folder', defaults['default_ringtone_folder'])
        self._ringtone = clock.get('ringtone', defaults['default_ringtone'])
        self._filter = clock.get('filter', defaults['default_filter'])
        self._status = clock.get('status', defaults['default_status'])
        self._label = clock.get('label', defaults['default_label'])
        self._time = clock.get('time', -1)

    def start(self):
        countdown = self.get_count_down(self._time)
        music_path = os.path.join(self._ringtone_folder, self._ringtone)
        if countdown >= 0:
            Timer(countdown, self.play_music, [music_path]).start()

    @property
    def label(self):
        return self._label

    @property
    def status(self):
        return self._status

    @property
    def istoday(self):
        _, _, _, _, _, _, tm_wday, _, _ = time.localtime()
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
        res = []
        for _ in self._filter:
            if tm_wday in d.get(_.lower()):
                return True

    @staticmethod
    def get_count_down(time_str):
        """
        :param time_str:
        :type time_str: str
        :return:
        """
        # 06:00 -> 6*60*60
        if re.match(r'\d+:\d+:\d+', time_str):
            h, m, s = time_str.split(':')
        elif re.match(r'\d+:\d+', time_str):
            h, m = time_str.split(':')
            s = 0
        else:
            raise TypeError("Wrong type for time:" + str(time_str))
        clock_timestamp = sum((int(s), int(m) * 60, int(h) * 60 * 60))

        _, _, _, tm_hour, tm_min, tm_sec, _, _, _ = time.localtime()
        now_timestamp = sum((tm_sec, tm_min * 60, tm_hour * 60 * 60))

        countdown = clock_timestamp - now_timestamp
        if countdown < 0:
            countdown = 24 * 60 * 60 - countdown
        return countdown

    @staticmethod
    def play_music(music_path):
        """"""
        print '\nplaying music: ' + str(music_path)
        os.system("afplay {_musix_path} &".format(_musix_path=music_path))


def stop_clocks():
    """"""
    CMD = """ps aux|grep afplay|grep -v "grep"|awk '{print $2}'|xargs kill -9"""
    os.system(CMD)


def daemonize():
    """"""
    if os.fork():
        os._exit(0)
    os.chdir("/")
    os.umask(022)
    os.setsid()
    os.umask(0)
    if os.fork():
        os._exit(0)
    stdin = open(os.devnull)
    stdout = open(os.devnull, 'w')
    os.dup2(stdin.fileno(), 0)
    os.dup2(stdout.fileno(), 1)
    os.dup2(stdout.fileno(), 2)
    stdin.close()
    stdout.close()
    os.umask(022)


if __name__ == '__main__':
    # Timer(1, list_clock).start()
    # print time.gmtime(), time.ctime()
    # _, _, _, tm_hour, tm_min, tm_sec, tm_wday, _, _ = time.gmtime()
    # print tm_hour, tm_min, type(tm_sec), tm_wday
    # print get_count_down('14:19')
    def foo(x):
        print x


    #
    # Timer(1, foo, 'y').start()
    # run_clocks()
    # os.system('echo "test1" >> /Users/eacon/github/python-tools/alarm-clock/test &')
    # daemonize()
    # os.system('afplay /Users/eacon/Documents/music/gao_bai_qi_qiu.mp3')
    # loop_forever(1, foo, x=10)

    main()
