#!/usr/bin/env python3
"""AmazingHand 基础手势 Demo（PythonExample/AmazingHand_Demo.py 的可用化版本）。

相对原版的改动：
  * 串口不写死 COM11，可 --port 指定或自动扫描
  * 支持 --side right/left
  * 支持 --dry-run：不连硬件，只打印每帧目标角度，用于验证逻辑
  * 启动前做一次舵机扫描，缺失的 ID 会提示

用法（Windows，需在 conda 环境 yolov10 下）:
    python hand_demo.py                      # 自动找端口，跑一遍全部手势
    python hand_demo.py --dry-run            # 不连硬件，只打印目标角度
    python hand_demo.py --port COM21 --side right
    python hand_demo.py --loops 0            # 无限循环
"""

import argparse
import glob
import os
import sys
import time

import numpy as np

try:
    from rustypot import Scs0009PyController
except ImportError:  # pragma: no cover
    Scs0009PyController = None

BAUD = 1_000_000
MAX_SPEED = 7          # SCS0009 速度 1~7，7 最快
CLOSE_SPEED = 3
SCAN_IDS = list(range(1, 9))

# 每个手指 2 个舵机：(id_1, id_2)，MiddlePos 中对应 (索引, 索引+1)
FINGERS = {
    "index": (1, 2),
    "middle": (3, 4),
    "ring": (5, 6),
    "thumb": (7, 8),
}

# 标定得到的中间位（度）。换成你自己的标定结果。
DEFAULT_MIDDLE_POS = [3, 0, -5, -8, -2, 5, -12, 0]

PORT_PATTERNS = [
    "/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyCH343USB*", "/dev/ttyCH341USB*",
    "/dev/ttyHS*", "/dev/ttyAMA*", "/dev/ttyS[0-3]",
]


def candidate_ports():
    """列出候选串口。Windows 下用 pyserial 枚举真实存在的 COM 口。"""
    if os.name == "nt":
        try:
            from serial.tools import list_ports
            return [p.device for p in list_ports.comports()]
        except Exception:
            return [f"COM{i}" for i in range(1, 21)]
    ports = []
    for pat in PORT_PATTERNS:
        ports.extend(glob.glob(pat))
    return [p for p in dict.fromkeys(ports) if os.path.exists(p)]


def autodetect_port():
    """扫描所有候选串口，返回第一个能应答舵机的端口。"""
    if Scs0009PyController is None:
        return None
    for port in candidate_ports():
        try:
            ctrl = Scs0009PyController(serial_port=port, baudrate=BAUD, timeout=0.15)
        except Exception:
            continue
        try:
            if ctrl.scan(SCAN_IDS):
                return port
        except Exception:
            pass
        finally:
            try:
                ctrl.close()
            except Exception:
                pass
    return None


