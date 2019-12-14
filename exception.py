#!/usr/bin/python3.7

class Error(Exception):
    def __init__(self,msg='what'):
        super().__init__(msg)

def error():
    raise Error('ya goofed it')

if __name__ == '__main__':
    try:
        error()
    except Error:
        print('lol')
