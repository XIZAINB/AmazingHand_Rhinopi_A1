#!/usr/bin/env python3
"""扫描本机所有串口，寻找 Feetech SCS0009 总线舵机（AmazingHand）。

用法:
    sudo /home/aidlux/hand/.venv/bin/python tools/probe_servos.py [端口...]
不传参数时自动扫描常见串口。
"""

import glob
import os
import sys

from rustypot import Scs0009PyController

BAUD = 1_000_000  # AmazingHand / SCS0009 总线默认波特率
IDS = list(range(0, 21))

PATTERNS = [
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/ttyCH343USB*",
    "/dev/ttyCH341USB*",
    "/dev/ttyHS*",
    "/dev/ttyS[0-3]",
    "/dev/ttyAMA*",
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
    for pat in PATTERNS:
        ports.extend(glob.glob(pat))
    return [p for p in dict.fromkeys(ports) if os.path.exists(p)]


def _scalar(v):
    """rustypot 新版 read_* 可能返回 list，统一取第一个元素。"""
    if isinstance(v, (list, tuple)):
        return v[0] if v else float("nan")
    return v


def probe(port):
    print(f"\n== {port} ==", flush=True)
    try:
        ctrl = Scs0009PyController(serial_port=port, baudrate=BAUD, timeout=0.15)
    except Exception as e:  # 打不开（权限/无设备/不支持）
        print(f"  [跳过] 无法打开: {type(e).__name__}: {e}", flush=True)
        return None

    try:
        found = ctrl.scan(IDS)
        if found:
            # scan 在新版返回 {id: model}, 旧版返回 [id, ...]
            ids = list(found.keys()) if isinstance(found, dict) else list(found)
            print(f"  [发现] 舵机 ID: {ids}", flush=True)
            for sid in ids:
                try:
                    pos = _scalar(ctrl.read_present_position(sid))
                    volt = _scalar(ctrl.read_present_voltage(sid))
                    temp = _scalar(ctrl.read_present_temperature(sid))
                    print(
                        f"    ID {sid:>2}: 位置={pos:+.4f} rad  电压={volt:.1f} V  温度={temp:.0f} °C",
                        flush=True,
                    )
                except Exception as e:
                    print(f"    ID {sid:>2}: 读取状态失败 {type(e).__name__}: {e}", flush=True)
            return ids
        print("  [无响应] 未发现舵机", flush=True)
    except Exception as e:
        print(f"  [错误] scan 失败: {type(e).__name__}: {e}", flush=True)
    finally:
        try:
            ctrl.close()
        except Exception:
            pass
    return None


def main():
    ports = sys.argv[1:] or candidate_ports()
    if not ports:
        print("未找到任何串口设备节点")
        return 1
    print(f"待扫描端口 ({len(ports)}): {', '.join(ports)}")
    hits = {}
    for p in ports:
        r = probe(p)
        if r:
            hits[p] = r
    print("\n" + "=" * 50)
    if hits:
        for p, ids in hits.items():
            print(f"✅ {p}  -> 舵机 {ids}")
        return 0
    print("❌ 所有端口均未发现舵机")
    return 2


if __name__ == "__main__":
    sys.exit(main())
