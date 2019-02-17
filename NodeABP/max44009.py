/*
Driver do sensor de iluminância MAX 44009
Retorna a iluminância lida em lux
*/

"""
Low memory version of MicroPython driver for Maxim Integrated MAX44009 ambient light I2C sensor :
https://github.com/rcolistete/MicroPython_MAX44009
"""

from micropython import const


_MAX44009_REG_CONFIGURATION = const(0x02)
_MAX44009_REG_LUX_HIGH_BYTE = const(0x03)
 

class MAX44009:
    
    def __init__(self, i2c, address=0x4A):
        self.i2c = i2c
        self.address = address
        self.configuration = 0x00   # Default continous mode, automatic mode

    @property
    def configuration(self):
        return self._config

    @configuration.setter
    def configuration(self, value):
        self._config = value
        self.i2c.writeto_mem(self.address, _MAX44009_REG_CONFIGURATION, self._config)

    @property
    def illuminance_lux(self):
        data = self.i2c.readfrom_mem(self.address, _MAX44009_REG_LUX_HIGH_BYTE, 2)
        exponent = (data[0] & 0xF0) >> 4
        mantissa = ((data[0] & 0x0F) << 4) | (data[1] & 0x0F)
        illuminance = (2**exponent)*mantissa*0.045
        return illuminance   # float in lux
