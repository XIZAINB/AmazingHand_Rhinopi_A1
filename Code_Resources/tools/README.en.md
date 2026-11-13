# AmazingHand · Host Tools

Drive the AmazingHand dexterous hand (8 × Feetech SCS0009 serial-bus servos, 1 Mbps) from
Python through a USB-TTL bus adapter.

**Languages**: English | [简体中文](README.md)

---

## 1. Environment

Requires **Python 3.10+**. Use a dedicated virtual environment so you do not pollute the
system interpreter.

### AidLux Rhino Pi A1 / Ubuntu

```bash
cd AmazingHand_Rhinopi_A1
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

Afterwards either use `.venv/bin/python` explicitly or `source .venv/bin/activate` first.

### Windows workstation

```powershell
conda create -n amazinghand python=3.10 -y
conda activate amazinghand
pip install -r requirements.txt
```

> The scripts must run in the interpreter that actually has `rustypot` installed.
> If your prompt shows `(base)` while the dependencies live in another environment,
> you will get `缺少 rustypot` (missing rustypot).

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `rustypot` (>=1.13) | SCS series serial-bus servo protocol |
| `numpy` (>=1.24) | degree / radian conversion |
| `pyserial` | pulled in by `rustypot`; used on Windows to enumerate COM ports |

## 3. Identify the serial port (most common pitfall)

### Linux (AidLux Rhino Pi A1)

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* /dev/ttyCH343USB* 2>/dev/null
dmesg | tail -20          # plug/unplug the adapter and watch the kernel enumerate it
```

`Permission denied` means you lack serial permission:

```bash
sudo usermod -aG dialout $USER   # takes effect after logging out and back in
```

### Windows

Windows usually exposes several `COM` ports at once. **A Bluetooth virtual serial port is not
the adapter** — connecting to it will always find zero servos.

```powershell
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'COM\d+' } | Select-Object Name, DeviceID
```

Typical output:

```
蓝牙链接上的标准串行 (COM3)      <- do not use
蓝牙链接上的标准串行 (COM5)      <- do not use
USB-SERIAL CH340 (COM21)        <- this is the adapter
```

Look for a USB-serial chip name such as **`USB-SERIAL CH340`** or **`CP210x`**. The port number
can change when you replug the adapter, so re-check it each time.

## 4. Scanning servos

Two tools with different purposes:

| Script | Purpose |
|---|---|
| `scan_bus.py` | Scan one specific port and print a position / voltage / temperature / torque table (used for the QCS6490 on-device validation) |
| `probe_servos.py` | Try every candidate port and find which one has servos attached |

### scan_bus.py

```bash
python scan_bus.py                       # defaults to /dev/ttyUSB0 @ 1000000
python scan_bus.py /dev/ttyUSB0 1000000
python scan_bus.py COM21                 # Windows
```

Output:

```
端口=/dev/ttyUSB0 波特率=1000000
  ID     在线    位置(deg)    电压(V)    温度(C)     扭矩
   1    YES      92.87     51.0       22      1
   2    YES     -89.94     50.0       23      1
   ...
   8    YES     -74.12     50.0       26      1

在线舵机: [1, 2, 3, 4, 5, 6, 7, 8]  共 8/8
```

### probe_servos.py

```bash
python probe_servos.py                  # probe every serial port
python probe_servos.py /dev/ttyUSB0     # Linux
python probe_servos.py COM21            # Windows
```

Expected output (all 8 servos online):

```
== COM21 ==
  [发现] 舵机 ID: [1, 2, 3, 4, 5, 6, 7, 8]
    ID  1: 位置=+1.2579 rad  电压=51.0 V  温度=21 °C
    ...
✅ COM21  -> 舵机 [1, 2, 3, 4, 5, 6, 7, 8]
```

> The voltage field uses the servo's **raw unit of 0.1 V** — `51.0` means **5.1 V**, not 51 V.
> 20–30 °C is normal; shut down and cool above 55 °C. Torque: `1` = On, `2` = Off, `3` = Free.

## 5. Running the gesture demo

```bash
python hand_demo.py                     # auto-detect the port, play the full sequence
python hand_demo.py --port /dev/ttyUSB0 # Linux, explicit port
python hand_demo.py --port COM21        # Windows, explicit port
python hand_demo.py --side left         # left hand
python hand_demo.py --loops 0           # loop forever (Ctrl+C to stop)
python hand_demo.py --dry-run           # no hardware, print target angles only
python hand_demo.py --quiet             # less output
python hand_demo.py --middle-pos 3 0 -5 -8 -2 5 -12 0   # custom 8 middle positions (deg)
```

### Parameters

