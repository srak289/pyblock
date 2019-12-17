#!/usr/bin/python3.7

from pymongo import MongoClient
from threading import Event
import re, datetime, tarfile, sys, time

class EventError(Exception):
    def __init__(self,msg):
        """Defines custom error to throw messages"""
        super().__init__(msg)

class MongoDriver:

    def __init__(self):
        """Initialize connection to local mongo database and set global variables for collections"""
        self.client = MongoClient("mongodb://localhost:27117/")
        self.db = self.client["ace"]
        self.user = self.db["user"]
        self.event = self.db["event"]
        self.squirrel = self.db["squirrel"]
        self.site = self.db["site"]
        
    def auto_block(self):
        """Read whitelist and IPS collection, cross reference IPS events with user collection, tag matching objects"""
        squirrels = self.whitelist()
        class1 = self.find_new_ips_event( 1 )
        class2 = self.find_new_ips_event( 2 )
        for x in class1 + class2:
            #add functionality for full bypass OR by-threat-id bypass
            try:
                package = self.process_event( x )
            except KeyError:
                print("[KeyError]:Will suppress event "+self.id_str(x)+" for future.")
                self.suppress_event(x)
                continue
            except EventError:
                print("[EventError]:Will suppress event "+self.id_str(x)+" for future.")
                self.suppress_event(x)
                continue
            if package['mac'] in squirrels:
                print("User "+package['mac']+" is a squirrel..and will not be blocked")
                continue
            if self.user.find_one( { 'mac': package[ 'mac' ], 'blocked': True } ):
                print( "User "+package[ 'mac' ]+" is already blocked" )
                continue
            self.update_user(package['mac'],package['keys'])
            
    def block(self,mac):
        """Tags all matching objects in user collection, then calls replicate()"""
        query = {
            "mac":mac
        }
        values = {
            "$set": {
                "autoblocked":True,
                "blocked":True
            }
        }
        # add custom property to user object
        self.user.update_many(query,values)
        self.replicate()

    def create_user(self,user):
        """Function that inserts user objects into the database"""
        newUser = {
            "mac": user['mac'],
            "msg": user['msg'],
            "note": user['note'],
            "site_id": user['site'],
            "noted": True,
            "blocked": True,
            "autoblocked": True
        }
        print("Inserting "+newUser)
        self.db.user.insert_one(newUser)

    def query(self,mac):
        """function that returns an array of user objects matching a mac address query against the user collection"""
        query = {
            "mac":mac
        }
        return self.to_array(self.user.find(query))

    def find_user(self,query):
        """finds one user object in the collection based on a custom query string"""
        return self.user.find_one(query)

    def find_internal_mac(self,ipsevent):
        """method that determines the direction of traffic flow in the ips event by regex-matching for private IP addresses"""
        try:
            if re.match("(10\.){2}\d{1,3}\.\d{1,3}",ipsevent['src_ip']):
                return ipsevent['src_mac']
            elif re.match("(10\.){2}\d{1,3}\.\d{1,3}",ipsevent['dest_ip']):
                return ipsevent['dst_mac']
            elif re.match("172\.16\.\d{1,3}\.\d{1,3}",ipsevent['src_ip']):
                return ipsevent['src_mac']
            elif re.match("172\.16\.\d{1,3}\.\d{1,3}",ipsevent['dest_ip']):
                return ipsevent['dst_mac']
            elif re.match("192\.168\.\d{1,3}\.\d{1,3}",ipsevent['src_ip']):
                return ipsevent['src_mac']
            elif re.match("192\.168\.\d{1,3}\.\d{1,3}",ipsevent['dest_ip']):
                return ipsevent['dst_mac']
            else:
                raise EventError("[ERROR]Internal mac cannot be determined..suppressing")
        except KeyError:
            raise EventError("[ERROR]IP keys not present for event..suppressing")

    def find_new_ips_event(self,severity):
        """method that returns array of unprocessed ips events of severity {severity}"""
        query = {
            "key":"EVT_IPS_IpsAlert",
            "inner_alert_severity":severity,
            "processed": {
                "$exists":False
            }
        }
        return self.to_array(self.event.find(query))
    
    def find_old_events(self,query = { "processed":True }):
        """Returns array of IPS events that have the processed tag. Can override {query} for more granularity"""
        return self.to_array(self.event.find(query))
    
    def find_sites(self):
        """Returns array of current sites"""
        # the code below excludes the site constructor class that is present in the sites collection of the database
        query = {
            "key": {
                "$exists": False
            }
        }
        return self.to_array(self.site.find(query))

    def find_site_ips(self):
        """Returns array of IPs of all UniFi routers"""
        query = {
            "type":"ugw"
        },{
            "ip":1
        }
        # 
        # cross ref to determine site names
        return self.to_array(self.db.device.find(query))

    def find_suppressed_events(self):
        """Returns array of suppressed events from database"""
        query = {
            "suppressed": True
        }
        return self.to_array(self.event.find(query))

    def find_blocked_users(self,query={ "blocked": True, "autoblocked": True }):
        """Returns array of blocked users that have been blocked by this program"""
        return self.to_array(self.user.find(query))

    def id_str(self,x):
        """Returns string of ObjectID('<hexidecimal trash>')"""
        return x['_id'].__str__()

    def process_event(self,e):
        """Returns small json object with information for auto_block"""
        int_mac = self.find_internal_mac(e)
        print("The internal mac is: "+int_mac)
        v = {
            "$set": {
                "processed":True                
            }
        }
        self.update_event(e,v)
        package = {
            "mac": int_mac,
            "keys": {
                "$set": {
                    "blocked": True,
                    "autoblocked": True,
                    "noted": True,
                    "note": e[ 'msg' ]
                }
            }
        }
        return package

    def translate_sites(self):
        """Return dictionary of site IDs as keys for the site names"""
        # this is most useful like so:
        # sites = self.translate_sites()
        # site = sites[ self.id_str(some_event[ '_id' ]) ] #this will return a site name like 'Concord'
        siteDicc = {}
        for x in self.find_sites():
            siteDicc[ self.id_str(x) ] = x[ 'desc' ]
        return siteDicc

    def replicate(self):
        """Commands replication of blocked users to all current sites"""
        sites = self.find_sites()
        siteDic = self.translate_sites()
        uniq_macs = []
        site_macs = []
        users = self.find_blocked_users( { "blocked": True } )
        print("Generating unique mac address list for all blocked users")
        for user in users:
            if not uniq_macs.__contains__( user[ 'mac' ] ):
                uniq_macs.append( user[ 'mac' ] )
        print( uniq_macs )
        for site in sites:
            print("Checking site "+site['desc'])
            for user in self.find_blocked_users( { "blocked": True, "site_id": self.id_str( site ) } ):
                if not site_macs.__contains__( user[ 'mac' ] ):
                    site_macs.append( user[ 'mac' ] )
            print("Generating unique mac address list for blocked users of site "+site['desc'])
            for mac in uniq_macs:
                print("Checking that site "+siteDic[self.id_str(site)]+" contains mac "+mac)
                if not site_macs.__contains__(mac):
                    userObj = self.find_user( { "blocked": True, "mac": mac, "site_id": self.id_str( site ) } )
                    if userObj is None:
                        print("[ERROR]: find_user returned NoneType for "+mac)
                        continue
                    else:
                        breakpoint()
                        self.create_user( userObj )
                        print("Adding mac "+mac+" to site "+siteDic[self.id_str(site)])
        
    def stats(self):
        """Prints useful database stats"""
        a = len(self.find_blocked_users())
        b = len(self.find_sites())
        c = len(self.find_old_events())
        d = len(self.find_new_ips_event(1))
        e = len(self.find_new_ips_event(2))
        f = len(self.find_suppressed_events())

        print('This program currently tracks '+str(a)+' blocked users, and '+str(c)+' IPS Events, across '+str(b)+' sites.')
        print('There are '+str(d)+' Class 1 events and '+str(e)+' Class 2 events in the IPS database to process.')

    def suppress_event(self,e):
        """Tags events that cannot be handled as suppressed"""
        print("Suppressing event "+self.id_str(e))
        v = {
            "$set": {
                "processed": True,
                "suppressed": True,
            }
        }
        self.update_event(e,v)

    def unblock_user(self,mac):
        """Remove tags from all user objects matching {mac} and add note for when user was unblocked"""
        date = datetime.datetime.now().date().isoformat()
        result = self.user.update_many(
            {
                "mac": mac
            },
            {
                "$set": {
                    "note": "Unblocked on "+date,
                },
                "$unset": {
                    "blocked": "",
                    "autoblocked": ""
                }
            }
        )
        return result

    def reset_ips_tags(self):
        #code to scrape all current 'autoblocked' tags
        pass

    def to_array(self,cursor):
        """Method for transforming the MongoClient cursor into an array of json objects to be easily handled"""
        a = []
        for x in cursor:
            a.append(x)
        return a
    
    def update_event(self,e,values):
        """Update one event that matches { e[ '_id'] } with {values}"""
        query = {
            "_id": e[ '_id' ]
        }
        print( "Updating event "+self.id_str(e))
        self.event.update(query,values)

    def update_user(self,mac='',values={}):
        """Update all user objects that match {mac} with {values} which defaults to {} but can be overridden"""
        query = {
            "mac": mac
        }
        print( "Updating user "+mac)
        self.user.update_many(query,values)

    def whitelist(self):
        """Reads the whitelist collection for all objects, then transforms them into an array of mac addresses"""
        a = []
        x = self.to_array( self.squirrel.find() )
        for m in x:
            a.append( m[ 'mac' ] )
        return a

