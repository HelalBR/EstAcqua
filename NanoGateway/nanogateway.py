/*
Modulo principal do NanoGateway

Biblitoecas importadas:
	errno
	machine
	ubinascii
	ujson
	uos
	usocket
	utime
	_thread
	micropython
	network
	pycom
	os
*/


# Importando Bibliotecas
import errno
import machine
import ubinascii
import ujson
import uos
import usocket
import utime
import _thread
from micropython import const
from network import LoRa
from network import WLAN
from machine import Timer
import pycom
from machine import SD
import os

# Caso haja um cartão SD inserido na placa de expansão, será efetuada uma tentativa de montar o cartão
# Se conseguir montar o cartão, a flaguSDcard será setada como true para que o LoPy4 saiba que pode
# efetuar gravações dos dados recebidos no cartão uSD
# Caso não consegui montar, o led embutido na placa ficará vermelho para que o operador saiba
# que houve um erro durante a montagem do cartão uSD.
try:
    sd = SD()
    os.mount(sd, '/sd')
    print("Cartão uSD montado. Espaço livre: {:.3f} GB".format(os.getfree('/sd')/(1024*1024)))
    flaguSDcard = True
except OSError as e:
    pycom.rgbled(0xFF0000)
    print("Ocorreu um erro durante a montagem do cartão SD. {}".format(e))
    flaguSDcard = False

# Verifica se já existe um arquivo contendo os logs recebidos anteriormente. Se já existir, a flag exists é setada
# como true e o LoPy4 sabe que não precisa criar um arquivo novo. Caso não existe, a flag é setada como false e o
# arquivo de log é criado quando for salvar o primeiro dado recebido.
try:
    f = open('/sd/recv.txt', "r")
    exists = True
    f.close()
except OSError as e:
    exists = False


# Informações gerais sobre erros e formato JSON do satus do pacote recebido, dados do pacote recebido e envio de ACK
PROTOCOL_VERSION = const(2)

PUSH_DATA = const(0)
PUSH_ACK = const(1)
PULL_DATA = const(2)
PULL_ACK = const(4)
PULL_RESP = const(3)

TX_ERR_NONE = 'NONE'
TX_ERR_TOO_LATE = 'TOO_LATE'
TX_ERR_TOO_EARLY = 'TOO_EARLY'
TX_ERR_COLLISION_PACKET = 'COLLISION_PACKET'
TX_ERR_COLLISION_BEACON = 'COLLISION_BEACON'
TX_ERR_TX_FREQ = 'TX_FREQ'
TX_ERR_TX_POWER = 'TX_POWER'
TX_ERR_GPS_UNLOCKED = 'GPS_UNLOCKED'

UDP_THREAD_CYCLE_MS = const(10)

STAT_PK = {
    'stat': {
        'time': '',
        'lati': 0,
        'long': 0,
        'alti': 0,
        'rxnb': 0,
        'rxok': 0,
        'rxfw': 0,
        'ackr': 100.0,
        'dwnb': 0,
        'txnb': 0
    }
}

RX_PK = {
    'rxpk': [{
        'time': '',
        'tmst': 0,
        'chan': 0,
        'rfch': 0,
        'freq': 0,
        'stat': 1,
        'modu': 'LORA',
        'datr': '',
        'codr': '4/5',
        'rssi': 0,
        'lsnr': 0,
        'size': 0,
        'data': ''
    }]
}

TX_ACK_PK = {
    'txpk_ack': {
        'error': ''
    }
}


