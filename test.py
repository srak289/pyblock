#!/usr/bin/python3
from MongoDriverTesting import MongoDriver
import datetime
import tarfile
import sys

today = datetime.datetime.now().isoformat()

driver = MongoDriver()

with open('auto'+today,'w') as sys.stdout:

    print( "\nCall to whitelist()\n" )
    print( driver.to_array( driver.whitelist() ) )
    print( "\nCall to find_new_ips_event(1)\n" )
    print( driver.to_array( driver.find_new_ips_event( 1 ) ) )

#driver.replicate()
