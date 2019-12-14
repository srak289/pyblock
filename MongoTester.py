#!/usr/bin/python3.7
from MongoDriver import MongoDriver

driver = MongoDriver()

driver.stats()

driver.auto_block()

driver.replicate()

driver.stats()
