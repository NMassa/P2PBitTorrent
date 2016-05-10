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

    # TODO: da finire
    def remove_session(self, sessionID):
        return True

    def get_parts(self, md5):
        """
            Restituisce una lista di peer con ip+porta e la stringa delle parti possedute
        """
        # cursor = self.db.hitpeers.find({"md5": md5}, {"_id": 0, "md5": 0, "session_id": 0}) vecchia versione db
        # db.getCollection('hitpeers').find({md5: "md52"}, { _id : 0, md5 : 0, session_id : 0 })
        cursor = self.db.files.find({"md5": md5}, {"_id": 0, "md5": 0, "peers.session_id": 0, "name": 0, "len_part": 0,
                                                   "len_file": 0})

        # TODO: vedere lista
        peers = list(cursor)
        prova = peers[0]
        return prova['peers']

    def update_parts(self, md5, sessionID, str_part):
        # TODO: funziona ma migliorabile
        """
            modifica la stringa delle parti possedute del file di un peer
        """
        part = self.db.files.find_one({"md5": md5, "peers.session_id": sessionID})
        if part is not None:
            try:
                #self.db.files.update({'md5': md5, 'peers.session_id': sessionID}, {"$set": {'part_list': str_part}})
                # db.files.update({'md5': "3md5", 'peers.session_id': "id1"}, {"$set": {'part_list': "dddd"}}) funziona
                # db.getCollection('files').update({"md5": "1md5"}, {"$set": {"peers.part_list": "bbb"}})

                peer = self.db.files.find_one({'md5': "3md5", 'peers.session_id': "id1"},
                                              {'peers': {"$elemMatch": {'session_id': "id1"}}})
                #db.getCollection('files').findOne({'md5' : "3md5", 'peers.session_id' : "id1"}, {"peers": {"$elemMatch": {"session_id": "id1"}}})
                str_part_old = peer['session_id']

                self.db.files.update({"md5": md5, 'peers': {'$elemMatch': {'session_id':sessionID}}}, {"$set": {'peers.$.part_list': "str_part"}})
                # db.getCollection('files').update({"md5": "1md5", 'peers': {'$elemMatch' : {'session_id':"id1"}}},{"$set":{'peers.$.part_list': "aaaaaaaaaa"}})
                print "update part_list non esistente"
            except Exception as e:
                print "error update file: " + e.message
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

    def insert_peer(self, name, md5, LenFile, LenPart, sessionID):
        file = self.db.files.find_one({"md5": md5})
        if file is not None:
            # update
            try:
                #str_part ="\xff\xff\xff\xff"
                str_part = chr(int("11111111", 2))
                self.db.files.update({"md5": md5},
                                     {"$push": {"peers": [{"session_id": sessionID, "part_list": str_part}]}})
                # self.db.files.update({"md5": md5}, {"$addToSet": {"peers": {"session_id": sessionID, "part_list": str_part}}})
            except:
                output(self.out_lck, "error insert file")
            output(self.out_lck, "add peer")
        else:
            # insert
            try:
                n_parts = int(LenFile) / int(LenPart)
                str_part = ""
                i = 0
                for i in range(1, n_parts):
                    str_part = str_part + "1"

                peer = self.db.sessions.find_one({"session_id": sessionID})

                # TODO: sistemare database peer
                self.db.files.insert_one({"name": name, "md5": md5, "len_file": LenFile, "len_part": LenPart,
                                          'peers': [{'session_id': sessionID, 'ipv4': peer['ipv4'], 'ipv6': peer['ipv6'],
                                                     'port': peer['port'],'part_list': str_part}]})
            except:
                print "error insert file"

        '''
        peer = self.db.hitpeers.find_one({'md5': md5, 'session_id': sessionID})
        if peer is None:
            session = self.db.sessions.find_one({"session_id": sessionID})
            ipv4 = session['ipv4']
            ipv6 = session['ipv6']
            port = session['port']
            # TODO: sistemare st_part
            str_part = ""
            self.db.hitpeers.insert_one({"md5": md5, "session_id": sessionID, "ipv4": ipv4, "ipv6": ipv6, "port": port, "part_list": str_part})

        '''

    def get_files(self, query_str):
        """
            Restituisce i file il cui nome comprende la stringa query_str
        """
        regexp = re.compile(query_str.strip(" "), re.IGNORECASE)
        if regexp == "*":
            files = self.db.files.find()
        else:
            files = self.db.files.find({"name": {"$regex": regexp}})
        return files

    def get_download(self, md5):
        download = self.db.download.find_one({"md5": md5})
        return download

    def insert_download(self, name, md5, len_file, len_part):
        parts = []
        self.db.download.insert_one({
            "name": name,
            "md5": md5,
            "len_file": len_file,
            "len_part": len_part,
            "parts": parts
        })

    def update_download_parts(self, md5, sorted_parts):

        self.db.download.update_one({"md5": md5},
                                           {
                                                "$set": {"parts": sorted_parts}
                                           })