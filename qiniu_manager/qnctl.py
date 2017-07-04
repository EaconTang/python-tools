#!/usr/bin/env python
# coding=utf-8
"""
自制七牛管理工具
"""
import sys
import os
import json
from optparse import OptionParser

from qiniu import Auth, put_file, etag

from config import ACCESS_KEY, SECRET_KEY, DEFAULT_BUCKET, BUCKET_DOMAIN


def parse_args():
    """参数解析"""
    parser = OptionParser(description='Qiniu manger')
    parser.add_option('--list-bucket', dest='list_bucket', default=False,
                      help='list bucket')
    parser.add_option('--web', dest='web', default=False, action='store_true',
                      help='web browser for file manger')
    options, args = parser.parse_args()
    return options, args


def main():
    """"""
    options, args = parse_args()
    print 'Options: {}\n\n'.format(options)
    if options.web:
        web()
        sys.exit()
    if options.list_bucket:
        list_bucket(options.list_bucket)


def web():
    """"""
    from bottle import run, Bottle, static_file

    app = Bottle()

    @app.route('/')
    def home():
        """"""
        return 'Saluton!'

    @app.route('/<filepath>')
    def view(filepath):
        """"""
        base_dir = os.path.dirname(os.path.realpath(__file__))
        # file_path = os.path.join(base_dir, filepath)
        # return open(file_path).read()
        return static_file(filename=filepath, root=base_dir)

    run(app=app, host='localhost', port=8083, debug=True)


def auth():
    """"""


def list_bucket(bucket):
    """"""
    from qiniu import BucketManager

    m = BucketManager(auth=Auth(ACCESS_KEY, SECRET_KEY))
    ret, eof, info = m.list(bucket=bucket)
    # print 'Return: \n\t{}\n'.format(ret)
    # print 'Info: \n\t{}\n'.format(info)
    if info.status_code == 200:
        text = json.loads(info.text_body)
        for item in text['items']:
            print '\t{}/{}'.format(BUCKET_DOMAIN[bucket], item['key'])


def upload(file_path, key, bucket, token_ttl=3600):
    """"""
    file_path = os.path.abspath(file_path)
    print '\n'.join(['Upload detail:',
                     '\tbucket-name: {}'.format(bucket),
                     '\tkey-name: {}'.format(key),
                     '\tlocal-file: {}'.format(file_path),
                     ])

    ret, info = put_file(
        up_token=Auth(ACCESS_KEY, SECRET_KEY).upload_token(bucket, key, token_ttl),
        key=key,
        file_path=file_path
    )
    assert ret['key'] == key
    assert ret['hash'] == etag(file_path)

    print 'Result: \n\t{}\n\t{}'.format(ret, info)
    print 'Url: \n\t{}/{}'.format(BUCKET_DOMAIN.get(bucket), key)


if __name__ == '__main__':
    main()
