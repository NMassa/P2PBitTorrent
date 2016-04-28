# coding=utf-8
import socket, os, hashlib, select, sys, time

# sys.path.insert(1, '/home/massa/Documenti/PycharmProjects/P2PKazaa')
from random import randint
import threading
from dbmodules.dbconnection import *
from PyQt4 import QtCore, QtGui
from helpers import *


class Peer_Server(threading.Thread):
    """
        Ascolta sulla porta 6000
        Supernodo: Gestisce le comunicazioni con gli altri i supernodi e l'invio dei file: SUPE, ASUP, QUER, AQUE, RETR
        Peer: Gestisce la propagazione dei pacchetti SUPE a tutti i vicini e l'invio dei file
    """

    def __init__(self, (client, address), dbConnect, output_lock, print_trigger, my_ipv4, my_ipv6, my_port):
        #QtCore.QThread.__init__(self, parent=None)
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
            if cmd[:4] == 'RETP':
                #IPP2P:RND <> IPP2P:PP2P
                #> “RETP”[4B].Filemd5_i[32B].PartNum[8B]
                #< “AREP”[4B].  # chunk[6B].{Lenchunk_i[5B].data[LB]}(i=1..#chunk)

                print "RETP"

            else:
                self.print_trigger.emit("Command not recognized", 11)

            cmd = conn.recv(self.size)
