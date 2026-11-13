#!/usr/bin/env python3
"""扫描 Amazing Hand 舵机总线，检查 8 个 SCS0009 舵机是否在线。"""
import sys
import math
import time
from rustypot import Scs0009PyController

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUD = int(sys.argv[2]) if len(sys.argv) > 2 else 1000000

c = Scs0009PyController(serial_port=PORT, baudrate=BAUD, timeout=0.3)

print(f"端口={PORT} 波特率={BAUD}")
print(f"{'ID':>4} {'在线':>6} {'位置(deg)':>10} {'电压(V)':>8} {'温度(C)':>8} {'扭矩':>6}")
found = []
for sid in range(1, 9):
    try:
        pos = c.read_present_position(sid)[0]
        volt = c.read_present_voltage(sid)[0]
        temp = c.read_present_temperature(sid)[0]
        tq = c.read_torque_enable(sid)[0]
        found.append(sid)
        print(f"{sid:>4} {'YES':>6} {math.degrees(pos):>10.2f} {volt:>8.1f} {temp:>8d} {tq:>6d}")
    except Exception as e:
        print(f"{sid:>4} {'--':>6}  {type(e).__name__}: {str(e)[:60]}")

print(f"\n在线舵机: {found}  共 {len(found)}/8")
c.close()
