#
# Codigo RC 1.0 - 03/06/2018
# Lago Terra Alta, 3a visita em 04/06/2018
# Wifi desabilitado no boot
# Sem RTC externo
# Sem Expansion Board (sem gravar no cartão de memoria)
# Deepsleep de 10 minutos
#

flagDebug = False
flagRun = True
if flagDebug or flagRun:
    from machine import Timer
    chrono = Timer.Chrono()
    chrono.start()

# Builtin modules
from network import LoRa
import socket
import binascii
import struct
import time
from machine import Pin, I2C, ADC, deepsleep
import machine
from onewire import DS18X20, OneWire
import pycom
import os

pycom.heartbeat(False)

# Additional modules
import bme280
import max44009
import cayenneLPP
import config
import myfuncs


if flagDebug:
    lap1 = chrono.read_ms()
    print("Tempo de importacao dos modulos: {} ms".format(lap1))


#
# Inicialização de LoRaWan com ABP
#

lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

# create an ABP authentication params
dev_addr = struct.unpack(">l", binascii.unhexlify('260XXXX6'))[0]
nwk_swkey = binascii.unhexlify('50BDE0FD219E1XXXXXXXXXXXXXXXXXXX')
app_swkey = binascii.unhexlify('F9E4XXXXXXXXXXXXXXXXX3CBD3B830ED')

# remove all the channels
for channel in range(0, 72):
    lora.remove_channel(channel)

for channel in range(0, 72):
    lora.add_channel(channel, frequency=config.LORA_FREQUENCY, dr_min=0, dr_max=3)

# join a network using ABP (Activation By Personalization)
lora.join(activation=LoRa.ABP, auth=(dev_addr, nwk_swkey, app_swkey))

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, config.LORA_NODE_DR)

# make the socket blocking
s.setblocking(False)

if flagDebug:
    lap2 = chrono.read_ms()
    print("Tempo apos inicializaco LoRA: {} ms".format(lap2))


#
# Inicialização e leitura dos sensores
#
if flagRun:
    lap1 = chrono.read_ms()

i2c = I2C(0, I2C.MASTER, pins=('G10', 'G9'),baudrate=400000)
connectedI2C = i2c.scan()
if flagDebug:
    print("Connected I2C devices: " + str(connectedI2C))

ow = OneWire(Pin('G8'))
temp = DS18X20(ow)
connectedOW = ow.scan()
if flagDebug:
    print("Connected 1-Wire devices: " + str(connectedOW))

ilum = []   # Lista com as luminosidades lidas com o MAX44009
bmet = []   # Lista com as temperaturas lidas com o BME280
bmeh = []   # Lista com as umiadades lidas com o BME280
bmep = []   # Lista com as pressoes lidas com o BME280
owTemp = []   # Lista com as temperaturas lidas com o OneWire

light_s = False   # Flag para indicar se o MAX44009 esta conectado
bme_s = False   # Flag para indicar se o BME280 esta conectado
ow_s = False   # Flag para indicar se possui algum sensor 1-Wire conectado
if len(connectedOW) > 0:
    ow_s = True

connected_i2c = False   # Flag para indicar se possui algum sensor I2C conectado
if len(connectedI2C) > 0:
    connected_i2c = True

if connected_i2c:
    for device in connectedI2C:
        if device == 0x4A:   # MAX44009 - 74
            light_sensor = max44009.MAX44009(i2c)
            light_s = True
        elif device == 0x76:   # BME280 - 118
            bme = bme280.BME280(i2c=i2c, pressure_mode=bme280.OSAMPLE_8, iir=bme280.FILTER_8)
            bme_s = True
        else:
            if flagDebug:
                print("I2C nao reconhecido")   # Dispositivo nao cadastrado

if ow_s:
    count = 0
    for sensors in connectedOW:
        temp.start_conversion(temp.roms[count])
        count += 1

if light_s:
    # Le iluminancia em lux do MAX44009
    data = int(light_sensor.illuminance_lux)
    ilum.append(data)
