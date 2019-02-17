/*
Arquivo de Boot do nó que enviará dados para o NanoGateway
Para informações mais detalhadas desse arquivo, olhar o arquivo boot.py do NanoGateway
*/

from machine import UART
import machine
import os
import pycom

# Como o nó ficará em um local de dificil acesso, não será necessário utilizar o Wi-Fi embutido nele.
# Como enconomia de energia, o Wi-Fi interno já é desabilitado no Boot
pycom.wifi_on_boot(False)

uart = UART(0, baudrate=115200)
os.dupterm(uart)

machine.main('main.py')
