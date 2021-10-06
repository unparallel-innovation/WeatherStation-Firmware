# The MIT License (MIT)
#
# Copyright (c) 2018 Limor Fried
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_am2320`
====================================================

This is a MicroPython driver for the AM2320 temperature and humidity sensor,
adapted from Adafreuit's implementation en CircuitPython.

* Author(s): Limor Fried, Alexandre Marquet.

Implementation Notes
--------------------

**Hardware:**

* Adafruit `AM2320 Temperature & Humidity Sensor
  <https://www.adafruit.com/product/3721>`_ (Product ID: 3721)

**Software and Dependencies:**

* MicroPython:
    https://github.com/micropython/micropython

"""

# imports
try:
    import struct
except ImportError:
    import ustruct as struct

import time

from micropython import const

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/alexmrqt/Adafruit_CircuitPython_am2320.git"


_AM2320_DEFAULT_ADDR = const(0x5C)
_AM2320_CMD_READREG = const(0x03)
_AM2320_REG_TEMP_H = const(0x02)
_AM2320_REG_HUM_H = const(0x00)


def _crc16(data):
    crc = 0xffff
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


class AM2320:
    """A driver for the AM2320 temperature and humidity sensor.

    :param i2c_bus: The `I2C` object to use. This is the only required parameter.
    :param int address: (optional) The I2C address of the device.

    """
    def __init__(self, i2c_bus, address=_AM2320_DEFAULT_ADDR):
        self._i2c_bus = i2c_bus
        self._addr = address

    def _read_register(self, register, length):
        # wake up sensor
        self._i2c_bus.writeto(self._addr, bytes([0x00]))
        time.sleep(0.01)  # wait 10 ms

        # Send command to read register
        cmd = [_AM2320_CMD_READREG, register & 0xFF, length]
        # print("cmd: %s" % [hex(i) for i in cmd])
        self._i2c_bus.writeto(self._addr, bytes(cmd))
        time.sleep(0.002)  # wait 2 ms for reply
        result = bytearray(length+4) # 2 bytes pre, 2 bytes crc
        self._i2c_bus.readfrom_into(self._addr, result)
        # print("$%02X => %s" % (register, [hex(i) for i in result]))
        # Check preamble indicates correct readings
        if result[0] != 0x3 or result[1] != length:
            raise RuntimeError('I2C modbus read failure')
        # Check CRC on all but last 2 bytes
        crc1 = struct.unpack("<H", bytes(result[-2:]))[0]
        crc2 = _crc16(result[0:-2])
        if crc1 != crc2:
            print("erro crc")
            raise RuntimeError('CRC failure 0x%04X vs 0x%04X' % (crc1, crc2))
        return result[2:-2]

    @property
    def temperature(self):
        """The measured temperature in celsius."""
        temperature = struct.unpack(">H", self._read_register(_AM2320_REG_TEMP_H, 2))[0]
        if temperature >= 32768:
            temperature = 32768 - temperature
        return temperature/10.0

    @property
    def relative_humidity(self):
        """The measured relative humidity in percent."""
        humidity = struct.unpack(">H", self._read_register(_AM2320_REG_HUM_H, 2))[0]
        return humidity/10.0