#!/usr/bin/python3.7

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

import sys
sys.path.append("/var/lib/pyblock")

from MongoDriver import MongoDriver
import subprocess
from os import system
import re
import time
import datetime
                
def main():

    system('clear')
    driver = MongoDriver()
    state = 0
    ttl = 5



    while 1:

        print("        ____        ____  __           __")
        print("       / __ \__  __/ __ )/ /___  _____/ /__")
        print("      / /_/ / / / / __  / / __ \/ ___/ //_/")
        print("     / ____/ /_/ / /_/ / / /_/ / /__/ ,<")
        print("    /_/    \__, /_____/_/\____/\___/_/|_|")
        print("          /____/")

        if state is 0:

            print("\nWelcome to the Unblock feature of MongoDriver v1.0\n\nPress Ctrl+C at any time to exit...\n")
            time.sleep(5)
            system('clear')
            state = 1

        elif state is 1:

            try:
                mac = input("\nEnter the MAC address of the user you would like to unblock:   ")
                print("\nRead "+mac+" as input\n")
                if not re.match(r'([0-9a-f]{2}:){5}[0-9a-f]{2}',mac):
                    raise ValueError
                else:
                    state = 2
            except ValueError:
                print("\n[ERROR]: MAC Address must be in the format xx:xx:xx:xx:xx:xx and may only use the characters 0-9 a-f\nTry again...\n")
            time.sleep(5)
            system('clear')

        elif state is 2:

            try:
                query = {
                    "mac": mac,
                    "blocked": True,
                    "autoblocked": True
                }
                result = driver.find_blocked_users(query)
                if len(result) is 0:
                    raise ValueError
                else:
                    state = 3
            except ValueError:
                print("\n[ERROR]: MAC Address was not present in database..for further assistance dial x1262\n")
                state = 0
            time.sleep(5)
            system('clear')

        elif state is 3:
            try:
                try:
                    answer = input("User "+mac+" was blocked for\n"+result[0]['msg']+"\nAre you sure you want to continue? [y/n]")
                except KeyError:
                    answer = input("User "+mac+" has no reason for being blocked...\nAre you sure you want to continue? [y/n]")

                print("Read "+answer+" as input\n")
                if not re.match(r'[yn]',answer):
                    raise ValueError
                else:
                    if answer is 'y':
                        print("Proceeding with unblock of user "+mac+"\n")
                        result = driver.unblock_user(mac)
                        print(str(result.modified_count)+" instances of user "+mac+" were unblocked.\n")
                        state = 10
                    else:
                        print("Aborting unblock of user "+mac+"\n")
                        state = 10
                    time.sleep(5)
                    system('clear')
                    
            except ValueError:
                print("You must answer 'y' or 'n'...\n")
                time.sleep(5)
                system('clear')


        else:
            
            print("\nYour session will be terminated in "+str(ttl)+" seconds")
            time.sleep(1)
            system('clear')
            ttl -=1 
            if ttl is 0:
                break

if __name__ == '__main__':

    now = datetime.datetime.now().isoformat()
    tstamp = re.sub(r'[-T:\.]','',now[:now.index('.')])

    logfile = open('/var/log/pyblock/pyblock'+tstamp+'.log','w+')
    sys.stdout = stream_tee(sys.stdout, logfile)

    main()