| Parameter | Description |
|---|---|
| `--port` | Serial port, e.g. `/dev/ttyUSB0` or `COM21`. Omit to scan every port for one that has servos answering |
| `--side` | `right` (default) / `left` |
| `--middle-pos` | 8 calibrated middle positions in degrees, ordered ID 1→8 |
| `--loops` | Number of repetitions; `0` means infinite |
| `--dry-run` | No hardware, just print the target angle of every frame |
| `--quiet` | Reduce output |

### Gesture sequence

`open_hand` → `close_hand` → `open_hand_progressive` → `spread_hand` → `clench_hand` → `index_pointing` → `nonono` → `perfect` → `victory` → `scissors` → `pinched` → `rock_sign`

## 6. Closed-loop verification

Commands the `open_hand` pose, waits 1.5 s, then reads back the actual positions and prints
the error per ID:

```bash
python verify_closed_loop.py                     # defaults to /dev/ttyUSB0
python verify_closed_loop.py /dev/ttyUSB0
python verify_closed_loop.py COM21               # Windows
```

```
 ID     target  actual   error
  1     -32.00  -31.85    0.15
  2      35.00   34.76    0.24
  ...

Conclusion: closed loop OK, servos reached the target positions
```

The threshold is 5°; exceeding it points to a mechanical linkage or power-supply problem on
that finger. On the QCS6490 all 8 servos measured **< 1.4°**.

## 7. Servo ID assignment

Two servos per finger; the `MiddlePos` index is `(id-1, id)`:

| Finger | Servo IDs | MiddlePos index |
|---|---|---|
| index | 1, 2 | 0, 1 |
| middle | 3, 4 | 2, 3 |
| ring | 5, 6 | 4, 5 |
| thumb | 7, 8 | 6, 7 |

## 8. Calibrating the middle positions (important)

`DEFAULT_MIDDLE_POS = [3, 0, -5, -8, -2, 5, -12, 0]` in `hand_demo.py` is the **upstream
author's calibration**. On your hand it will be offset as a whole — every gesture is computed
as *middle position + offset*, so wrong middle positions make every gesture wrong.

Calibration sources (equivalent, pick one):

- **In this repository (recommended)**
  - `upstream/AmazingHand-main/PythonExample/AmazingHand_FingerTest.py`
  - `upstream/AmazingHand-main/PythonExample/AmazingHand_Hand_FingerMiddlePos.py`
  - `upstream/AmazingHand-main/ArduinoExample/Amazing_Hand-Finger_Test.ino`
- **Vendor material pack** (local `vendor/` directory; large, not distributed with the repo)
  ```
  vendor/00 先看这个/00 TTL串口舵机/arduino程序（MEGA328P开发板）/
    01 微调MiddlePos值时使用/Amazing_Hand-Finger_Test/
  ```

Once calibrated, verify with `--middle-pos`, then write the values into `DEFAULT_MIDDLE_POS`.

## 9. FAQ

| Symptom | Cause / fix |
|---|---|
| `缺少 rustypot` (missing rustypot) | The current interpreter lacks the dependencies — use the right virtual / conda environment |
| `Permission denied: '/dev/ttyUSB0'` | Linux: user not in `dialout`, see section 3 |
| No servos found | 9 times out of 10 the wrong port is selected (on Windows it is easy to pick a Bluetooth port). Otherwise check adapter wiring (signal / power / GND) and servo power |
| `RuntimeError: Timeout error` | Nothing answers on that port, so the write times out. Run `probe_servos.py` first |
| Adapter LED is on but no servos answer | The LED only means the adapter is powered. Confirm you are on the **bus port**, not a PWM output |
| Some IDs do not respond | That servo is unplugged, its ID is not 1–8, or the bus has a bad contact |
| Gesture goes the wrong way / hits the limit | `--side` is inverted, or the middle positions are not calibrated |
| Port number suddenly changed | Replugging the adapter changes the port; re-check it |

## 10. Other files

| File | Description |
|---|---|
| `scan_bus.py` | Single-port bus scan; prints a position / voltage / temperature / torque table |
| `probe_servos.py` | Multi-port auto-probing; finds which serial port has servos attached |
| `hand_demo.py` | Basic gesture demo (auto port, left/right hand, dry-run) |
| `verify_closed_loop.py` | Closed-loop check: command a pose, read back and compare |
| `requirements.txt` | Dependency list |
| `watch_usb.sh` | **Linux only** — watches USB device plug/unplug events. On Windows use the command in section 3 |

> The full on-device deployment procedure (measured environment data, wiring, systemd
> autostart) is in [`DEPLOY_qcs6490_aidlux.md`](../DEPLOY_qcs6490_aidlux.md) at the repository
> root — currently written in Chinese.
