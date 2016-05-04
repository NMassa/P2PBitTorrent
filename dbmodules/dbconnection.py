# coding=utf-8
import datetime
import re
import sys
from pymongo import MongoClient
from helpers.helpers import *


class MongoConnection():
    def __init__(self, out_lck, host="localhost", port=27017, db_name='torrent', conn_type="local", username='', password=''):
        self.out_lck = out_lck
        self.host = host
        self.port = port
        try:
            self.conn = MongoClient()
            self.db = self.conn[db_name]
            if "sessions" not in self.db.collection_names():
                self.db.create_collection("sessions")
            if "files" not in self.db.collection_names():
                self.db.create_collection("files")

        except Exception as e:
            # TODO: cambiare print
            output(out_lck, "Could not connect to server: " + e.message)

    def get_sessions(self):
        """
            Restituisce tutte le sessioni aperte
        """
        cursor = self.db.sessions.find()
        return list(cursor)

    def get_session(self, session_id):
        session = self.db.sessions.find_one({"session_id": session_id})
        return session

    def insert_session(self, ipv4, ipv6, port):
        """
            Inserisce una nuova sessione, o restitusce il session_id in caso esista già
        """
        cursor = self.db.sessions.find_one({"ipv4": ipv4,
                                            "ipv6": ipv6,
                                            "port": port
                                            })
        if cursor is not None:
            # TODO: modificare print
            output(self.out_lck, "already logged in")
            # Restituisco il session id esistente come da specifiche
            return cursor['session_id']
        else:
            try:
                session_id = id_generator(16)
                self.db.sessions.insert_one({"session_id": session_id,
                                             "ipv4": ipv4,
                                             "ipv6": ipv6,
                                             "port": port
                                             })
                return session_id
            except Exception as e:
                output(self.out_lck, "insert_session: " + e.message)
                return "0000000000000000"

    # def remove_session(self, sessionID):

    # TODO: FCHU
    def get_parts(self, md5):
        cursor = self.db.hitpeers.find({"md5": md5}, {"_id": 0, "md5": 0, "session_id": 0})
        return list(cursor)
        # db.getCollection('hitpeers').find({md5: "md52"}, { _id : 0, md5 : 0, sessionid : 0 })

    def update_parts(self, md5, sessionID, str_part):
        part = self.db.files.find_one({"md5": md5, "peers.session_id": sessionID})
        if part is not None:
            try:
                self.db.files.update({'md5': md5, 'peers.session_id': sessionID}, {"$set": {'part_list': str_part}})
                # db.files.update({'md5': "3md5", 'peers.session_id': "id1"}, {"$set": {'part_list': "dddd"}}) funziona
                # db.getCollection('files').update({"md5": "1md5"}, {"$set": {"peers.part_list": "bbb"}})

            except:
                output(self.out_lck, "error insert file")
        else:
            print "file or user not found"
        session = self.db.sessions.find_one({"session_id": sessionID})
        list(session)
        ipv4 = session['ipv4']
        ipv6 = session['ipv6']
        port = session['port']
        check = self.db.hitpeers.find_one({"md5": md5, "session_id": sessionID})
        if check is not None:
            self.db.hitpeers.remove({"md5": md5, "session_id": sessionID})
        self.db.hitpeers.insert_one({"md5": md5, "session_id": sessionID, "ipv4": ipv4, "ipv6": ipv6, "port": port, "part_list": str_part})

    # TODO: da vedere
    def get_peers(self, md5, sessionID):
        peers = self.db.sessions.find_one({"md5": md5})
        if peers is not None:
            output(self.out_lck, "nessun file trovato")



