#!/usr/bin/python3.7

class Lol:
    
    def __init__(self):
        pass
    def a(self):
        print('this is a')

    def b(self):
        print('this is b')

    def c(self):
        print('this is c')
    def returndicc(self):
        self.dicc = {
            'a': self.a(),
            'b': self.b(),
            'c': self.c()
        }
        return self.dicc

    def main(self):
        print("printing main")
        self.dicc = self.returndicc()
        self.dicc['a']
        self.dicc['b']
        self.dicc['c']

if __name__ == '__main__':
    print('name is main')
    lol = Lol()
    lol.main()
    
