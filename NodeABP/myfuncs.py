/*
Funcao criada para ler a voltagem no divisor de tensao (na placa desenvolvida para o projeto - visualizar pasta Projeto)
Retorna a voltagem da bateria
*/

from machine import ADC


# myADC
# ADC 12 bits
# Conversao para mV
# Retorna o valor da tensao da bateria em mV
# Divisor de tensao: R1=680k, R2=100k
# ADC Pino 16, (input only; max voltage 1.1V)
def get_batt_mV():
    numADCreadings = const(100)

    adc = ADC(0)
    adcread = adc.channel(pin='P16')
    samplesADC = [0.0]*numADCreadings; meanADC = 0.0
    i = 0
    while (i < numADCreadings):
        adcint = adcread()
        samplesADC[i] = adcint
        meanADC += adcint
        i += 1
    meanADC /= numADCreadings

    mV = ((meanADC*1100/4096)*(680+100)/100)
    mV_int = int(mV)
    return mV_int
