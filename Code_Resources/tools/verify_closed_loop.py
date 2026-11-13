#!/usr/bin/env python3
"""闭环验证：下发 open_hand 姿态 -> 回读位置 -> 比对误差。

用法:
    python verify_closed_loop.py                      # 默认 /dev/ttyUSB0
    python verify_closed_loop.py /dev/ttyUSB0
    python verify_closed_loop.py COM21                # Windows
"""
import math
import sys
import time

from rustypot import Scs0009PyController

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUD = 1_000_000
MIDDLE = [3, 0, -5, -8, -2, 5, -12, 0]
TARGET_DELTA = {"index": (-35, 35), "middle": (-35, 35), "ring": (-35, 35), "thumb": (-35, 35)}
FINGERS = {"index": (1, 2), "middle": (3, 4), "ring": (5, 6), "thumb": (7, 8)}

c = Scs0009PyController(serial_port=PORT, baudrate=BAUD, timeout=0.5)
for sid in range(1, 9):
    c.write_torque_enable(sid, 1)

tgt = {}
for f, (a1, a2) in TARGET_DELTA.items():
    id1, id2 = FINGERS[f]
    tgt[id1] = MIDDLE[id1 - 1] + a1
    tgt[id2] = MIDDLE[id2 - 1] + a2
    c.write_goal_speed(id1, 7)
    c.write_goal_speed(id2, 7)
    c.write_goal_position(id1, math.radians(tgt[id1]))
    c.write_goal_position(id2, math.radians(tgt[id2]))

time.sleep(1.5)
print(f"{'ID':>3} {'目标':>9} {'回读':>9} {'误差':>8}")
ok = True
for sid in range(1, 9):
    pos = math.degrees(c.read_present_position(sid)[0])
    err = abs(pos - tgt[sid])
    ok &= err < 5.0
    print(f"{sid:>3} {tgt[sid]:>9.2f} {pos:>9.2f} {err:>8.2f}")
print("\n结论:", "闭环正常，舵机已跟随目标位" if ok else "存在超差舵机，检查机械/供电")
c.close()
