from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time
import traceback, sys
import dso
import pxa
import pyvisa
#Только тест стабильного коннекта устройств - в функциях происходит открытие,закрытие соединения и запись в файлы полученных данных
#Начальные параметры устройств 
#filepath путь до файла на Устройстве с сохраненным состоянием 
delay=1
configpxa={ "adress": "TCPIP::192.168.4.192",
        "filepath":"D:/User_My_Documents/Instrument/My Documents/SA/state/test.state"
}
configdso={ "adress":"TCPIP::192.168.4.16", 
        "points":1000,
        "tout":1000
}
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()    

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

class Obj:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        layout = QVBoxLayout()
        self.l = QLabel("Start")
        b = QPushButton("Run!")

        self.pxa = Obj(**configpxa)
        self.dso = Obj(**configdso)
        
        b.pressed.connect(self.run)
        layout.addWidget(self.l)
        layout.addWidget(b)
        w = QWidget()
        w.setLayout(layout)
        self.setCentralWidget(w)
        self.show()

        self.threadpool = QThreadPool()
        
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
    
    
    def execute_pxa(self, *args, **kwargs):
        while True:
            pxa.pxa_receive_data(*args, **kwargs)
            QThread.sleep(delay)
        return "Done."
    
    def execute_dso(self, *args, **kwargs):
        while  True:
            dso.dso_receive_data(*args, **kwargs)
            QThread.sleep(delay)
        return "Done."
 
    def thread_complete(self):
        print("THREAD COMPLETE!")
 
    def run(self):
        """Инициализация pyvisa и создание отдельных потоков"""
        rm = pyvisa.ResourceManager()
        workerpxa = Worker(self.execute_pxa, rm, filepath=self.pxa.filepath, adress=self.pxa.adress) # Any other args, kwargs are passed to the run function
        workerdso = Worker(self.execute_dso, rm, adress=self.dso.adress, points=self.dso.points, tout=self.dso.tout)
        workerpxa.signals.finished.connect(self.thread_complete)
        workerdso.signals.finished.connect(self.thread_complete)
        self.threadpool.start(workerpxa)
        self.threadpool.start(workerdso) 
    
app = QApplication([])
window = MainWindow()
app.exec_()