class Hand:
    def __init__(self, ctrl, side="right", middle_pos=None, dry_run=False, verbose=True):
        self.ctrl = ctrl
        self.side = side
        self.middle_pos = list(middle_pos or DEFAULT_MIDDLE_POS)
        self.dry_run = dry_run or ctrl is None
        self.verbose = verbose
        self.t0 = time.time()
        self.frames = 0

    # ---------- 底层 ----------
    def move(self, finger, a1, a2, speed=MAX_SPEED):
        """让某根手指的两个舵机相对中间位偏移 a1/a2 度。"""
        id1, id2 = FINGERS[finger]
        i1, i2 = (id1 - 1), (id2 - 1)
        deg1 = self.middle_pos[i1] + a1
        deg2 = self.middle_pos[i2] + a2

        if self.dry_run:
            self.frames += 1
            if self.verbose:
                print(
                    f"[{time.time() - self.t0:6.2f}s] {finger:<6} "
                    f"ID{id1}={deg1:+7.2f}°  ID{id2}={deg2:+7.2f}°  speed={speed}",
                    flush=True,
                )
            return

        self.ctrl.write_goal_speed(id1, speed)
        time.sleep(0.0002)
        self.ctrl.write_goal_speed(id2, speed)
        time.sleep(0.0002)
        self.ctrl.write_goal_position(id1, float(np.deg2rad(deg1)))
        self.ctrl.write_goal_position(id2, float(np.deg2rad(deg2)))
        time.sleep(0.005)

    def move_all(self, poses, speed=MAX_SPEED):
        for finger, (a1, a2) in poses.items():
            self.move(finger, a1, a2, speed)

    # ---------- 手势 ----------
    def open_hand(self):
        self.move_all({f: (-35, 35) for f in FINGERS})

    def close_hand(self):
        # 与原始 demo 一致：拇指比其余手指快一档
        for f in ("index", "middle", "ring"):
            self.move(f, 90, -90, CLOSE_SPEED)
        self.move("thumb", 90, -90, CLOSE_SPEED + 1)

    def open_hand_progressive(self):
        for f in ("index", "middle", "ring", "thumb"):
            self.move(f, -35, 35, MAX_SPEED - 2)
            time.sleep(0.2)

    def spread_hand(self):
        if self.side == "right":
            self.move_all({
                "index": (4, 90), "middle": (-32, 32),
                "ring": (-90, -4), "thumb": (-90, -4),
            })
        else:
            self.move_all({
                "index": (-60, 0), "middle": (-35, 35),
                "ring": (-4, 90), "thumb": (-4, 90),
            })

    def clench_hand(self):
        if self.side == "right":
            self.move_all({
                "index": (-60, 0), "middle": (-35, 35),
                "ring": (0, 70), "thumb": (-4, 90),
            })
        else:
            self.move_all({
                "index": (0, 60), "middle": (-35, 35),
                "ring": (-70, 0), "thumb": (-90, -4),
            })

    def index_pointing(self):
        self.move_all({
            "index": (-40, 40), "middle": (90, -90),
            "ring": (90, -90), "thumb": (90, -90),
        })

    def nonono(self):
        self.index_pointing()
        for _ in range(3):
            time.sleep(0.2)
            self.move("index", -10, 80)
            time.sleep(0.2)
            self.move("index", -80, 10)
        self.move("index", -35, 35)
        time.sleep(0.4)

    def perfect(self):
        thumb = (65, 12) if self.side == "right" else (-12, -65)
        self.move_all({
            "index": (50, -50), "middle": (0, 0),
            "ring": (-20, 20), "thumb": thumb,
        })

    def victory(self):
        if self.side == "right":
            self.move_all({
                "index": (-15, 65), "middle": (-65, 15),
                "ring": (90, -90), "thumb": (90, -90),
            })
        else:
            self.move_all({
                "index": (-65, 15), "middle": (-15, 65),
                "ring": (90, -90), "thumb": (90, -90),
            })

    def scissors(self):
        self.victory()
        if self.side == "right":
            for _ in range(3):
                time.sleep(0.2)
                self.move("index", -50, 20)
                self.move("middle", -20, 50)
                time.sleep(0.2)
                self.move("index", -15, 65)
                self.move("middle", -65, 15)
        else:
            for _ in range(3):
                time.sleep(0.2)
                self.move("index", -20, 50)
                self.move("middle", -50, 20)
                time.sleep(0.2)
                self.move("index", -65, 15)
                self.move("middle", -15, 65)

    def pinched(self):
        thumb = (0, -75) if self.side == "right" else (75, 5)
        self.move_all({
            "index": (90, -90), "middle": (90, -90),
            "ring": (90, -90), "thumb": thumb,
        })

    def rock_sign(self):
        thumb = (0, -75) if self.side == "right" else (75, 0)
        self.move_all({
            "index": (90, -90), "middle": (-35, 35),
            "ring": (90, -90), "thumb": thumb,
        })

    # ---------- 主流程 ----------
    def run_sequence(self, loops=0):
        """跑一遍完整手势序列；loops<=0 表示无限循环。"""
        n = 0
        while loops <= 0 or n < loops:
            n += 1
            if not self.dry_run and n == 1:
                for sid in SCAN_IDS:
                    try:
                        self.ctrl.write_torque_enable(sid, 1)  # 1=On 2=Off 3=Free
                    except Exception:
                        pass

            steps = [
                (self.open_hand, 0.5),
                (self.close_hand, 3.0),
                (self.open_hand_progressive, 0.5),
                (self.spread_hand, 0.6),
                (self.clench_hand, 0.6),
                (self.open_hand, 0.2),
                (self.index_pointing, 0.4),
                (self.nonono, 0.5),
                (self.open_hand, 0.3),
                (self.perfect, 0.8),
                (self.open_hand, 0.4),
                (self.victory, 1.0),
                (self.scissors, 0.5),
                (self.open_hand, 0.4),
                (self.pinched, 1.0),
                (self.rock_sign, 0.8),
            ]
            for fn, hold in steps:
                if self.verbose:
                    print(f"\n--- {fn.__name__} ---", flush=True)
                fn()
                time.sleep(hold)


