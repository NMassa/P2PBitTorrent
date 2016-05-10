# coding=utf-8
import time

from SharedFile import SharedFile
from helpers import connection
from helpers.helpers import *
import threading


class Client(object):

    session_id = None
    files_list = []
    #TODO cambiare sul mac con ./fileCondivisi
    path = "./fileCondivisi"
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
        self.fetch_thread = None

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

        # “LOGI”[4B].IPP2P[55B].PP2P[5B]
        output(self.out_lck, "Logging in...")
        msg = 'LOGI' + self.my_ipv4 + '|' + self.my_ipv6 + str(self.my_port).zfill(5)

        response_message = None
        try:
            self.tracker = None
            c = connection.Connection(self.track_ipv4, self.track_ipv6, self.track_port, self.print_trigger,
                                      "0")  # Creazione connessione con la directory
            c.connect()
            self.tracker = c.socket

            self.tracker.send(msg)  # Richiesta di login
            self.print_trigger.emit(
                '=> ' + str(self.tracker.getpeername()[0]) + '  ' + msg[0:4] + '  ' + self.my_ipv4 + '  ' +
                self.my_ipv6 + '  ' + str(self.my_port).zfill(5), "00")

            # Spazio
            self.print_trigger.emit("", "00")

            response_message = self.tracker.recv(20)  # Risposta della directory, deve contenere ALGI e il session id
            self.print_trigger.emit(
                '<= ' + str(self.tracker.getpeername()[0]) + '  ' + response_message[0:4] + '  ' + response_message[4:20],
                '02')

        except socket.error, msg:
            self.print_trigger.emit('Socket Error: ' + str(msg), '01')
        except Exception as e:
            self.print_trigger.emit('Error: ' + e.message, '01')

        if response_message is None:
            output(self.out_lck, 'No response from tracker. Login failed')
        else:
            self.session_id = response_message[4:20]
            if self.session_id == '0000000000000000' or self.session_id == '':
                output(self.out_lck, 'Troubles with the login procedure.\nPlease, try again.')
            else:
                output(self.out_lck, 'Session ID assigned by the directory: ' + self.session_id)
                output(self.out_lck, 'Login completed')
                self.print_trigger.emit('Login completed', '02')

    def logout(self):
        #IPP2P:RND <> IPT:3000
        #> “LOGO”[4B].SessionID[16B]
        #1 < “NLOG”[4B].  # partdown[10B]
        #2 < “ALOG”[4B].  # partown[10B]

        print "logout"

        output(self.out_lck, 'Logging out...')
        msg = 'LOGO' + self.session_id

        response_message = None
        try:
            self.check_connection()

            self.tracker.send(msg)  # Richeista di logout
            self.print_trigger.emit('=> ' + str(self.tracker.getpeername()[0]) + '  ' + msg[0:4] + '  ' + self.session_id,
                                    "00")

            # Spazio
            self.print_trigger.emit("", "00")

            response_message = self.tracker.recv(
                7)  # Risposta della directory, deve contenere ALGO e il numero di file che erano stati condivisi
            self.print_trigger.emit(
                '<= ' + str(self.tracker.getpeername()[0]) + '  ' + response_message[0:4] + '  ' + response_message[4:7],
                '02')

        except socket.error, msg:
            self.print_trigger.emit('Socket Error: ' + str(msg), '01')
        except Exception as e:
            self.print_trigger.emit('Error: ' + e.message, '01')

        if response_message is None:
            output(self.out_lck, 'No response from tracker. Login failed')
        elif response_message[0:4] == 'ALOG':
            self.session_id = None

            self.tracker.close()  # Chiusura della connessione
            output(self.out_lck, 'Logout completed')
            self.print_trigger.emit('Logout completed', '02')
        elif response_message[0:4] == "NLOG":
            self.session_id = None

            self.tracker.close()  # Chiusura della connessione
            output(self.out_lck, 'Logout completed')
            self.print_trigger.emit('Logout completed', '02')
        else:
            output(self.out_lck, 'Error: unknown response from tracker.\n')
            self.print_trigger.emit('Error: unknown response from tracker.', '01')

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

                            len_part = 262144  # 256KB
                            #ipv4+ipv6 in byte
                            ip_concat = self.my_ipv4 + self.my_ipv6
                            bytes_ip = str.encode(ip_concat)
                            #my_decoded_str = str.decode(bytes)

                            LenFile = str(os.path.getsize(self.path+"/"+file.name)).zfill(10)
                            LenPart = str(len_part).zfill(6)
                            FileName = file.name.ljust(100)
                            Filemd5_i = hashfile_ip(open(self.path+"/"+file.name, "rb"), hashlib.md5(), bytes_ip)

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

        output(self.out_lck, 'Insert search term:')
        try:
            ricerca = raw_input()  # Inserimento del parametro di ricerca
        except SyntaxError:
            ricerca = None
        if ricerca is None:
            output(self.out_lck, 'Please select an option')
        else:
            output(self.out_lck, "Searching files that match: " + ricerca)

            msg = 'LOOK' + self.session_id + ricerca.ljust(20)

            response_message = None
            try:
                self.check_connection()

                self.tracker.send(msg)
                self.print_trigger.emit(
                    '=> ' + str(self.tracker.getpeername()[0]) + '  ' + msg[0:4] + '  ' + self.session_id +
                    '  ' + ricerca.ljust(20), "00")

                # Spazio
                self.print_trigger.emit("", "00")

                response_message = self.tracker.recv(4)

                self.print_trigger.emit(
                    '<= ' + str(self.tracker.getpeername()[0]) + '  ' + response_message[0:4],
                    '02')
            except socket.error, msg:
                # output(self.out_lck, 'Socket Error: ' + str(msg))
                self.print_trigger.emit('Socket Error: ' + str(msg), '01')
            except Exception as e:
                # output(self.out_lck, 'Error: ' + e.message)
                self.print_trigger.emit('Error: ' + e.message, '01')

            if response_message is None:
                output(self.out_lck, 'No response from tracker. Look failed')
            elif response_message[0:4] == 'ALOO':

                idmd5 = None
                try:
                    idmd5 = self.tracker.recv(3)  # Numero di identificativi md5
                except socket.error as e:
                    print 'Socket Error: ' + e.message
                except Exception as e:
                    print 'Error: ' + e.message

                if idmd5 is None:
                    print 'Error: idmd5 is blank'
                else:
                    try:
                        idmd5 = int(idmd5)
                    except ValueError:
                        print "idmd5 is not a number"
                    else:
                        if idmd5 == 0:
                            print "No results found for search term: " + ricerca
                        elif idmd5 > 0:  # At least one result
                            available_files = []

                            try:
                                for idx in range(0, idmd5):  # Per ogni identificativo diverso si ricevono:
                                    # md5, nome del file, numero di copie, elenco dei peer che l'hanno condiviso

                                    file_i_md5 = self.tracker.recv(32)  # md5 dell'i-esimo file (32 caratteri)
                                    file_i_name = self.tracker.recv(
                                        100).strip()  # nome dell'i-esimo file (100 caratteri compresi spazi)
                                    len_file_i = self.tracker.recv(10)
                                    len_part_i = self.tracker.recv(6)

                                    available_files.append({"name": file_i_name,
                                                            "md5": file_i_md5,
                                                            "len_file": len_file_i,
                                                            "len_part": len_part_i
                                                            })

                            except socket.error, msg:
                                print 'Socket Error: ' + str(msg)
                            except Exception as e:
                                print 'Error: ' + e.message

                            if len(available_files) == 0:
                                print "No results found for search term: " + ricerca
                            else:
                                print "Select a file to download ('c' to cancel): "
                                for idx, file in enumerate(available_files):  # visualizza i risultati della ricerca
                                    print str(idx) + ": " + file['name']

                                selected_file = None
                                while selected_file is None:
                                    try:
                                        option = raw_input()  # Selezione del file da scaricare
                                    except SyntaxError:
                                        option = None

                                    if option is None:
                                        print 'Please select an option'
                                    elif option == 'c':
                                        return
                                    else:
                                        try:
                                            selected_file = int(option)
                                        except ValueError:
                                            print "A number is required"

                                file_to_download = available_files[
                                    selected_file]  # Recupero del file selezionato dalla lista dei risultati



                                # avvio un thread che esegue la fetch ogni 60(10) sec

                                self.fetch_thread = threading.timer(10, self.fetch(file_to_download))
                                self.fetch_thread.start()
                                #self.fetch(file_to_download)

            else:
                output(self.out_lck, 'Error: unknown response from tracker.\n')
                self.print_trigger.emit('Error: unknown response from tracker.', '01')

    def fetch(self, file):
        # IPP2P:RND <> IPT:3000
        # > “FCHU”[4B].SessionID[16B].Filemd5_i[32B]
        # < “AFCH”[4B].#hitpeer[3B].{IPP2P_i[55B].PP2P_i[5B].PartList_i[#part8]}(i = 1..# hitpeer)

        # file = {
        #     "name": "prova.avi",
        #     "md5": "DYENCNYDABKASDKJCBAS8441132A57ST",
        #     "len_file": "1073741824",  # 1GB
        #     "len_part": "1048576"  # 256KB
        # }

        n_parts = int(file['len_file']) / int(file['len_part'])  # 1024

        n_parts8 = int(round(n_parts/8))  # 128

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

            n_hitpeers = int(self.tracker.recv(3))

            if n_hitpeers is not None and n_hitpeers > 0:

                hitpeers = []

                for i in range(0, n_hitpeers):
                    hitpeer_ipv4 = self.tracker.recv(16).replace("|", "")
                    hitpeer_ipv6 = self.tracker.recv(39)
                    hitpeer_port = self.tracker.recv(5)
                    hitpeer_partlist = self.tracker.recv(n_parts8)

                    hitpeers.append({
                        "ipv4": hitpeer_ipv4,
                        "ipv6": hitpeer_ipv6,
                        "port": hitpeer_port,
                        "part_list": hitpeer_partlist
                    })

                if hitpeers:
                    # cerco la tabella delle parti di cui fare il download se non esiste la creo

                    download = self.dbConnect.download.find_one({"md5": file['md5']})
                    if download:
                        parts = download['parts']
                    else:
                        parts = []
                        self.dbConnect.downlaod.inser_one({
                            "name": file['name'],
                            "md5": file['md5'],
                            "len_file": file['len_file'],  # 1GB
                            "len_part": file['len_part'],  # 256KB
                            "parts": parts
                        })

                    # scorro i risultati della FETCH ed aggiorno la lista delle parti in base alla disponibilità
                    for hp in hitpeers:
                        part_count = 1
                        # VALIDO PER part_list salvata come stringa di caratteri ASCII

                        # for c in hp['part_list']:
                        #     bits = bin(ord(c)).zfill(8)[2:]  # Es: 0b01001101
                        #     for bit in bits:
                        #         if bit == 1:  # se la parte è disponibile
                        #             found = False
                        #
                        #             # cerco la parte nella lista, se esiste aggiungo il peer altrimenti la creo
                        #             for part in parts:
                        #                 if part['n'] == part_count:
                        #                     found = True
                        #
                        #                     peers = part['peers']
                        #                     peers.append({
                        #                         "ipv4": hp['ipv4'],
                        #                         "ipv6": hp['ipv6'],
                        #                         "port": hp['port']
                        #                     })
                        #
                        #                     part['occ'] = int(part['occ']) + 1
                        #                     part['peers'] = peers
                        #
                        #             if not found:
                        #                 parts.append({
                        #                     "n": part_count,
                        #                     "occ": 1,
                        #                     "peers": [].append({
                        #                         "ipv4": hp['ipv4'],
                        #                         "ipv6": hp['ipv6'],
                        #                         "port": hp['port']
                        #                     })
                        #                 })
                        #
                        #     part_count += 1

                        # VALIDO PER part_list salvata come sequenza di 0 e 1
                        for c in hp['part_list']:
                            bit = int(c)
                            if bit == 1:  # se la parte è disponibile
                                found = False

                                # cerco la parte nella lista, se esiste aggiungo il peer altrimenti la creo
                                for part in parts:
                                    if part['n'] == part_count:
                                        found = True

                                        peers = part['peers']
                                        peers.append({
                                            "ipv4": hp['ipv4'],
                                            "ipv6": hp['ipv6'],
                                            "port": hp['port']
                                        })

                                        part['occ'] = int(part['occ']) + 1

                                        part['peers'] = peers

                                if not found:
                                    parts.append({
                                        "n": part_count,
                                        "occ": 1,
                                        "downloaded": "false",
                                        "peers": [].append({
                                            "ipv4": hp['ipv4'],
                                            "ipv6": hp['ipv6'],
                                            "port": hp['port']
                                        })
                                    })

                            part_count += 1

                    # ordino la lista delle parti in base alle occorrenze in modo crescente
                    sorted_parts = sorted(parts, key=lambda k: k['occ'])

                    # aggiorno la lista già ordinata
                    self.dbConnect.downlaod.update_one({"md5": file['md5']},
                                                       {
                                                            "$set": {"parts": sorted_parts}
                                                       })

            else:
                output(self.out_lck, 'No peers found.\n')
                self.print_trigger.emit('No peers found.\n', '01')

        else:
            output(self.out_lck, 'Error: unknown response from tracker.\n')
            self.print_trigger.emit('Error: unknown response from tracker.', '01')

    def downlaod(self, md5):
        # IPP2P:RND <> IPP2P:PP2P
        # > “RETP”[4B].Filemd5_i[32B].PartNum[8B]
        # < “AREP”[4B].  # chunk[6B].{Lenchunk_i[5B].data[LB]}(i=1..#chunk)



        # Terminato il download fermo la fetch
        self.fetch_thread.stop()

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

