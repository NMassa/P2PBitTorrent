# coding=utf-8
import time

from SharedFile import SharedFile
from helpers import connection
from helpers.helpers import *


class Client(object):

    session_id = None
    files_list = []
    #TODO cambiare sul mac con ./fileCondivisi
    path="./fileCondivisi"
    tracker = None

    def __init__(self, my_ipv4, my_ipv6, my_port, track_ipv4, track_ipv6, track_port, database, out_lck, print_trigger):
        """
            Costruttore della classe Peer
        """

        self.my_ipv4 = my_ipv4
        self.my_ipv6 = my_ipv6
        self.my_port = my_port
        self.track_ipv4 = track_ipv4
        self.track_ipv6 = track_ipv6
        self.track_port = track_port
        self.dbConnect = database
        self.out_lck = out_lck
        self.print_trigger = print_trigger

        # Searching for shareable files
        for root, dirs, files in os.walk(self.path):
            for file in files:
                file_md5 = hashfile(open(self.path+"/" + file, 'rb'), hashlib.md5())
                new_file = SharedFile(file, file_md5)
                self.files_list.append(new_file)



    def login(self):
        #IPP2P:RND <> IPT:3000
        #> “LOGI”[4B].IPP2P[55B].PP2P[5B]
        #< “ALGI”[4B].SessionID[16B]

        print "login"


    def logout(self):
        #IPP2P:RND <> IPT:3000
        #> “LOGO”[4B].SessionID[16B]
        #1 < “NLOG”[4B].  # partdown[10B]
        #2 < “ALOG”[4B].  # partown[10B]

        print "logout"

    def share(self):
        # IPP2P:RND <> IPT:3000
        # > “ADDR”[4B].SessionID[16B].LenFile[10B].LenPart[6B].Filename[100B].Filemd5_i[32B]
        # < “AADR”[4B].  # part[8B]

        found = False
        while not found:
            output(self.out_lck, '\nSelect a file to share (\'c\' to cancel):')
            for idx, file in enumerate(self.files_list):
                output(self.out_lck, str(idx) + ": " + file.name)

            try:
                option = raw_input()  # Selezione del file da condividere tra quelli disponibili (nella cartella shareable)
            except SyntaxError:
                option = None

            if option is None:
                output(self.out_lck, 'Please select an option')
            elif option == "c":
                break
            else:
                try:
                    int_option = int(option)
                except ValueError:
                    output(self.out_lck, "A number is required")
                else:
                    for idx, file in enumerate(self.files_list):  # Ricerca del file selezionato
                        if idx == int_option:
                            found = True

                            output(self.out_lck, "Adding file " + file.name)
                            print '\nSelect a file to share (\'c\' to cancel):'

                            len_part = 262144 #Byte
                            #ipv4+ipv6 in byte
                            ip_concat = self.my_ipv4 + self.my_ipv6
                            bytes_ip = str.encode(ip_concat)
                            #my_decoded_str = str.decode(bytes)

                            LenFile=str(os.path.getsize(self.path+"/"+file.name)).ljust(10)
                            LenPart=len_part
                            FileName=file.name.ljust(100)
                            Filemd5_i=hashfile_ip(open(self.path+"/"+file.name ,"rb"), hashlib.md5(),bytes_ip).ljust(32)

                            msg = "ADDR" + str(self.session_id) + str(LenFile) + str(LenPart) + str(FileName) + str(Filemd5_i)

                            response_message = None

                            try:
                                self.check_connection()

                                self.tracker.send(msg)
                                self.print_trigger.emit(
                                    '=> ' + str(self.tracker.getpeername()[0]) + '  ' + msg[0:4] + '  ' + self.session_id +
                                    '  '+ str(LenFile).strip("") + '  '+ str(LenPart).strip("")+'  ' + str(FileName).strip("")+
                                    '  '+ str(Filemd5_i).strip(""), "00")

                                # Spazio
                                self.print_trigger.emit("", "00")

                            except socket.error, msg:
                                # output(self.out_lck, 'Socket Error: ' + str(msg))
                                self.print_trigger.emit('Socket Error: ' + str(msg), '01')
                            except Exception as e:
                                # output(self.out_lck, 'Error: ' + e.message)
                                self.print_trigger.emit('Error: ' + e.message, '01')

                    if not found:
                        output(self.out_lck, 'Option not available')


    def look(self):
        #IPP2P:RND <> IPT:3000
        #> “LOOK”[4B].SessionID[16B].Ricerca[20B]
        #< “ALOO”[4B].  # idmd5[3B].{Filemd5_i[32B].Filename_i[100B].LenFile[10B].LenPart[6B]}(i = 1..  # idmd5)

        print "search"

    def fetch(self, file):
        # IPP2P:RND <> IPT:3000
        # > “FCHU”[4B].SessionID[16B].Filemd5_i[32B]
        # < “AFCH”[4B].#hitpeer[3B].{IPP2P_i[55B].PP2P_i[5B].PartList_i[#part8]}(i = 1..# hitpeer)

        file = {
            "name": "prova.avi",
            "md5": "DYENCNYDABKASDKJCBAS8441132A57ST",
            "len_file": "1073741824", #1GB
            "len_part": "1048576" #256KB
        }
        # #part = 4096
        # #part8 = supint[#part/8] = 512

        print "update part list"

        output(self.out_lck, "Fetching parts informations about file " + file['name'])
        msg = "FCHU" + self.session_id + file['md5']

        response_message = None
        try:
            self.check_connection()

            self.tracker.sendall(msg)
            self.print_trigger.emit('=> ' + str(self.tracker.getpeername()[0]) + '  ' + msg[0:4] + '  ' +
                                    self.session_id + '  ' + file['md5'], "00")

            # Spazio
            self.print_trigger.emit("", "00")

            response_message = self.tracker.recv(4)
            self.print_trigger.emit('<= ' + str(self.tracker.getpeername()[0]) + '  ' + response_message[0:4], '02')

        except socket.error, msg:
            self.print_trigger.emit('Socket Error: ' + str(msg), '01')
        except Exception as e:
            self.print_trigger.emit('Error: ' + e.message, '01')

        if response_message is None:
            output(self.out_lck, 'No response from tracker. Fetch failed')
        elif response_message[0:4] == 'AFCH':




        else:
            output(self.out_lck, 'Error: unknown response from tracker.\n')
            self.print_trigger.emit('Error: unknown response from tracker.', '01')

    def downlaod(self, host_ipv4, host_ipv6, host_port, filemd5, part_n):
        # IPP2P:RND <> IPP2P:PP2P
        # > “RETP”[4B].Filemd5_i[32B].PartNum[8B]
        # < “AREP”[4B].  # chunk[6B].{Lenchunk_i[5B].data[LB]}(i=1..#chunk)

        print "download"

    def notify_tracker(self):
        #IPP2P:RND <> IPT:3000
        #> “RPAD”[4B].SessionID[16B].Filemd5_i[32B].PartNum[8B]
        #< “APAD”[4B].  # Part[8B]

        print "notify tracker"

    '''
        Helper methods
    '''
    def check_connection(self):
        if not self.alive(self.tracker):
            c = connection.Connection(self.track_ipv4, self.track_ipv6, self.track_port,
                                      self.print_trigger, "0")  # Creazione connessione con il tracker
            c.connect()
            self.tracker = c.socket

    def alive(self, socket):
        try:
            if socket.socket() != None:
                return True
        except Exception:
            pass
            return False