class NanoGateway:
    
		/*
		Inicialização da classe do NanoGayeway, configurada para ser utilizada com a TTN.
		Os parâmetros estão definidos no arquivo config.py
		Eventualmente a Pycom faz atualizações nesse arquivo. Sempre recorrer ao repositório oficial da Pycom
		https://github.com/pycom/
		*/
    def __init__(self, id, frequency, datarate, ssid, password, server, port, ntp_server, ntp_period):
        self.id = id
        self.server = server
        self.port = port

        self.frequency = frequency
        self.datarate = datarate

        self.ssid = ssid
        self.password = password

        self.ntp_server = ntp_server
        self.ntp_period = ntp_period

        self.server_ip = None

        self.rxnb = 0
        self.rxok = 0
        self.rxfw = 0
        self.dwnb = 0
        self.txnb = 0

        self.sf = self._dr_to_sf(self.datarate)
        self.bw = self._dr_to_bw(self.datarate)

        self.stat_alarm = None
        self.pull_alarm = None
        self.uplink_alarm = None

        self.wlan = None
        self.sock = None
        self.udp_stop = False
        self.udp_lock = _thread.allocate_lock()

        self.lora = None
        self.lora_sock = None

        self.rtc = machine.RTC()

    def start(self):
				# Inicia o NanoGayeway LoRaWAN
        self._log('Iniciando NanoGateway LoRaWAN com id: {}', self.id)

        # Configura o Wi-Fi do LoPy4 para funcionar como uma estação e se conecta na rede Wi-Fi
        self.wlan = WLAN(mode=WLAN.STA)
        self._connect_to_wifi()

        # Sincroniza a hora com o servidor NTP
        self._log('Sincronizando a hora com {} ...', self.ntp_server)
        self.rtc.ntp_sync(self.ntp_server, update_period=self.ntp_period)
        while not self.rtc.synced():
            utime.sleep_ms(50)
        self._log("Sincronização completa")

        # Pega o IP do servidor utilizado como IoT Cloud e cria um socket UDP
        self.server_ip = usocket.getaddrinfo(self.server, self.port)[0][-1]
        self._log('Abrindo socket UDP para {} ({}) port {}...', self.server, self.server_ip[0], self.server_ip[1])
        self.sock = usocket.socket(usocket.AF_INET, usocket.SOCK_DGRAM, usocket.IPPROTO_UDP)
        self.sock.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)

        # Imediatamente após a criação do socket é criado e enviado um pacote com o status
        self._push_data(self._make_stat_packet())

        # Cria alarmes
        self.stat_alarm = Timer.Alarm(handler=lambda t: self._push_data(self._make_stat_packet()), s=60, periodic=True)
        self.pull_alarm = Timer.Alarm(handler=lambda u: self._pull_data(), s=25, periodic=True)

        # Inicia uma thread para receber pacotes UDP
        self.udp_stop = False
        _thread.start_new_thread(self._udp_thread, ())

	# Inicia o radio LoRa utilizando o modo LORA
        self._log('Iniciando LoRa com {} Mhz e datarate {}', self._freq_to_float(self.frequency), self.datarate)
        self.lora = LoRa(
            mode=LoRa.LORA,
            frequency=self.frequency,
            bandwidth=self.bw,
            sf=self.sf,
            preamble=8,
            coding_rate=LoRa.CODING_4_5,
            tx_iq=True
        )

        # Cria um socket cru do LoRa
        self.lora_sock = usocket.socket(usocket.AF_LORA, usocket.SOCK_RAW)
        self.lora_sock.setblocking(False)
        self.lora_tx_done = False

        self.lora.callback(trigger=(LoRa.RX_PACKET_EVENT | LoRa.TX_PACKET_EVENT), handler=self._lora_cb)
        self._log('NanoGateway LoRaWAN se encontra online')

    def stop(self):
       
				# Função para parar o NanoGayeway
        self._log('Stopping...')
        self._log('Stopping...')

        # Envia o radio LoRa para o modo SLEEP
        self.lora.callback(trigger=None, handler=None)
        self.lora.power_mode(LoRa.SLEEP)

        # Para a sincronizacao com o servidor NTP
        self.rtc.ntp_sync(None)

        # Cancela todos os alarmes criados
        self.stat_alarm.cancel()
        self.pull_alarm.cancel()

        # Envia um sinal para parar a thread UDP
        self.udp_stop = True
        while self.udp_stop:
            utime.sleep_ms(50)

        # Se desconecta da rede Wi-Fi e desabilita o Wi-Fi do LoPy4
        self.wlan.disconnect()
        self.wlan.deinit()

		# Funcao para se conectar na rede Wi-Fi. Apos se conectar o led embutido no LoPy4 fica na cor verde
		# Funcao configurada para utilizar uma antena Wi-Fi externa acoplada ao LoPy4. Caso queira utilizar
		# a antena interna do LoPy, substituir o parametro WLAN.EXT_ANT para WLAN.INT_ANT
    def _connect_to_wifi(self):
        self.wlan.init(antenna=WLAN.EXT_ANT)
        self.wlan.connect(self.ssid, auth=(None, self.password))
        while not self.wlan.isconnected():
            utime.sleep_ms(50)
        self._log('WiFi conectado em: {}', self.ssid)
        pycom.rgbled(0x00ff00)

    # Funcao que recebe o datarate e retorna qual o Spreading Factor
		# Data rate definido da seguinte maneira: SFXBWZYV
		def _dr_to_sf(self, dr):
        sf = dr[2:4]
        if sf[1] not in '0123456789':
            sf = sf[:1]
        return int(sf)
		
		# Função que recebe o datarate e retorna qual o Bandwidth
		# Data rate definido da seguinte maneira: SFXBWZYV
    def _dr_to_bw(self, dr):
        bw = dr[-5:]
        if bw == 'BW125':
            return LoRa.BW_125KHZ
        elif bw == 'BW250':
            return LoRa.BW_250KHZ
        else:
            return LoRa.BW_500KHZ
		
		# Funcao que recebe o SF e o BW e retorna o datarate
		# Data rate definido da seguinte maneira: SFXBWZYV
    def _sf_bw_to_dr(self, sf, bw):
        dr = 'SF' + str(sf)
        if bw == LoRa.BW_125KHZ:
            return dr + 'BW125'
        elif bw == LoRa.BW_250KHZ:
            return dr + 'BW250'
        else:
            return dr + 'BW500'

		# Manipulador de retorno de chamada de eventos de rádio LoRa
		# Funcao responsavel por receber os pacotes transmitidos ao NanoGateway
    def _lora_cb(self, lora):
      
        events = lora.events()
        if events & LoRa.RX_PACKET_EVENT:
            self.rxnb += 1
            self.rxok += 1
            rx_data = self.lora_sock.recv(256)
            stats = lora.stats()
            packet = self._make_node_packet(rx_data, self.rtc.now(), stats.rx_timestamp, stats.sfrx, self.bw, stats.rssi, stats.snr)
            # pacote recebido! pisca o led em azul para mostrar que o NanoGateway recebeu o dado
            # mesmo que nao esteja conectado na TTN ele ira salvar o dado no cartao de memoria
            # e esse dado depois pode ser recuperado depois
            pycom.rgbled(0x0000ff)
            utime.sleep_ms(100)
            pycom.rgbled(0x00ff00)
            # se o cartao estiver montado ele grava o pacote recebido
            if flaguSDcard:
                logfile = open('/sd/recv.txt', 'a')
                logfile.write('{}\n'.format(packet))
                logfile.close()
                os.sync()
            self._push_data(packet)
            self._log('Received packet: {}', packet)
            self.rxfw += 1
        if events & LoRa.TX_PACKET_EVENT:
            self.txnb += 1
            lora.init(
                mode=LoRa.LORA,
                frequency=self.frequency,
                bandwidth=self.bw,
                sf=self.sf,
                preamble=8,
                coding_rate=LoRa.CODING_4_5,
                tx_iq=True
                )
						
		# Funcao para tratar um problema de imprecisao do micropython em divisoes com float.
    def _freq_to_float(self, frequency):
       
        divider = 6
        while divider > 0 and frequency % 10 == 0:
            frequency = frequency // 10
            divider -= 1
        if divider > 0:
            frequency = frequency / (10 ** divider)
        return frequency

    def _make_stat_packet(self):
        now = self.rtc.now()
        STAT_PK["stat"]["time"] = "%d-%02d-%02d %02d:%02d:%02d GMT" % (now[0], now[1], now[2], now[3], now[4], now[5])
        STAT_PK["stat"]["rxnb"] = self.rxnb
        STAT_PK["stat"]["rxok"] = self.rxok
        STAT_PK["stat"]["rxfw"] = self.rxfw
        STAT_PK["stat"]["dwnb"] = self.dwnb
        STAT_PK["stat"]["txnb"] = self.txnb
        return ujson.dumps(STAT_PK)

    def _make_node_packet(self, rx_data, rx_time, tmst, sf, bw, rssi, snr):
        RX_PK["rxpk"][0]["time"] = "%d-%02d-%02dT%02d:%02d:%02d.%dZ" % (rx_time[0], rx_time[1], rx_time[2], rx_time[3], rx_time[4], rx_time[5], rx_time[6])
        RX_PK["rxpk"][0]["tmst"] = tmst
        RX_PK["rxpk"][0]["freq"] = self._freq_to_float(self.frequency)
        RX_PK["rxpk"][0]["datr"] = self._sf_bw_to_dr(sf, bw)
        RX_PK["rxpk"][0]["rssi"] = rssi
        RX_PK["rxpk"][0]["lsnr"] = snr
        RX_PK["rxpk"][0]["data"] = ubinascii.b2a_base64(rx_data)[:-1]
        RX_PK["rxpk"][0]["size"] = len(rx_data)
        return ujson.dumps(RX_PK)

    def _push_data(self, data):
        token = uos.urandom(2)
        packet = bytes([PROTOCOL_VERSION]) + token + bytes([PUSH_DATA]) + ubinascii.unhexlify(self.id) + data
        with self.udp_lock:
            try:
                self.sock.sendto(packet, self.server_ip)
            except Exception as ex:
                self._log('Failed to push uplink packet to server: {}', ex)

    def _pull_data(self):
        token = uos.urandom(2)
        packet = bytes([PROTOCOL_VERSION]) + token + bytes([PULL_DATA]) + ubinascii.unhexlify(self.id)
        with self.udp_lock:
            try:
                self.sock.sendto(packet, self.server_ip)
            except Exception as ex:
                self._log('Failed to pull downlink packets from server: {}', ex)

    def _ack_pull_rsp(self, token, error):
        TX_ACK_PK["txpk_ack"]["error"] = error
        resp = ujson.dumps(TX_ACK_PK)
        packet = bytes([PROTOCOL_VERSION]) + token + bytes([PULL_ACK]) + ubinascii.unhexlify(self.id) + resp
        with self.udp_lock:
            try:
                self.sock.sendto(packet, self.server_ip)
            except Exception as ex:
                self._log('PULL RSP ACK exception: {}', ex)
								
		# Funcao para agendar e transmitir um pacote downlink do servidor para o NanoGateway
    def _send_down_link(self, data, tmst, datarate, frequency):
    
        self.lora.init(
            mode=LoRa.LORA,
            frequency=frequency,
            bandwidth=self._dr_to_bw(datarate),
            sf=self._dr_to_sf(datarate),
            preamble=8,
            coding_rate=LoRa.CODING_4_5,
            tx_iq=True
            )
        while utime.ticks_cpu() < tmst:
            pass
        self.lora_sock.send(data)
        self._log(
            'Sent downlink packet scheduled on {:.3f}, at {:.3f} Mhz using {}: {}',
            tmst / 1000000,
            self._freq_to_float(frequency),
            datarate,
            data
        )
				
		# Thread UDP para ler e tratar os dados recebidos do servidor IoT
    def _udp_thread(self):
   
        while not self.udp_stop:
            try:
                data, src = self.sock.recvfrom(1024)
                _token = data[1:3]
                _type = data[3]
                if _type == PUSH_ACK:
                    self._log("Push ack")
                elif _type == PULL_ACK:
                    self._log("Pull ack")
                elif _type == PULL_RESP:
                    self.dwnb += 1
                    ack_error = TX_ERR_NONE
                    tx_pk = ujson.loads(data[4:])
                    tmst = tx_pk["txpk"]["tmst"]
                    t_us = tmst - utime.ticks_cpu() - 15000
                    if t_us < 0:
                        t_us += 0xFFFFFFFF
                    if t_us < 20000000:
                        self.uplink_alarm = Timer.Alarm(
                            handler=lambda x: self._send_down_link(
                                ubinascii.a2b_base64(tx_pk["txpk"]["data"]),
                                tx_pk["txpk"]["tmst"] - 50, tx_pk["txpk"]["datr"],
                                int(tx_pk["txpk"]["freq"] * 1000) * 1000
                            ),
                            us=t_us
                        )
                    else:
                        ack_error = TX_ERR_TOO_LATE
                        self._log('Downlink timestamp error!, t_us: {}', t_us)
                    self._ack_pull_rsp(_token, ack_error)
                    self._log("Pull rsp")
            except usocket.timeout:
                pass
            except OSError as ex:
                if ex.errno != errno.EAGAIN:
                    self._log('UDP recv OSError Exception: {}', ex)
            except Exception as ex:
                self._log('UDP recv Exception: {}', ex)

            utime.sleep_ms(UDP_THREAD_CYCLE_MS)

        # Fecha o socket e para a thread UDP
        self.sock.close()
        self.udp_stop = False
        self._log('Thread UDP parada')

		# Funcao de log no terminal
		# Printa o tempo em ms, a mensagem recebido e os parametros da mensagem
		# Utilizado pelo NanoGateway para gerar o log dos eventos ocorridos
    def _log(self, message, *args):
        print('[{:>10.3f}] {}'.format(
            utime.ticks_ms() / 1000,
            str(message).format(*args)
            ))
