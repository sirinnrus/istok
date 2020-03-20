import sys
import visa # PyVisa info @ http://PyVisa.readthedocs.io/en/stable/
import time
import struct
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import time
import pyvisa

def dso_receive_data(rm, adress="TCPIP::192.168.4.16", points=1000, tout=1000):
    USER_REQUESTED_POINTS = points
    SCOPE_VISA_ADDRESS = adress
    GLOBAL_TOUT =  tout
    
    try:
        KsInfiniiVisionX = rm.open_resource(SCOPE_VISA_ADDRESS)
        print("Device connected successfully")
    except Exception:
        print("Unable to connect to oscilloscope at " + str(SCOPE_VISA_ADDRESS) + ". Aborting script.\n")
        sys.exit()

    KsInfiniiVisionX.timeout = GLOBAL_TOUT
    KsInfiniiVisionX.clear()

    IDN = str(KsInfiniiVisionX.query("*IDN?"))
    ## Parse IDN
    IDN = IDN.split(',') # IDN parts are separated by commas, so parse on the commas
    MODEL = IDN[1]
    if list(MODEL[1]) == "9": # This is the test for the PXIe scope, M942xA)
        NUMBER_ANALOG_CHS = 2
    else:
        NUMBER_ANALOG_CHS = int(MODEL[len(MODEL)-2])
    NUMBER_CHANNELS_ON = 0

    KsInfiniiVisionX.write(":WAVeform:POINts:MODE MAX") # MAX mode works for all acquisition types, so this is done here to avoid Acq. Type vs points mode problems. Adjusted later for specific acquisition types.
    ## Channel 1
    ts=time.time()
    On_Off = int(KsInfiniiVisionX.query(":CHANnel1:DISPlay?")) # Is the channel displayed? If not, don't pull.
    if On_Off == 1:
        Channel_Acquired = int(KsInfiniiVisionX.query(":WAVeform:SOURce CHANnel1;:WAVeform:POINts?"))  # The scope can acquire waveform data even if the channel is off (in some cases) - so modify as needed
            ## If this returns a zero, then this channel did not capture data and thus there are no points
            ## Note that setting the :WAV:SOUR to some channel has the effect of turning it on
        
    else:
        Channel_Acquired = 0
    if Channel_Acquired == 0:
        CHAN1_STATE = 0
        KsInfiniiVisionX.write(":CHANnel1:DISPlay OFF") # Setting a channel to be a waveform source turns it on... so if here, turn it off.
        NUMBER_CHANNELS_ON += 0
    else:
        CHAN1_STATE = 1
        NUMBER_CHANNELS_ON += 1
        if NUMBER_CHANNELS_ON == 1:
            FIRST_CHANNEL_ON = 1
        LAST_CHANNEL_ON = 1
        Pre = KsInfiniiVisionX.query(":WAVeform:SOURce CHANnel1;:WAVeform:PREamble?").split(',')
        Y_INCrement_Ch1 = float(Pre[7]) # Voltage difference between data points; Could also be found with :WAVeform:YINCrement? after setting :WAVeform:SOURce
        Y_ORIGin_Ch1    = float(Pre[8]) # Voltage at center screen; Could also be found with :WAVeform:YORigin? after setting :WAVeform:SOURce
        Y_REFerence_Ch1 = float(Pre[9]) # Specifies the data point where y-origin occurs, always zero; Could also be found with :WAVeform:YREFerence? after setting :WAVeform:SOURce
        
    if NUMBER_CHANNELS_ON == 0:
        KsInfiniiVisionX.clear()
        KsInfiniiVisionX.close()
        sys.exit("No data has been acquired. Properly closing scope and aborting script.")

    ## Setup data export - For repetitive acquisitions, this only needs to be done once unless settings are changed
    KsInfiniiVisionX.write(":WAVeform:FORMat WORD") # 16 bit word format... or BYTE for 8 bit format - WORD recommended, see more comments below when the data is actually retrieved
    KsInfiniiVisionX.write(":WAVeform:BYTeorder LSBFirst") # Explicitly set this to avoid confusion - only applies to WORD FORMat
    KsInfiniiVisionX.write(":WAVeform:UNSigned 0")
    ACQ_TYPE = str(KsInfiniiVisionX.query(":ACQuire:TYPE?")).strip("\n")
    if ACQ_TYPE == "AVER" or ACQ_TYPE == "HRES": # Don't need to check for both types of mnemonics like this: if ACQ_TYPE == "AVER" or ACQ_TYPE == "AVERage": becasue the scope ALWAYS returns the short form
        POINTS_MODE = "NORMal" # Use for Average and High Resoultion acquisition Types.
    else:
        POINTS_MODE = "RAW"

    KsInfiniiVisionX.write(":WAVeform:SOURce CHANnel" + str(FIRST_CHANNEL_ON))
    KsInfiniiVisionX.write(":WAVeform:POINts MAX") # This command sets the points mode to MAX AND ensures that the maximum # of points to be transferred is set, though they must still be on screen
    KsInfiniiVisionX.write(":WAVeform:POINts:MODE " + str(POINTS_MODE))
    MAX_CURRENTLY_AVAILABLE_POINTS = int(KsInfiniiVisionX.query(":WAVeform:POINts?")) # This is the max number of points currently available - this is for on screen data only - Will not change channel to channel.
    if USER_REQUESTED_POINTS < 100:
        USER_REQUESTED_POINTS = 100
    if MAX_CURRENTLY_AVAILABLE_POINTS < 100:
        MAX_CURRENTLY_AVAILABLE_POINTS = 100

    if USER_REQUESTED_POINTS > MAX_CURRENTLY_AVAILABLE_POINTS or ACQ_TYPE == "PEAK":
        USER_REQUESTED_POINTS = MAX_CURRENTLY_AVAILABLE_POINTS

    KsInfiniiVisionX.write(":WAVeform:POINts " + str(USER_REQUESTED_POINTS))

    ## Then ask how many points it will actually give you, as it may not give you exactly what you want.
    NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE = int(KsInfiniiVisionX.query(":WAVeform:POINts?"))

    ## Get timing pre-amble data and create time axis
    ## One could just save off the preamble factors and #points and post process this later...
    Pre = KsInfiniiVisionX.query(":WAVeform:PREamble?").split(',')
    X_INCrement = float(Pre[4]) # Time difference between data points; Could also be found with :WAVeform:XINCrement? after setting :WAVeform:SOURce
    X_ORIGin    = float(Pre[5]) # Always the first data point in memory; Could also be found with :WAVeform:XORigin? after setting :WAVeform:SOURce
    X_REFerence = float(Pre[6]) # Specifies the data point associated with x-origin; The x-reference point is the first point displayed and XREFerence is always 0.; Could also be found with :WAVeform:XREFerence? after setting :WAVeform:SOURce
    ## This could have been pulled earlier...
    del Pre

    DataTime = ((np.linspace(0,NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE-1,NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE)-X_REFerence)*X_INCrement)+X_ORIGin
    if ACQ_TYPE == "PEAK": # This means Peak Detect Acq. Type
        DataTime = np.repeat(DataTime,2)

    WFORM = str(KsInfiniiVisionX.query(":WAVeform:FORMat?"))
    if WFORM == "BYTE":
        FORMAT_MULTIPLIER = 1
    else: #WFORM == "WORD"
        FORMAT_MULTIPLIER = 2

    if ACQ_TYPE == "PEAK":
        POINTS_MULTIPLIER = 2 # Recall that Peak Acq. Type basically doubles the number of points.
    else:
        POINTS_MULTIPLIER = 1

    TOTAL_BYTES_TO_XFER = POINTS_MULTIPLIER * NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE * FORMAT_MULTIPLIER + 11

    ## Set chunk size:
    if TOTAL_BYTES_TO_XFER >= 400000:
        KsInfiniiVisionX.chunk_size = TOTAL_BYTES_TO_XFER
    if CHAN1_STATE == 1:
        Data_Ch1 = np.array(KsInfiniiVisionX.query_binary_values(':WAVeform:SOURce CHANnel1;DATA?', "h", False))
        Data_Ch1 = ((Data_Ch1-Y_REFerence_Ch1)*Y_INCrement_Ch1)+Y_ORIGin_Ch1

    ## Reset the chunk size back to default if needed.
    if TOTAL_BYTES_TO_XFER >= 400000:
        KsInfiniiVisionX.chunk_size = 20480
    KsInfiniiVisionX.clear()
    KsInfiniiVisionX.close()

    if CHAN1_STATE == 1:
        ########################################################
        ## As a NUMPY BINARY file - fast and small, but really only good for python - can't use header
        ########################################################
        now = time.clock() # Only to show how long it takes to save
        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = f'dso_{timestr}.csv'
        with open(filename, 'wb') as filehandle: # wb means open for writing in binary; can overwrite
            np.save(filehandle, np.vstack((DataTime,Data_Ch1)).T) # See comment above regarding np.vstack and .T
        del now
    
if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    #В параметрах функции необходимо задать значения, для изменения параметров по умолчанию
    #Если все команды выполнятся успешно, произведется запись файла
    dso(rm)
    