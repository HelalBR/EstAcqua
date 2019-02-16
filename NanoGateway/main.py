/*
	Arquivo principal do NanoGateway. É o arquivo carregado após o processo de boot do LoPy4 ter sido concluído
	
	Bibliotecas importadas:
		config (Arquivo criado com as configurações a serem utilizadas - config.py)
		nanogateway
*/

# Importando bibliotecas
import config
from nanogateway import NanoGateway

# Criando uma instância do NanoGateway e configurando com os parâmetros definidos no config.py
if __name__ == '__main__':
    nanogw = NanoGateway(
        id=config.GATEWAY_ID, # ID do Gateway que será autenticado na TTN
        frequency=config.LORA_FREQUENCY, # Frequência a ser utilizada na transmissão LoRa
        datarate=config.LORA_GW_DR, # Datarate utilizado
        ssid=config.WIFI_SSID, # SSID da rede Wi-Fi que o LoPy4 se conectará para transmistir para a internet
        password=config.WIFI_PASS, # Senha da rede Wi-Fi
        server=config.SERVER, # Servidor utilizado da TTN
        port=config.PORT, # Porta de acesso ao servidor da TTN
        ntp_server=config.NTP, # Servidor NTP utilizado
        ntp_period=config.NTP_PERIOD_S # Período, em segundos, entre as sincronizações com o NTP
        )
	
	# inicialização da instância do NanoGateway
    	nanogw.start()
	
	# Se estiver conectado via terminal ao LoPy4, pressione Enter para utilizar o REPL
    	nanogw._log('Pressione Enter para utilizar o REPL')
    	input()
