# coding=utf-8
import datetime
import re
import sys

# sys.path.insert(1, '/home/massa/Documenti/PycharmProjects/P2PKazaa')
from pymongo import MongoClient
from helpers.helpers import *


class MongoConnection():
    def __init__(self, out_lck, host="localhost", port=27017, db_name='kazaa', conn_type="local", username='',
                 password=''):
        self.out_lck = out_lck
        self.host = host
        self.port = port
        try:
            self.conn = MongoClient()
            self.db = self.conn[db_name]

        except Exception as e:
            output(out_lck, "Could not connect to server: " + e.message)
