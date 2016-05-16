# coding=utf-8
import datetime
import re
import math
import sys
from pymongo import MongoClient
from helpers.helpers import *
import math
import threading

class MongoConnection():
    def __init__(self, out_lck, host="localhost", port=27017, db_name='torrent', conn_type="local", username='',
                 password=''):
        self.out_lck = out_lck
        self.db_lck = threading.Lock()
        self.host = host
        self.port = port
        try:
            self.conn = MongoClient()
            self.db = self.conn[db_name]
            if "sessions" not in self.db.collection_names():
                self.db.create_collection("sessions")
            if "files" not in self.db.collection_names():
                self.db.create_collection("files")
            if "download" not in self.db.collection_names():
                self.db.create_collection("download")
        except Exception as e:
            output(self.out_lck, "Could not connect to server: " + e.message)

    def get_sessions(self):
        """
            Restituisce tutte le sessioni aperte
        """
        self.db_lck.acquire()
        try:
            cursor = self.db.sessions.find()
        except Exception as e:
            output(self.out_lck, "Database Error > get_sessions: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()
            return list(cursor)

    def get_session(self, session_id):
        self.db_lck.acquire()
        try:
            session = self.db.sessions.find_one({"session_id": session_id})
        except Exception as e:
            output(self.out_lck, "Database Error > get_session: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()
            return session

    def insert_session(self, ipv4, ipv6, port):
        """
            Inserisce una nuova sessione, o restitusce il session_id in caso esista già
        """
        self.db_lck.acquire()
        try:
            cursor = self.db.sessions.find_one({"ipv4": ipv4,
                                                "ipv6": ipv6,
                                                "port": port
                                                })
        except Exception as e:
            output(self.out_lck, "Database Error > insert_session: " + e.message)
            self.db_lck.release()
        else:
            if cursor is not None:
                output(self.out_lck, "User already logged in")
                self.db_lck.release()
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
                    self.db_lck.release()
                    return session_id
                except Exception as e:
                    output(self.out_lck, "Database Error > insert_session: " + e.message)
                    self.db_lck.release()
                    return "0000000000000000"

    def remove_session(self, sessionID):
        self.db_lck.acquire()
        try:
            source = self.get_session(sessionID)
            files = self.db.files.find({'peers.session_id': sessionID})
        except Exception as e:
            output(self.out_lck, "Database Error > remove_session: " + e.message)
            self.db_lck.release()
        else:
            if files is None:
                self.db_lck.release()
                return True
            else:
                lista_file = list(files)
                for i in range(len(lista_file)):  # ciclo numero di file
                    index2 = lista_file[i]
                    # print index2['name']
                    index_peer = index2['peers']
                    n_parts = int(math.ceil(float(index2['len_file']) / float(index2['len_part'])))
                    parts = []
                    for j in range(0, n_parts):  # ciclo paerti del file
                        is_available = False
                        for peer in range(len(index_peer)):  # ciclo numero di peer
                            if index_peer[peer]['ipv4'] == source['ipv4']:
                                pass
                            else:
                                if index_peer[peer]['part_list'][j] == '1':
                                    # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer]['ipv4'] + " " + str(j)
                                    is_available = True
                                    break
                                else:
                                    # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer]['ipv4'] + " " + str(j)
                                    is_available = False
                        if is_available:
                            parts.append('1')  # parte presente
                        else:
                            parts.append('0')
                    if '0' in parts:
                        self.db_lck.release()
                        # print "parti mancanti"
                        return False
                    else:
                        self.db_lck.release()
                        return True
                        break

                self.db_lck.release()
                return True

    def get_parts(self, md5):
        """
            Restituisce una lista di peer con ip+porta e la stringa delle parti possedute
        """
        # cursor = self.db.hitpeers.find({"md5": md5}, {"_id": 0, "md5": 0, "session_id": 0}) vecchia versione db
        # db.getCollection('hitpeers').find({md5: "md52"}, { _id : 0, md5 : 0, session_id : 0 })
        self.db_lck.acquire()
        try:
            cursor = self.db.files.find({"md5": md5},
                                        {"_id": 0, "md5": 0, "peers.session_id": 0, "name": 0, "len_part": 0,
                                         "len_file": 0})
        except Exception as e:
            output(self.out_lck, "Database Error > get_parts: " + e.message)
            self.db_lck.release()
        else:
            if cursor.count() > 0:
                # TODO: vedere lista
                peers = list(cursor)
                prova = peers[0]
                self.db_lck.release()
                return prova['peers']
            else:
                output(self.out_lck, "Database Error > get_parts: No parts found for " + md5)
                self.db_lck.release()

    def update_parts(self, md5, sessionID, n_part):
        # TODO: funziona ma migliorabile
        """
            seleziono con md5 e sessionID la parte da modificare, poi cambio il bit con indice n_part
        """
        self.db_lck.acquire()
        try:
            part = self.db.files.find_one({"md5": md5, "peers.session_id": sessionID})
        except Exception as e:
            output(self.out_lck, "Database Error > update_parts: " + e.message)
            self.db_lck.release()

        if part is not None:
            try:
                # self.db.files.update({'md5': md5, 'peers.session_id': sessionID}, {"$set": {'part_list': str_part}})
                # db.files.update({'md5': "3md5", 'peers.session_id': "id1"}, {"$set": {'part_list': "dddd"}}) funziona
                # db.getCollection('files').update({"md5": "1md5"}, {"$set": {"peers.part_list": "bbb"}})

                peer = self.db.files.find_one({'md5': "3md5", 'peers.session_id': "id1"},
                                              {'peers': {"$elemMatch": {'session_id': "id1"}}})
                # db.getCollection('files').findOne({'md5' : "3md5", 'peers.session_id' : "id1"}, {"peers": {"$elemMatch": {"session_id": "id1"}}})
                str_part_old = peer['part_list']
                str_list = list(str_part_old)
                str_list[n_part] = '1'
                str_part = "".join(str_list)

                self.db.files.update({"md5": md5, 'peers': {'$elemMatch': {'session_id': sessionID}}},
                                     {"$set": {'peers.$.part_list': str_part}})
                # db.getCollection('files').update({"md5": "1md5", 'peers': {'$elemMatch' : {'session_id':"id1"}}},{"$set":{'peers.$.part_list': "aaaaaaaaaa"}})

            except Exception as e:
                output(self.out_lck, "Database Error > update_parts: " + e.message)
                self.db_lck.release()
        else:
            output(self.out_lck, "Database Error > update_parts: file " + md5 + " or user " + sessionID + " not found")
            self.db_lck.release()

    def insert_peer(self, name, md5, LenFile, LenPart, sessionID):
        self.db_lck.acquire()
        try:
            file = self.db.files.find_one({"md5": md5})
        except Exception as e:
            output(self.out_lck, "Database Error > insert_peer: " + e.message)
            self.db_lck.release()
        else:
            if file is not None:
                # update
                try:
                    # str_part ="\xff\xff\xff\xff"
                    str_part = chr(int("11111111", 2))
                    peer = self.db.sessions.find_one({"session_id": sessionID})
                    self.db.files.update({"md5": md5},
                                         {"$push": {"peers": [{"session_id": sessionID, "part_list": str_part}]}})
                    # self.db.files.update({"md5": md5}, {"$addToSet": {"peers": {"session_id": sessionID, "part_list": str_part}}})
                except Exception as e:
                    output(self.out_lck, "Database Error > insert_peer: " + e.message)
                    self.db_lck.release()
            else:
                # insert
                try:
                    n_parts = int(math.ceil(float(LenFile) / float(LenPart)))
                    str_part = ""
                    i = 0
                    for i in range(1, n_parts):
                        str_part = str_part + "1"

                    peer = self.db.sessions.find_one({"session_id": sessionID})

                    # TODO: sistemare database peer
                    self.db.files.insert_one({"name": name, "md5": md5, "len_file": LenFile, "len_part": LenPart,
                                              'peers': [
                                                  {'session_id': sessionID, 'ipv4': peer['ipv4'], 'ipv6': peer['ipv6'],
                                                   'port': peer['port'], 'part_list': str_part}]})
                except Exception as e:
                    output(self.out_lck, "Database Error > insert_peer: " + e.message)
                    self.db_lck.release()

    def get_files(self, query_str):
        """
            Restituisce i file il cui nome comprende la stringa query_str
        """
        self.db_lck.acquire()
        try:
            regexp = re.compile(query_str.strip(" "), re.IGNORECASE)
            if regexp == "*":
                files = self.db.files.find()
            else:
                files = self.db.files.find({"name": {"$regex": regexp}})
        except Exception as e:
            output(self.out_lck, "Database Error > get_files: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()
            return files

    def get_file(self, md5):
        self.db_lck.acquire()
        try:
            file = self.db.files.find_one({"md5": md5})
        except Exception as e:
            output(self.out_lck, "Database Error > get_file: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()
            return file

    def insert_file(self, name, md5, len_file, len_part):
        self.db_lck.acquire()
        try:
            self.db.files.insert_one({"name": name,
                                      "md5": md5,
                                      "len_file": len_file,
                                      "len_part": len_part})
        except Exception as e:
            output(self.out_lck, "Database Error > insert_file: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()

    def get_download(self, md5):
        self.db_lck.acquire()
        try:
            download = self.db.download.find_one({"md5": md5})
        except Exception as e:
            output(self.out_lck, "Database Error > get_download: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()
            return download

    def insert_download(self, name, md5, len_file, len_part):
        parts = []
        self.db_lck.acquire()
        try:
            self.db.download.insert_one({
                "name": name,
                "md5": md5,
                "len_file": len_file,
                "len_part": len_part,
                "parts": parts
            })
        except Exception as e:
            output(self.out_lck, "Database Error > insert_download: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()

    def update_download_parts(self, md5, sorted_parts):
        self.db_lck.acquire()
        try:
            self.db.download.update_one({"md5": md5},
                                        {
                                            "$set": {"parts": sorted_parts}
                                        })
        except Exception as e:
            output(self.out_lck, "Database Error > update_download_parts: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()

    def update_download(self, md5, part_n):
        self.db_lck.acquire()
        try:
            self.db.download.update(
                {"md5": md5, "parts": {"$elemMatch": {"n": part_n}}},
                {"$set": {"parts.$.downloaded": "true"}})
        except Exception as e:
            output(self.out_lck, "Database Error > update_download: " + e.message)
            self.db_lck.release()
        else:
            self.db_lck.release()

    def downloading(self, md5):
        self.db_lck.acquire()
        try:
            download = self.db.download.find_one({"md5": md5})
        except Exception as e:
            output(self.out_lck, "Database Error > downloading: " + e.message)
            self.db_lck.release()
        else:
            if download is not None:
                parts = download['parts']

                completed = True
                for part in parts:
                    if part['downloaded'] == "false":
                        completed = False
                self.db_lck.release()
                return completed
            else:
                output(self.out_lck, "Database Error > downloading: parts table not found for file " + md5)
                self.db_lck.release()
                return None

    def get_download_progress(self, md5):
        self.db_lck.acquire()
        try:
            download = self.db.download.find_one({"md5": md5})
        except Exception as e:
            output(self.out_lck, "Database Error > downloading: " + e.message)
            self.db_lck.release()
        else:
            if download is not None:
                parts = download['parts']
                parts_down = 0
                parts_tot = len(parts)

                for part in parts:
                    if part['downloaded'] == "true":
                        parts_down += 1

                self.db_lck.release()
                return parts_down, parts_tot
            else:
                output(self.out_lck, "Database Error > get_download_progress: parts table not found for file " + md5)
                self.db_lck.release()
                return None

    def get_downloadable_part(self, md5, idx):
        self.db_lck.acquire()
        try:
            cursor = self.db.download.find({"md5": md5}, {"parts": {"$elemMatch": {"n": idx}}})
            parts = list(cursor)
        except Exception as e:
            output(self.out_lck, "Database Error > get_downloadable_part: " + e.message)
            self.db_lck.release()
        else:
            if cursor.count() > 0:
                part = parts[0]['parts'][0]
                # part = parts['parts'][0]
                self.db_lck.release()
                return part
            else:
                output(self.out_lck, "Database Error > get_downloadable_part: part " + idx + " not found")
                self.db_lck.release()
                return None

    # partdown
    def get_number_partdown(self, sessionID):

        tot = 0
        self.db_lck.acquire()
        try:
            source = self.db.sessions.find_one({'session_id': sessionID})
            files = self.db.files.find({'peers.session_id': sessionID})
        except Exception as e:
            output(self.out_lck, "Database Error > get_number_partdown: " + e.message)
            self.db_lck.release()
        else:
            if files is None:
                self.db_lck.release()
                return 0
            else:
                lista_file = list(files)
                for i in range(len(lista_file)):  # ciclo numero di file
                    index2 = lista_file[i]
                    # print index2['name']
                    index_peer = index2['peers']
                    n_parts = int(math.ceil(float(index2['len_file']) / float(index2['len_part'])))
                    source_parts = self.db.files.find({'md5': index2['md5']},
                                                      {'peers': {"$elemMatch": {"session_id": sessionID}},
                                                       'peers.part_list': 1, '_id': 0})
                    source_bit = list(source_parts)[0]['peers'][0]['part_list']
                    parts = []
                    for j in range(0, len(source_bit)):  # ciclo paerti del file
                        is_available = False
                        if source_bit[j] == '1':
                            for peer in range(len(index_peer)):  # ciclo numero di peer
                                if index_peer[peer]['ipv4'] == source['ipv4']:
                                    pass
                                else:
                                    if index_peer[peer]['part_list'][j] == '1':
                                        # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer][
                                        #     'ipv4'] + " indice: " + str(j)
                                        is_available = True
                                        break
                                    else:
                                        # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer][
                                        #     'ipv4'] + " indicie: " + str(j)
                                        is_available = False
                            if is_available:
                                parts.append('1')  # parte presente
                            else:
                                parts.append('0')
                        else:
                            pass
                    tot += parts.count('1')

                self.db_lck.release()
                return tot

    # partown tutte le parti a 1 sul db
    def get_number_partown(self, sessionID):
        # TODO: da finre
        tot = 0
        self.db_lck.acquire()
        try:
            source = self.db.sessions.find_one({'session_id': sessionID})
            files = self.db.files.find({'peers.session_id': sessionID})
        except Exception as e:
            output(self.out_lck, "Database Error > get_number_partdown: " + e.message)
            self.db_lck.release()
        else:
            if files is None:
                self.db_lck.release()
                return 0
            else:
                lista_file = list(files)
                for i in range(len(lista_file)):  # ciclo numero di file
                    index2 = lista_file[i]
                    #print index2['name']
                    index_peer = index2['peers']
                    n_parts = int(math.ceil(float(index2['len_file']) / float(index2['len_part'])))
                    source_parts = self.db.files.find({'md5': index2['md5']},
                                                      {'peers': {"$elemMatch": {"session_id": sessionID}},
                                                       'peers.part_list': 1, '_id': 0})
                    source_bit = list(source_parts)[0]['peers'][0]['part_list']
                    parts = []
                    for j in range(0, len(source_bit)):  # ciclo parti del file
                        is_available = False
                        if source_bit[j] == '1':
                            for peer in range(len(index_peer)):  # ciclo numero di peer
                                if index_peer[peer]['ipv4'] == source['ipv4']:
                                    pass
                                else:
                                    if index_peer[peer]['part_list'][j] == '1':
                                        # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer][
                                        #     'ipv4'] + " indice: " + str(j)
                                        is_available = True
                                        break
                                    else:
                                        # print index_peer[peer]['part_list'][j] + " : " + index_peer[peer][
                                        #     'ipv4'] + " indicie: " + str(j)
                                        is_available = False
                            if is_available:
                                parts.append('1')  # parte presente
                            else:
                                parts.append('0')
                        else:
                            pass
                    tot += parts.count('1')

                self.db_lck.release()
                return tot

