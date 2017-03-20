# coding=utf-8
"""
MacOS的系统通知脚本：告诉自己，工作时间每隔一小时记得喝点水、起来走走、并且上个洗手间～

设为crontab（以996工作强度为例[捂脸]）：
    0 9-21/1 * * 1-6 python ~/github/python-tools/sys_notify/rest.py
"""
import applescript


def main():
    notify_msg = "Drink water, see around and pee."
    script = applescript.AppleScript(source='display notification "{}"'.format(notify_msg))
    script.run()


if __name__ == '__main__':
    main()