if bme_s:
    # Le valores BME280 com media para ter maior precisao :
    numreadings = 15
    samples_temperature = [0.0]*numreadings; mean_temperature = 0.0
    samples_pressure = [0.0]*numreadings; mean_pressure = 0.0
    samples_humidity = [0.0]*numreadings; mean_humidity = 0.0
    for i in range (numreadings):
        samples_temperature[i], samples_pressure[i], samples_humidity[i] = bme.values
    mean_temperature = sum(samples_temperature)/len(samples_temperature)
    mean_pressure = sum(samples_pressure)/len(samples_pressure)
    mean_humidity = sum(samples_humidity)/len(samples_humidity)
    t = mean_temperature
    p = mean_pressure/100   # Pa -> hectoPa
    h = mean_humidity
    bmet.append(t)
    bmep.append(p)
    bmeh.append(h)

if ow_s:
    count = 0
    for sensor in connectedOW:
        tempOW = temp.read_temp_async(temp.roms[count])
        # tempOW_c = myfuncs.sensor_calibration(sensor, tempOW)
        # tempOW_clpp = str(tempOW_c)
        # owTemp.append(tempOW_clpp)
        # print("Sensor: " +str(sensor)+"| Temperatura: "+str(tempOW) +"| Temperatura Calibrada: "+str(tempOW_c))
        owTemp.append(tempOW)
        count += 1

if flagDebug:
    lap3 = chrono.read_ms()
    print("Tempo apos sensores: {} ms".format(lap3))

if flagRun:
    lap2 = chrono.read_ms()
    timeSensors=lap2-lap1

#
# Criando pacote Cayenne LPP
#

lpp = cayenneLPP.CayenneLPP(size = 100, sock = s)

if bme_s:
    lpp.add_temperature(bmet[0])
    lpp.add_barometric_pressure(bmep[0])
    lpp.add_relative_humidity(bmeh[0])
if light_s:
    lpp.add_luminosity(ilum[0])

owChannel = 150

if ow_s:
    for tempValue in owTemp:
        val = float(tempValue)
        lpp.add_temperature(value = val, channel = owChannel)
        owChannel += 1

VBAT = myfuncs.get_batt_mV()

lpp.add_generic(lpp_id=2, values = VBAT, channel = 13, data_size = 2, is_signed = False, precision = 1)

if machine.wake_reason()[0] == machine.PWRON_WAKE:
    pycom.nvs_erase_all()   # 1st time power on

payloadcount = pycom.nvs_get('count')
if payloadcount is not None:
    payloadcount += 1
    pycom.nvs_set('count', payloadcount)
else:
    payloadcount = 1
    pycom.nvs_set('count', 1)  # Starts from 1
if flagDebug:
    print("# pacote LoRaWan = {}".format(payloadcount))

lpp.add_luminosity( value = payloadcount, channel = 155) # Numero do Pacote enviado

if flagDebug:
    print("Tamanho do pacote LPP = {} bytes".format(lpp.get_size()))

if flagDebug:
    lap4 = chrono.read_ms()
    print("Tempo antes do LPP send: {} ms".format(lap4))

if flagRun:
    lap3 = chrono.read_ms()
    totalAwake = lap3+210+3

lpp.add_luminosity( value = timeSensors, channel = 158) # Tempo dos sensores (inicializacao + leitura)
lpp.add_luminosity( value = totalAwake, channel = 159) # Tempo total acordado
lpp.send(reset_payload = True)   # Envio do pacote LoRaWan usando Cayenne LPP

if flagDebug:
    lap5 = chrono.read_ms()
    print("Tempo apos LPP send: {} ms".format(lap5))

time.sleep_ms(300)   # pausa para garantir o envio do pacote

#
# Entrando em deepsleep
#

if flagDebug:
    print("Entrando em deepsleep por 600s = 10 minutos...")

machine.deepsleep(600*1000)   # deep sleep por 10 minutos