# declaration of stopping the process
exit = Event()

def quit(signo, _frame):
    """Method that will accept a signal and set the exit flag"""
    print("Interrupted by %d, shutting down" % signo)
    exit.set()

def main():
    # instance driver class
    driver = MongoDriver()
    
    while not exit.is_set():
        # while no signal to terminate is recieved
        # get current time and generate time/date stamps
        now = datetime.datetime.now()
        datestamp = str(now.year)+'-'+str(now.month)+'-'+str(now.day)
        timestamp = str(now.hour)+':'+str(now.minute)+':'+str(now.second)
        # open logfile as sys.stdout in append mode
        with open('/var/log/pyblock/driver'+datestamp+'.log','a+') as sys.stdout:
            print('Log beginning at '+timestamp)

            #driver.clean_logs()

            driver.stats()
            driver.auto_block()
            driver.replicate()
        # sleep for two hours
        exit.wait(7200)
    # on exit log to file
    print("End of the program. I was killed gracefully :)")

if __name__ == '__main__':

    import signal
    # current time/date stamps
    now = datetime.datetime.now()
    datestamp = str(now.year)+'-'+str(now.month)+'-'+str(now.day)
    timestamp = str(now.hour)+':'+str(now.minute)+':'+str(now.second)
    # log startup time to logfile in append mode
    with open('/var/log/pyblock/driver'+datestamp+'.log','a+') as sys.stdout:
        print('[INFO] Starting pyblock.service at '+timestamp)

    # process signal
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit);
    # call main
    main()

    now = datetime.datetime.now()
    datestamp = str(now.year)+'-'+str(now.month)+'-'+str(now.day)
    timestamp = str(now.hour)+':'+str(now.minute)+':'+str(now.second)

    with open('/var/log/pyblock/driver'+datestamp+'.log','a+') as sys.stdout:
        print('[INFO] Starting pyblock.service at '+timestamp)
