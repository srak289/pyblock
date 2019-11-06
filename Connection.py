#!/usr/bin/python3

from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27117')

db = client.ace

users = db.users

blocked_data = users.find(
    {
    'blocked':'true'
    }
)
for user in blocked_data:
    print(user)
    
