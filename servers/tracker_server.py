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
                # < “ALGI”[4B].SessionID[16B]

                print "login"

            elif cmd[:4] == 'LOGO':
                # IPP2P:RND <> IPT:3000
                # > “LOGO”[4B].SessionID[16B]
                # 1 < “NLOG”[4B].  # partdown[10B]
                # 2 < “ALOG”[4B].  # partown[10B]

                print "logout"

            elif cmd[:4] == 'AADR':
                #IPP2P:RND <> IPT:3000
                #> “ADDR”[4B].SessionID[16B].LenFile[10B].LenPart[6B].Filename[100B].Filemd5_i[32B]
                #< “AADR”[4B].  # part[8B]

                sessId = cmd[4:20]
                len_file = cmd[20:30]
                len_part = cmd[30:36]
                num_part = round(int(len_file)/int(len_part))
                response = cmd[:4] + num_part

                self.print_trigger.emit(
                    "<= " + str(self.address[0]) + "  " + cmd[0:4] + "  " + len_file,+" "+len_part ,"10")

                self.dbConnect.share_file(response)
                self.print_trigger.emit("File succesfully shared by " + str(self.address[0]), "12")

                # Spazio
                self.print_trigger.emit("", "10")

                print "add file"

            elif cmd[:4] == 'LOOK':
                # IPP2P:RND <> IPT:3000
                # > “LOOK”[4B].SessionID[16B].Ricerca[20B]
                # < “ALOO”[4B].  # idmd5[3B].{Filemd5_i[32B].Filename_i[100B].LenFile[10B].LenPart[6B]}(i = 1..  # idmd5)

                print "look"

            elif cmd[:4] == 'FCHU':
                #IPP2P:RND <> IPT:3000
                #> “FCHU”[4B].SessionID[16B].Filemd5_i[32B]
                #< “AFCH”[4B].  # hitpeer[3B].{IPP2P_i[55B].PP2P_i[5B].PartList_i[#part8]}(i = 1..# hitpeer)

                print "fetch"

            elif cmd[:4] == 'RPAD':
                # IPP2P:RND <> IPT:3000
                # > “RPAD”[4B].SessionID[16B].Filemd5_i[32B].PartNum[8B]
                # < “APAD”[4B].  # Part[8B]

                print "download notify"

            else:
                self.print_trigger.emit("\n Command not recognized", "11")

            cmd = conn.recv(self.size)
