/*
Arquivo de configuração do NanoGateway
Utilizado para se conectar com o IoT Cloud (nesse projeto foi utilizado a The Things Network (TTN).

Bibliotecas importadas:
	machine
	ubinascii
*/

# Lendo o MAC Address da interface Wi-Fi do LoPy no formato hexadecimal, removendo ":" e utilizando letras maiúsculas
# Formato AABBCCDDEEFF
WIFI_MAC = ubinascii.hexlify(machine.unique_id()).upper()

# De forma a tentar minimizar a possibilidade de você ter dois dispositivos na mesma rede com o mesmo MAC Address,
# dividi-se o MAC Address lido em dois e adiciona-se as letras "FFFE" entre elas. Esse será o ID do Gateway a ser
# registrado na TTN
GATEWAY_ID = WIFI_MAC[:6] + "FFFE" + WIFI_MAC[6:12]

# Servidor utilizado da TTN (usando servidor brasileiro)
SERVER = 'router.br.thethings.network'

# Porta utilizada para se conectar ao servidor da TTN
PORT = 1700

# Servidor NTP utilizado para sincronizar a hora do LoPy4
NTP = "c.ntp.br"

# Período, em segundos, em que haverá a sincronização do LoPy4 com o NTP
NTP_PERIOD_S = 3600

# Nome e senha da rede Wi-Fi que o NanoGateway irá se conectar para transmitir os dados recebidos para a TTN
WIFI_SSID = 'NOME_DA_REDE'
WIFI_PASS = 'SENHA_DA_REDE'

# Configuração dos parâmetros LoRa a serem utilizados
# Frequência utilizada (em MHz) - No Brasil é utilizado o padrão US915. A frequência escolhida depende do plano de frequências
# da TTN (https://www.thethingsnetwork.org/docs/lorawan/frequency-plans.html)
LORA_FREQUENCY = 903900000

# Definição do Spreading Factor (SF) e Bandwidht (BW) a ser utilizado. Esses valores devem ser compatíveis com os valores
# indicados em cada plano de frequência na tabela de plano de frequências da TTN. Foi escolhido SF=8 e Bw=125kHz
LORA_GW_DR = "SF8BW125"

/*

 Seleção do DataRate (DR). É um valor tabelado e pode ser obtido abaixo de acordo com o plano de frequência utilizado

 *    LoRaWAN EU or IN or ASIA-PAC / LATAM:
 *    
 *    0: SF = 12, BW = 125 kHz, BitRate =  250 bps
 *    1: SF = 11, BW = 125 kHz, BitRate =  440 bps
 *    2: SF = 10, BW = 125 kHz, BitRate =  980 bps
 *    3: SF =  9, BW = 125 kHz, BitRate = 1760 bps
 *    4: SF =  8, BW = 125 kHz, BitRate = 3125 bps
 *    5: SF =  7, BW = 125 kHz, BitRate = 5470 bps
 *  
 *    LoRaWAN US or AU:
 *    
 *    0: SF = 10, BW = 125 kHz, BitRate =   980 bps
 *    1: SF =  9, BW = 125 kHz, BitRate =  1760 bps
 *    2: SF =  8, BW = 125 kHz, BitRate =  3125 bps
 *    3: SF =  7, BW = 125 kHz, BitRate =  5470 bps
*/
LORA_NODE_DR = 2
