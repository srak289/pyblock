#!/usr/bin/python3.7

import sys, re, time, datetime

sys.path.append("/var/lib/pyblock")

from MongoDriver import MongoDriver
from os import system

class MenuException(Exception):
    def __init__(self,msg):
        super().__init__(msg)

class FilterException(Exception):
    def __init__(self,msg):
        super().__init__(msg)

class stream_tee(object):
    # Based on https://gist.github.com/327585 by Anand Kunal
    def __init__(self, stream1, stream2):
        self.stream1 = stream1
        self.stream2 = stream2
        self.__missing_method_name = None # Hack!

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)

    def __getattr__(self, name):
        self.__missing_method_name = name # Could also be a property
        return getattr(self, '__methodmissing__')

    def __methodmissing__(self, *args, **kwargs):
        # Emit method call to the log copy
        callable2 = getattr(self.stream2, self.__missing_method_name)
        callable2(*args, **kwargs)

        # Emit method call to stdout (stream 1)
        callable1 = getattr(self.stream1, self.__missing_method_name)
        return callable1(*args, **kwargs)

class PyBlock:

    def __init__(self):

        self.driver = MongoDriver()

        self.advanced = False
        self.state = -1
        self.choice = 0
        self.ttl = 5

    def adv_menu(self):
        print("1. Auto Block")
        print("2. Manual Block")
        print("3. Database Report")
        print("4. Replicate Database")
        print("5. Blocked User Report")
        print("0. Exit PyBlock")
        res = self.input_filter("Enter a menu option: ",'[0-9]')
        if res not in self.adv_menu_dict.keys():
            raise MenuException(f'{res} not in {self.menu_dict.keys()}')
        self.state = res
        
    def auto_block(self):
        self.driver.auto_block()
        self.state = "30"
        time.sleep(5)

    def banner(self):
        print("        ____        ____  __           __")
        print("       / __ \__  __/ __ )/ /___  _____/ /__")
        print("      / /_/ / / / / __  / / __ \/ ___/ //_/")
        print("     / ____/ /_/ / /_/ / / /_/ / /__/ ,<")
        print("    /_/    \__, /_____/_/\____/\___/_/|_|")
        print("          /____/")
        print("-----------------------------------------------")

    def block(self):
        mac = self.input_filter("Enter the mac address you would like to block",'([0-9a-f]{2}:){5}[0-9a-f]{2}')
        self.driver.block(mac)
        self.state = "30"
        time.sleep(5)

    def blocked_user_report(self):
        self.driver.find_blocked_users()
        self.state = "30"
        time.sleep(5)

    def disconnect(self):
        while self.ttl > 0:
            system('clear')
            self.banner()
            print(f'Your session will be disconnected in {self.ttl} seconds...')
            self.ttl -= 1
            time.sleep(1)
        exit()
    
    def stats(self):
        self.driver.stats()
        self.state = "30"
        time.sleep(5)

    def input_filter(self,msg,filt):
        res = str(input(msg))
        if re.match(filt,res):
            return res
        else:
            raise FilterException(f'{res} does not match filter {filt}')
        
    def menu(self):
        print("1. Query Database")
        print("2. Unblock User")
        print("9. Advanced Menu")
        print("0. Exit PyBlock")
        res = self.input_filter("Enter a menu option: ",'[0-9]')
        if res not in self.menu_dict.keys():
            raise MenuException(f'{res} not in {self.menu_dict.keys()}')
        self.state = res

    def menu_upgrade(self):
        phrase = "Admin Me"
        res = self.input_filter(f'Type the following exactly as it appears: {phrase} \n\n','[A-Za-z]')
        if res == phrase:
            self.advanced = True
        else:
            print("\nSorry..that's not correct\n")
        self.state = "30"
        time.sleep(5)

    def output(self,res):
        if len(res) == 0:
            print("Sorry, your search returned no results...\n\nPress Enter to return to menu.")
        elif len(res) > 0:
            while len(res) > 0:
                print('\n'+str(res.pop())+'\n')
                input("Press Enter to list more items..." if len(res) > 0 else "Press Enter to return to menu.")

    def query(self):
        res = self.input_filter("Enter the mac address you would like to query: ",'([0-9a-f]{2}:){5}[0-9a-f]{2}')
        self.output(self.driver.find_blocked_users({ "mac": res }))
        self.state = "30"
        time.sleep(5)

    def replicate(self):
        orig = sys.stdout
        sys.stdout = system('more')
        self.driver.replicate()
        self.state = "30"
        sys.stdout = orig
        time.sleep(5)

    def unblock(self):
        mac = self.input_filter("Enter the mac address you would like to unblock: ",'([0-9a-f]{2}:){5}[0-9a-f]{2}')
        self.driver.unblock_user(mac)
        self.state = "30"
        time.sleep(5)
        
    def welcome(self):
        print("\nWelcome to Unblock v2: The user frontend for MongoDriver\n\nPress Ctrl+C at any time to exit...\n")
        self.state = "30"
        time.sleep(5)
        
    def adv_dicc(self):
        dicc = {
            "0": self.disconnect,
            "1": self.auto_block,
            "2": self.block,
            "3": self.stats,
            "4": self.replicate,
            "5": self.blocked_user_report,
            "30": self.adv_menu
        }
        return dicc

    def dicc(self):
        dicc = {
             "0": self.disconnect,
             "1": self.query,
             "2": self.unblock,
             "9": self.menu_upgrade,
             "30": self.menu
        }
        return dicc
    
    def main(self):
        self.adv_menu_dict = self.adv_dicc()
        self.menu_dict = self.dicc()
        system('clear')

        while 1:
            self.banner()
            if self.state is -1:
                self.welcome()
            else:
                try:
                    if self.advanced:
                        self.adv_menu_dict[self.state]()
                    else:
                        self.menu_dict[self.state]()
                except MenuException:
                    print("\nPlease enter a valid menu option...\n")
                except FilterException:
                    print("\nPlease format your input correctly...\n")
            system('clear')
            
if __name__ == '__main__':

    now = datetime.datetime.now().isoformat()
    tstamp = re.sub(r'[-T:\.]','',now[:now.index('.')])

    logfile = open('/var/log/pyblock/pyblock'+tstamp+'.log','w+')
    sys.stdout = stream_tee(sys.stdout, logfile)
    pyblock = PyBlock()
    pyblock.main()
