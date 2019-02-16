/*
Arquivo de Boot do LoPy4 (utilizado como NanoGateway no projeto)

Bibliotecas importadas:
	machine
	os
	pycom
*/

# Importando bibliotecas

from machine import UART
import machine
import os
import pycom

# Código executado no boot do LoPy4

# Desabilita o pisca-pisca do LED embutido na placa
pycom.heartbeat(False)

# Configura a UART
uart = UART(0, baudrate=115200)
os.dupterm(uart)

# Qual arquivo .py executar após o processo de boot do LoPy4
machine.main('main.py')
