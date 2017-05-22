#!/usr/bin/env python
# coding=utf-8
"""
上传文件到七牛空间
"""
import sys
import os

from qiniu import Auth, put_file, etag

from config import ACCESS_KEY, SECRET_KEY, DEFAULT_BUCKET, BUCKET_DOMAIN


def main():
    """"""
    if len(sys.argv) == 3:
        file_path, key = sys.argv[1:]
        bucket = DEFAULT_BUCKET
    elif len(sys.argv) == 4:
        file_path, key, bucket = sys.argv[1:]
    else:
        print >> sys.stderr, "python qn_upfile.py <file_path> <key> [bucket_name]"
        sys.exit()
    upload(file_path, key, bucket)


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
