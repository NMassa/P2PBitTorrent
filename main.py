# coding=utf-8
import threading
from Client.Client import Client
from servers import multithread_server
from dbmodules.dbconnection import *
from helpers.helpers import *
import config
from PyQt4 import QtCore, QtGui
from GUI.ui import *
#from GUI.main_window import Ui_MainWindow
from GUI import main_window
sys.path.insert(1, '/Users/stefano/Desktop/P2Pkazaa')


class Main(QtCore.QThread):
    print_trigger = QtCore.pyqtSignal(str, str)

    def __init__(self,parent=None):
        super(Main, self).__init__(parent)

    def run(self):
        out_lck = threading.Lock()
        db = MongoConnection(out_lck)
        client = Client(config.my_ipv4, config.my_ipv6, int(config.my_port), None, None, None, db, out_lck, self.print_trigger)
        client.share()

        print "main"


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    mainwindow = main_window.Ui_MainWindow()
    mainwindow.show()

    main = Main()
    main.print_trigger.connect(mainwindow.print_on_main_panel)
    main.start()

    sys.exit(app.exec_())
