# coding=utf-8
# coding=utf-8
import socket, os, hashlib, select, sys, time

sys.path.insert(1, '/home/massa/Documenti/PycharmProjects/P2PKazaa')
from random import randint
import threading
from dbmodules.dbconnection import *
from helpers import *
from PyQt4 import QtCore, QtGui


class Tracker_Server(threading.Thread):
    """
        Ascolta sulla porta 3000
        Supernodo: Gestisce le comunicazioni tra directory e i peer: LOGI, LOGO, ADDF, DELF, FIND
        Peer: non utilizzata
    """

    def __init__(self, (client, address), dbConnect, output_lock, print_trigger, my_ipv4, my_ipv6, my_port):
        # QtCore.QThread.__init__(self, parent=None)
        threading.Thread.__init__(self)
        self.client = client
        self.address = address
        self.size = 1024
        self.dbConnect = dbConnect
        self.output_lock = output_lock
        self.print_trigger = print_trigger
        self.my_ipv4 = my_ipv4
        self.my_ipv6 = my_ipv6
        self.my_port = my_port

    def run(self):
        conn = self.client
        cmd = conn.recv(self.size)

        while len(cmd) > 0:

            if cmd[:4] == 'LOGI':
                # IPP2P:RND <> IPT:3000
                # > “LOGI”[4B].IPP2P[55B].PP2P[5B]
                # > LOGI172.030.008.001|fc00:0000:0000:0000:0000:0000:0008:000106000
                # < “ALGI”[4B].SessionID[16B]
                ipv4 = cmd[4:19]
                ipv6 = cmd[20:59]
                port = cmd[59:64]
                self.print_trigger.emit(
                    "<= " + str(self.address[0]) + "  " + cmd[:4] + '  ' + ipv4 + '  ' + ipv6 + '  ' + str(port), "10")
                # Spazio
                self.print_trigger.emit("", "10")
                sessionId = self.dbConnect.insert_session(ipv4, ipv6, port)
                msg = 'ALGI' + sessionId
                try:
                    conn.send(msg)
                    self.print_trigger.emit("=> " + str(self.address[0]) + "  " + msg[0:4] + '  ' + sessionId, "12")
                except socket.error, msg:
                    self.print_trigger.emit("Connection Error: %s" % msg, "11")
                except Exception as e:
                    self.print_trigger.emit('Error: ' + e.message, "11")
                # Spazio
                self.print_trigger.emit("", "10")
                print "login"

            elif cmd[:4] == 'LOGO':
                # IPP2P:RND <> IPT:3000
                # > “LOGO”[4B].SessionID[16B]
                # 1 < “NLOG”[4B].  # partdown[10B]
                # 2 < “ALOG”[4B].  # partown[10B]
                sessId = cmd[4:20]
                self.print_trigger.emit("<= " + str(self.address[0]) + "  " + cmd[0:4] + "  " + sessId, "10")

                # Spazio
                self.print_trigger.emit("", "10")

                delete = self.dbConnect.remove_session(sessId)
                if delete is True:
                    print "logout"
                    # logout concesso
                else:
                    print "not logout"
                    # logout non concesso

                '''

                msg = 'ALGO' + str(delete).zfill(3)

                try:

                    conn.send(msg)
                    self.print_trigger.emit("=> " + str(self.address[0]) + "  " + msg[0:4] + '  ' + msg[4:7], "12")

                except socket.error, msg:
                    self.print_trigger.emit("Connection Error: %s" % msg, "11")
                except Exception as e:
                    self.print_trigger.emit('Error: ' + e.message, "11")

                # Spazio
                self.print_trigger.emit("", "10")
                '''

                print "logout"

            elif cmd[:4] == 'AADR':
                #IPP2P:RND <> IPT:3000
                #> “ADDR”[4B].SessionID[16B].LenFile[10B].LenPart[6B].Filename[100B].Filemd5_i[32B]
                #< “AADR”[4B].  # part[8B]

                session_id = cmd[4:20]
                len_file = cmd[20:30]
                len_part = cmd[30:36]
                num_part = round(int(len_file)/int(len_part))
                response = cmd[:4] + num_part

                self.print_trigger.emit(
                    "<= " + str(self.address[0]) + "  " + cmd[0:4] + "  " + session_id + "  " + len_file + "  " +
                    len_part, "10")
                # Spazio
                self.print_trigger.emit("", "10")

                self.dbConnect.share_file(response)
                # TODO: Manca la risposta



                self.print_trigger.emit("File succesfully shared by " + str(self.address[0]), "12")
                # Spazio
                self.print_trigger.emit("", "10")

            elif cmd[:4] == 'LOOK':
                # IPP2P:RND <> IPT:3000
                # > “LOOK”[4B].SessionID[16B].Ricerca[20B]
                # < “ALOO”[4B].  # idmd5[3B].{Filemd5_i[32B].Filename_i[100B].LenFile[10B].LenPart[6B]}(i = 1..  # idmd5)

                print "look"

            elif cmd[:4] == 'FCHU':
                #IPP2P:RND <> IPT:3000
                #> “FCHU”[4B].SessionID[16B].Filemd5_i[32B]
                #< “AFCH”[4B].  # hitpeer[3B].{IPP2P_i[55B].PP2P_i[5B].PartList_i[#part8]}(i = 1..# hitpeer)

                # file = {
                #     "name": "prova.avi",
                #     "md5": "DYENCNYDABKASDKJCBAS8441132A57ST",
                #     "len_file": "1073741824",  # 1GB
                #     "len_part": "1048576"  # 256KB
                # }
                #
                # n_parts = int(file['len_file']) / int(file['len_part'])  # 1024
                #
                # n_parts8 = int(round(n_parts / 8))  # 128

                session_id = cmd[4:20]
                file_md5 = cmd[20:52]

                self.print_trigger.emit(
                    "<= " + str(self.address[0]) + "  " + cmd[0:4] + "  " + session_id +" " + file_md5, "10")
                # Spazio
                self.print_trigger.emit("", "10")

                hitpeers = self.dbConnect.get_parts(file_md5)

                #cerco nel db i peer che hanno parti del file richiesto
                # hitpeers = [
                #     {
                #         "ipv4": "172.030.008.001",
                #         "ipv6": "fc00:0000:0000:0000:0000:0000:0008:0001",
                #         "port": "06000",
                #         "part_list": ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(128)])
                #     },
                #     {
                #         "ipv4": "172.030.008.003",
                #         "ipv6": "fc00:0000:0000:0000:0000:0000:0008:0003",
                #         "port": "06000",
                #         "part_list": ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(128)])
                #     },
                #     {
                #         "ipv4": "172.030.008.004",
                #         "ipv6": "fc00:0000:0000:0000:0000:0000:0008:0004",
                #         "port": "06000",
                #         "part_list": ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(128)])
                #     }
                # ]

                n_hitpeers = hitpeers.count().zfill(3)

                msg = "AFCH" + n_hitpeers

                print_msg = "AFCH" + "  " + n_hitpeers
                for peer in hitpeers:
                    msg += peer['ipv4'] + "|" + peer['ipv6'] + peer['port'] + peer['part_list']
                    print_msg += "  " + peer['ipv4'] + "  " + peer['ipv6'] + "  " + peer['port'] + "  " + peer['part_list']

                try:
                    conn.sendall(msg)

                    self.print_trigger.emit(
                        "=> " + str(conn.getpeername()[0]) + "  " + print_msg, "12")
                    # Spazio
                    self.print_trigger.emit("", "10")

                except socket.error, msg:
                    self.print_trigger.emit('Socket Error: ' + str(msg), '11')
                except Exception as e:
                    self.print_trigger.emit('Error: ' + e.message, '11')


            elif cmd[:4] == 'RPAD':
                # IPP2P:RND <> IPT:3000
                # > “RPAD”[4B].SessionID[16B].Filemd5_i[32B].PartNum[8B]
                # < “APAD”[4B].  # Part[8B]

                print "download notify"

            else:
                self.print_trigger.emit("\n Command not recognized", "11")

            cmd = conn.recv(self.size)
