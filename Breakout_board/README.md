# Breakout board

**Front**

![front_photo](Breakout_board_1_2/photo_front.jpg)

**Back**

![front_photo](Breakout_board_1_2/photo_back.jpg)



The Breakout board interfaces a Micropython microcontroller with a set of 6 pyControl behaviour ports, 4 BNC connectors, indicator LEDs and pushbuttons.

Each behaviour port is an 8 pin RJ45 connector which provides power (GND, 5V and 12V), two general purpose digital input/output (DIO) lines, and two driver lines which can be used for switching higher power loads such as solenoids or LEDs.   Ports 1 & 2 have an additional driver line POW_C. Ports 3 and 4 have an additional DIO line DIO_C which also supports analog output (DAC). Ports 3 and 4 support I2C and ports 1,3 & 4 support UART serial communication over their DIO lines.

[Documentation](https://pycontrol.readthedocs.io/en/latest/user-guide/hardware/#breakout-boards)

