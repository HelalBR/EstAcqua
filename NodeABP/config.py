/*
Arquivo de configuração do nó que enviará dados para o NanoGateway
Para maiores informações sobre esse arquivo, visualizar o arquivo config.py do NanoGateway
*/

import machine
import ubinascii

WIFI_MAC = ubinascii.hexlify(machine.unique_id()).upper()
# Set  the Gateway ID to be the first 3 bytes of MAC address + 'FFFE' + last 3 bytes of MAC address
GATEWAY_ID = WIFI_MAC[:6] + "FFFE" + WIFI_MAC[6:12]

SERVER = 'router.br.thethings.network'
PORT = 1700

NTP = "c.ntp.br"
NTP_PERIOD_S = 3600

WIFI_SSID = 'Nome_DA_REDE'
WIFI_PASS = 'SENHA_DA_REDE'

# for US915
LORA_FREQUENCY = 903900000
LORA_GW_DR = "SF8BW125"
LORA_NODE_DR = 2
