# AmazingHand 机械手 · 上位机工具

通过 USB-TTL 转接板直连舵机总线，用 Python 控制 AmazingHand 灵巧手（8 × Feetech SCS0009 总线舵机，1 Mbps）。

**语言 / Languages**: 简体中文 | [English](README.en.md)

---

## 1. 环境

需要 **Python 3.10+**。推荐为项目单独建虚拟环境，避免污染系统解释器。

### AidLux Rhino Pi A1 / Ubuntu

```bash
cd AmazingHand_Rhinopi_A1
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
```

之后所有命令用 `.venv/bin/python` 或先 `source .venv/bin/activate`。

### Windows 开发机

```powershell
conda create -n amazinghand python=3.10 -y
conda activate amazinghand
pip install -r requirements.txt
```

> 注意：脚本必须在**装过 `rustypot` 的那个环境**里跑。
> 如果终端提示符是 `(base)` 而依赖装在别的环境，会报 `缺少 rustypot`。

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

| 包 | 用途 |
|---|---|
| `rustypot` (>=1.13) | SCS 系列总线舵机协议 |
| `numpy` (>=1.24) | 角度弧度换算 |
| `pyserial` | 由 `rustypot` 自动安装，Windows 下用于枚举 COM 口 |

## 3. 确认串口号（最容易踩的坑）

### Linux（AidLux Rhino Pi A1）

```bash
ls -l /dev/ttyUSB* /dev/ttyACM* /dev/ttyCH343USB* 2>/dev/null
dmesg | tail -20          # 插拔转接板，看内核是否枚举成功
```

出现 `Permission denied` 说明没有串口权限：

```bash
sudo usermod -aG dialout $USER   # 重新登录后生效
```

### Windows

Windows 上会同时出现多个 `COM` 口，**蓝牙虚拟串口不是转接板**，连它必然扫不到舵机。

```powershell
Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'COM\d+' } | Select-Object Name, DeviceID
```

典型输出：

```
蓝牙链接上的标准串行 (COM3)      <- 不要用
蓝牙链接上的标准串行 (COM5)      <- 不要用
USB-SERIAL CH340 (COM21)        <- ✅ 转接板就是这个
```

认准 **`USB-SERIAL CH340` / `CP210x`** 这类 USB 串口芯片的名字。转接板插拔一次，端口号可能变化，重新查一遍即可。

## 4. 扫描舵机

两个工具，用途不同：

| 脚本 | 用途 |
|---|---|
| `scan_bus.py` | 指定单个端口，输出位置/电压/温度/力矩表格（QCM6490 实机验证用） |
| `probe_servos.py` | 遍历所有候选端口逐个试，自动找出哪个口上挂有舵机 |

### scan_bus.py

```bash
python scan_bus.py                       # 默认 /dev/ttyUSB0 @ 1000000
python scan_bus.py /dev/ttyUSB0 1000000
python scan_bus.py COM21                 # Windows
```

输出：

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
python probe_servos.py                  # 自动扫描所有串口
python probe_servos.py /dev/ttyUSB0     # Linux
python probe_servos.py COM21            # Windows
```

正常输出（8 个舵机全部在线）：

```
== COM21 ==
  [发现] 舵机 ID: [1, 2, 3, 4, 5, 6, 7, 8]
    ID  1: 位置=+1.2579 rad  电压=51.0 V  温度=21 °C
    ...
✅ COM21  -> 舵机 [1, 2, 3, 4, 5, 6, 7, 8]
```

> 电压字段是舵机的**原始单位 0.1 V**，`51.0` 表示 **5.1 V**，不是 51 V。
> 温度 20~30 ℃ 正常，> 55 ℃ 应停机散热。扭矩 `1`=On / `2`=Off / `3`=Free。

## 5. 运行手势 Demo

```bash
python hand_demo.py                     # 自动找端口，跑一遍全部手势
python hand_demo.py --port /dev/ttyUSB0 # Linux 指定端口
python hand_demo.py --port COM21        # Windows 指定端口
python hand_demo.py --side left         # 左手
python hand_demo.py --loops 0           # 无限循环（Ctrl+C 停止）
python hand_demo.py --dry-run           # 不连硬件，只打印目标角度
python hand_demo.py --quiet             # 少打印
python hand_demo.py --middle-pos 3 0 -5 -8 -2 5 -12 0   # 自定义 8 个中间位（度）
```

### 参数

| 参数 | 说明 |
|---|---|
| `--port` | 串口，如 `/dev/ttyUSB0` 或 `COM21`。省略时自动扫描所有端口找有舵机应答的 |
| `--side` | `right`（默认）/ `left` |
| `--middle-pos` | 8 个舵机的标定中间位（度），按 ID 1→8 顺序 |
| `--loops` | 循环次数，`0` 表示无限 |
| `--dry-run` | 不连硬件，只打印每帧目标角度，用于验证逻辑 |
| `--quiet` | 减少输出 |

### 手势序列

`open_hand` → `close_hand` → `open_hand_progressive` → `spread_hand` → `clench_hand` → `index_pointing` → `nonono` → `perfect` → `victory` → `scissors` → `pinched` → `rock_sign`

## 6. 闭环验证

下发 `open_hand` 姿态，等待 1.5 s 后回读实际位置，逐 ID 打印误差：

```bash
python verify_closed_loop.py                     # 默认 /dev/ttyUSB0
python verify_closed_loop.py /dev/ttyUSB0
python verify_closed_loop.py COM21               # Windows
```

```
 ID       目标       回读       误差
  1     -32.00    -31.85     0.15
  2      35.00     34.76     0.24
  ...

