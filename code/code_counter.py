#!/usr/bin/env python
"""
python code_counter.py [OPTIONS] PROJECT_ROOT_DIR

Options:
-p        Python files only, deafult value
-j        Java files only
-g        Golang files only
-c        C/C++ files only
"""
import sys
import os
import platform


def main():
    """"""
    # sys.argv = ['file', '-p', '.']
    option, project_path = parse_args(*sys.argv[1:])
    file_type = {
        '-p': 'py',
        '-j': 'java',
        '-g': 'go',
        '-c': '{c, cpp}'
    }.get(option)
    if platform.system() in ('Linux', 'Darwin'):
        shell_cmd(project_path, file_type)
    else:
        pass


def parse_args(*args):
    """"""
    options = ('-p', '-j', '-g', '-c')
    default_option = '-p'
    args_len = len(args)
    if args_len == 1:
        project_path = args[0]
        option = default_option
    elif args_len == 2:
        option, project_path = args
        if option not in options:
            sys.stderr.write('Unknow option: "{}"\n'.format(option))
            print(usage())
            sys.exit(-1)
    else:
        print(usage())
        sys.exit(-1)
    return option, project_path


def shell_cmd(_project_path, _suffix):
    """"""
    CMD = """find {path} -name "*.{suffix}" |xargs grep -v "^$"|wc -l"""
    _cmd = CMD.format(path=_project_path, suffix=_suffix)
    os.system(_cmd)


def walk_dir(project_path):
    """"""
    pass


def usage():
    """"""      
    return '\n'.join([
        'Usage: ',
        '\tpython code_counter.py [OPTIONS] PROJECT_ROOT_DIR',
        '\nOptions',
        '-p        Python files only, deafult value',
        '-j        Java files only',
        '-g        Golang files only',
        '-c        C/C++ files only'
    ])


if __name__ == '__main__':
    main()