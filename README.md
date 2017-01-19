# python tools
---

日常使用的自制工具

- ssh/pyssh.py
    - json文件记录ssh连接、管理用户密码
    - 支持主机跳转
- code/code_counter.py
    + 代码行数统计
- alarm-clock
    + 自制命令行闹钟
    + 专治懒人，必须起床敲命令行关闭闹钟
    + 无限自定义闹铃
    + 支持标签功能
    + 支持定义只在工作日、周末、或者具体周一／周二闹铃
        
        
### pyssh
展示主机列表：

    $ python pyssh.py -l
              Host          |          User          |         Alias
    --------------------------------------------------------------------------
          10.17.35.80       |         tangyk         |           80
         132.122.70.138     |          noce          |          138
         132.122.69.126     |          root          |          126

    
连接主机：
    
    $ python pyssh.py 80
    ######## Login Success! ########
    
    [tangyk@host-9-80 ~]$
    

通过自定义的json文件保存主机列表，如下示例：
    
    $ cat sample.json
    {
      "192.168.0.2": {
        "username": "tangyk",
        "password": "tangyk",
        "alias": "host-01"
        "proxy": "192.168.0.3"
      }
    }
     
      
### 代码统计
用法

    $ python code_counter.py
    Usage:
        python code_counter.py [OPTIONS] PROJECT_ROOT_DIR
    
    Options
    -p        Python files only, deafult value
    -j        Java files only
    -g        Golang files only
    -c        C/C++ files only
    
    $ python code_counter.py -p ssh/
    876
    $ pycode -p alarm-clock/
    160
    
    
    
### 命令行闹钟
用法

    $ python alarm.py -h
    Usage:
        python alarm.py [-r] [-l]
    
    Simple Alarm Clock
    
    Options:
      -h, --help            show this help message and exit
      -l, --list            list all alarm clocks
      -a, --all             run all alarm clocks
      -t RUN_LABEL, --tag=RUN_LABEL
                            run alarm clocks by label
      -k, --kill            kill all ringing tones
      -d, --daemon          run as daemon
     
         
    # 查看闹钟配置         
    $ python alarm.py -l
    {
        "clocks": [
            {
                "filter": [
                    "weekday"
                ],
                "time": "06:00:00"
            },
            {
                "filter": [
                    "weekend"
                ],
                "time": "09:00",
                "status": "off",
                "label": "kidding"
            }
        ],
        "default_ringtone": "gao_bai_qi_qiu.mp3",
        "default_filter": [
            "everyday"
        ],
        "default_status": "on",
        "default_label": "default",
        "default_ringtone_folder": "/Users/eacon/Documents/music"
    }   
          
    # 开启闹钟(加&符后台运行)
    $ python alarm.py -a &
    [1] 80950
    $ 
    $ 
    playing music: /Users/eacon/Documents/music/gao_bai_qi_qiu.mp3
    
    [1]  + 80950 done       python alarm.py -a
    
    # 关掉闹铃
    $ python alarm.py --kill
    

### 建议用法
赋予脚本执行权限：

    $ chmod +x alarm.py
    
添加软连接，方便全局使用：
    
    $ ln -s <path-to-alarm.py> </usr/local/bin/pyalarm>
    $ pyalarm -h
    Usage:
        python alarm.py [-r] [-l]
    
    Simple Alarm Clock
    
    Options:
      -h, --help            show this help message and exit
      -l, --list            list all alarm clocks
      -a, --all             run all alarm clocks
      -t RUN_LABEL, --tag=RUN_LABEL
                            run alarm clocks by label
      -k, --kill            kill all ringing tones
      -d, --daemon          run as daemon