def main(argv=None):
    ap = argparse.ArgumentParser(description="AmazingHand 基础手势 demo")
    ap.add_argument("--port", help="串口，如 /dev/ttyUSB0（默认自动扫描）")
    ap.add_argument("--side", choices=["right", "left"], default="right")
    ap.add_argument("--middle-pos", nargs=8, type=float, metavar="DEG",
                    help="8 个舵机的标定中间位（度），默认 3 0 -5 -8 -2 5 -12 0")
    ap.add_argument("--loops", type=int, default=1, help="循环次数，0=无限")
    ap.add_argument("--dry-run", action="store_true", help="不连硬件，只打印目标角度")
    ap.add_argument("--quiet", action="store_true", help="少打印")
    args = ap.parse_args(argv)

    ctrl = None
    if not args.dry_run:
        if Scs0009PyController is None:
            print("缺少 rustypot。请在 conda 环境 yolov10 下运行：\n"
                  "  conda activate yolov10\n"
                  "  pip install -r requirements.txt", file=sys.stderr)
            return 1
        port = args.port or autodetect_port()
        if not port:
            print("未找到可用串口。请确认机械手已通过 USB 串口连接，或用 --port 指定。",
                  file=sys.stderr)
            print(f"已尝试: {', '.join(candidate_ports()) or '(无任何串口节点)'}", file=sys.stderr)
            return 2
        print(f"使用串口: {port} @ {BAUD} bps")
        ctrl = Scs0009PyController(serial_port=port, baudrate=BAUD, timeout=0.5)
        found = ctrl.scan(SCAN_IDS)
        # scan 在新版 rustypot 返回 {id: model}, 旧版返回 [id, ...]
        ids = sorted(found.keys()) if isinstance(found, dict) else sorted(found or [])
        print(f"在线舵机: {ids or '无'}")
        if not ids:
            print("未检测到任何舵机，请检查：\n"
                  "  1) 端口是否为 TTL 转接板（Windows 上可能是 CH340/CP2102 对应的 COM 口，"
                  "不是蓝牙串口）\n"
                  "  2) 舵机总线接线（信号/电源/GND）与供电\n"
                  "  3) 波特率是否为 1000000", file=sys.stderr)
            ctrl.close()
            return 3
        missing = sorted(set(SCAN_IDS) - set(ids))
        if missing:
            print(f"⚠️  以下 ID 未响应: {missing}（检查接线/供电/ID 配置）")

    hand = Hand(ctrl, side=args.side, middle_pos=args.middle_pos,
                dry_run=args.dry_run, verbose=not args.quiet)
    mode = "DRY-RUN（未连硬件）" if hand.dry_run else "硬件模式"
    print(f"\n开始运行手势序列 | {mode} | 手别: {args.side}")
    try:
        hand.run_sequence(loops=args.loops)
    except KeyboardInterrupt:
        print("\n已中断")
    finally:
        if ctrl is not None:
            try:
                ctrl.close()
            except Exception:
                pass
    if hand.dry_run:
        print(f"\nDRY-RUN 完成，共下发 {hand.frames} 帧目标位置。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