结论: 闭环正常，舵机已跟随目标位
```

误差阈值 5°，超过说明该手指机械传动或供电有问题。QCM6490 实机测得 8 个舵机均 **< 1.4°**。

## 7. 舵机 ID 分配

每根手指 2 个舵机，`MiddlePos` 中对应索引 `(id-1, id)`：

| 手指 | 舵机 ID | MiddlePos 索引 |
|---|---|---|
| index | 1, 2 | 0, 1 |
| middle | 3, 4 | 2, 3 |
| ring | 5, 6 | 4, 5 |
| thumb | 7, 8 | 6, 7 |

## 8. 标定中间位（重要）

`hand_demo.py` 里的 `DEFAULT_MIDDLE_POS = [3, 0, -5, -8, -2, 5, -12, 0]` 是**原作者的标定值**，用到你的手上会整体偏移。所有手势都是「中间位 + 偏移量」算出来的，中间位不准 → 手势全歪。

标定方法（以下几种来源内容等价，任选其一）：

- **本仓库内（推荐）**
  - `upstream/AmazingHand-main/PythonExample/AmazingHand_FingerTest.py`
  - `upstream/AmazingHand-main/PythonExample/AmazingHand_Hand_FingerMiddlePos.py`
  - `upstream/AmazingHand-main/ArduinoExample/Amazing_Hand-Finger_Test.ino`
- **厂商资料包**（本地 `vendor/` 目录，体积大，不随仓库分发）
  ```
  vendor/00 先看这个/00 TTL串口舵机/arduino程序（MEGA328P开发板）/
    01 微调MiddlePos值时使用/Amazing_Hand-Finger_Test/
  ```

标好之后用 `--middle-pos` 传入验证，确认满意再改代码里的 `DEFAULT_MIDDLE_POS` 默认值。

## 9. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `缺少 rustypot` | 当前解释器没装依赖，用对虚拟环境 / conda 环境 |
| `Permission denied: '/dev/ttyUSB0'` | Linux 未加入 `dialout` 组，见第 3 节 |
| 扫不到任何舵机 | 90% 是端口选错（Windows 上尤其容易选到蓝牙口）；其次检查转接板接线（信号 / 电源 / GND）、舵机供电 |
| `RuntimeError: Timeout error` | 端口上没有舵机应答，写指令超时。先跑 `probe_servos.py` 确认 |
| 转接板红灯亮但仍扫不到 | 红灯只代表转接板通电，不代表数据线通。确认用的是 **总线口**，不是 PWM 口 |
| 部分 ID 未响应 | 该舵机没接、ID 不是 1~8、或总线接触不良 |
| 手势方向相反 / 撞限位 | `--side` 用反了，或中间位未标定 |
| 端口号突然变了 | 转接板重新插拔后端口号会变，重新确认 |

## 10. 其他文件

| 文件 | 说明 |
|---|---|
| `scan_bus.py` | 单端口总线扫描，输出位置/电压/温度/力矩表格 |
| `probe_servos.py` | 多端口自动探测，找出哪个串口挂有舵机 |
| `hand_demo.py` | 基础手势 Demo（自动找端口、左右手、dry-run） |
| `verify_closed_loop.py` | 闭环验证：下发姿态并回读比对误差 |
| `requirements.txt` | 依赖清单 |
| `watch_usb.sh` | **仅 Linux** 使用，监听 USB 设备插拔变化。Windows 下用第 3 节的命令代替 |

> 完整实机部署流程（含软硬件实测数据、接线、systemd 开机自启）见仓库根目录的
> [`DEPLOY_qcm6490_aidlux.md`](../DEPLOY_qcm6490_aidlux.md)。

> The English version of this document is [`README.en.md`](README.en.md).
