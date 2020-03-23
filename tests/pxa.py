import os
import sys
import time
import pyvisa
import numpy as np

def pxa_receive_data(rm, filepath='D:/User_My_Documents/Instrument/My Documents/SA/state/test.state', adress='TCPIP::192.168.4.192'):
    try:
        pxainst = rm.open_resource(adress)
        
        print("Device connected successfully")
    except Exception:
        print("Unable to connect to oscilloscope at " + str(adress) + ". Aborting script.\n")
        sys.exit()
    pxainst.clear()
    pxainst.read_termination = '\r\n'
    pxainst.write_termination = '\r\n'
    #3 параметра влияющих на возникновение ошибок при считывании
    #Символ окончания read_termination write_termination '\r\n'
    pxainst.timeout = 20000 #Время задержки
    pxainst.chunk_size=1024 #размер пакета
    pxainst.write(f'MMEMory:LOAD:STATe "{filepath}"')
    pxainst.write('FORMat:TRACe:DATA ASC')
    #100 раз считываем данные с анализатора спектра
    for i in range(100):
        pxainst.write(':FETC:SAN1?;')
        timestr = time.strftime("%H:%M:%S")
        print(f'Посылка запроса на анализатор {timestr}')
        data = pxainst.read_raw()
        timestr = time.strftime("%H:%M:%S")
        time.sleep(1)
        print(f"Получен Ответ от анализатора спектра {timestr}")
    pxainst.clear()
    pxainst.close()
    datastr=np.fromstring(data,  dtype=float, sep=',') 
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = f'pxa_{timestr}.csv'
    with open(filename, 'wb') as filehandle:
        #Запись в файл 1-й столбец - ось "X" c частотами, 2-й столбец - ось "Y" c значениями
        np.savetxt(filehandle, np.vstack((datastr[::2],datastr[1::2])).T)
    
    
if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    filepath='D:/User_My_Documents/Instrument/My Documents/SA/state/test.state'
    pxa_receive_data(rm, filepath)
