import numpy as np
import time
import pyvisa

def pxa_receive_data(rm, filepath='D:/User_My_Documents/Instrument/My Documents/SA/state/test.state', adress='TCPIP::192.168.4.192'):
    try:
        pxainst = rm.open_resource(adress)
        print("Device connected successfully")
    except Exception:
        print("Unable to connect to oscilloscope at " + str(adress) + ". Aborting script.\n")
        sys.exit()
    pxainst.clear()
    pxainst.write('*CLS;*OPC')
    pxainst.write(f'MMEMory:LOAD:STATe "{filepath}"')
    pxainst.write(':FETC:SAN1?;')
    data = pxainst.read_raw()
    datastr=np.fromstring(data,  dtype=float, sep=',') 
    timestr = time.strftime("%Y%m%d-%H%M%S")
    filename = f'pxa_{timestr}.csv'
    with open(filename, 'wb') as filehandle:
        #Запись в файл 1-й столбец - ось "X" c частотами, 2-й столбец - ось "Y" c значениями
        np.savetxt(filehandle, np.vstack((datastr[::2],datastr[1::2])).T)
    pxainst.clear()
    pxainst.close()
    
if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    filepath='D:/User_My_Documents/Instrument/My Documents/SA/state/test.state'
    pxa_receive_data(rm, filepath)
