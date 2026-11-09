# AmazingHand 在 Qualcomm QCM6490 (AidLux) 板卡上的部署指南

> 本文档基于**实机验证**结果编写，所有命令均已在目标板卡上执行通过。
> 目标：在板卡上通过 USB-TTL（CH340）驱动 Amazing Hand 的 8 个 Feetech SCS0009 舵机，并运行基础手势 Demo。

---

## 1. 已验证的软硬件环境

| 项目 | 实测值 |
|---|---|
| 板卡 | Qualcomm Technologies QCM6490 IDP（`qcm6490-addons IDP platform`） |
| 操作系统 | AidLux / Ubuntu 24.04.3 LTS (Noble) |
| 内核 | `6.6.65-qli-1.4-ver.1.1-04093` aarch64 |
| CPU / 内存 | 8 核 / 7.2 GiB |
| Python | 3.12.3（系统 Python，受 PEP 668 保护） |
| 舵机驱动库 | `rustypot 1.13.1`（PyPI 提供 `cp312-manylinux2014_aarch64` 预编译轮子，无需 Rust 工具链） |
| USB 转串口 | CH340（USB ID `1a86:7523`）→ `/dev/ttyUSB0` |
| 稳定设备路径 | `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` |
| 舵机总线波特率 | **1 000 000** bps（SCS0009 出厂默认） |
| 服务管理 | systemd 255 可用 |
| 当前用户 | `aidlux`（属组 `sudo`、`video`，**不含 `dialout`**） |

### 实跑结果

| 验证项 | 结果 |
|---|---|
| 舵机扫描 | **8/8 全部在线**，型号均为 1284（SCS0009） |
| 供电电压回读 | 5.0 ~ 5.1 V（稳定） |
| 舵机温度 | 22 ~ 26 ℃（连续跑完一轮手势后仍正常） |
| 闭环跟随误差 | 8 个舵机均 **< 1.4°** |
| 完整手势序列 | 16 组手势全部执行完毕，无异常、无报错 |

---

## 2. 硬件准备与接线

```
[5V/2A 直流电源] ──┐
                   ├──> [舵机总线: 8 × SCS0009] <──> [CH340 USB-TTL 转接板] ──> 板卡 USB 口
[板卡 USB 口] ─────┘
```

要点：

1. **外部独立供电**：8 个舵机同时动作峰值电流较大，必须用 5V/2A 以上的独立电源给总线供电，**不要**由板卡 USB 口供电。
2. **共地**：电源负极、转接板 GND、舵机总线 GND 必须共地。
3. **转接板**：Waveshare 类串口总线舵机驱动板或 Feetech TTL Linker 均可；本板卡上一次枚举成功的是 CH340。
4. 舵机 ID 必须为右手配置 **1~8**（可先用 Feetech 上位机设置好），左右手同一总线上 ID 不能重复。

---

## 3. 系统层确认串口

插上 USB-TTL 后执行：

```bash
# 1) 确认 USB 芯片被识别
lsusb | grep -i 1a86          # 期望: QinHeng Electronics CH340 serial converter

# 2) 确认内核已创建 tty 节点
dmesg | grep -iE "ch341|ttyUSB" | tail -5
# 期望: ch341-uart converter now attached to ttyUSB0

# 3) 确认设备与权限
ls -l /dev/ttyUSB0
# 本板实测: crw-rw-rw- 1 root dialout 188, 0 /dev/ttyUSB0  (0666，当前用户可直接读写)

# 4) 建议使用稳定路径（避免插拔后编号变化）
ls /dev/serial/by-id/
# usb-1a86_USB_Serial-if00-port0
```

> **权限说明**：本板卡上 `/dev/ttyUSB0` 权限为 `0666`，`aidlux` 用户可直接访问。若换到权限为 `0660 root:dialout` 的系统，需把用户加入 `dialout` 组：
> ```bash
> sudo usermod -aG dialout $USER   # 重新登录生效
> ```

---

## 4. 获取代码并部署 Python 环境

### 4.1 克隆仓库

```bash
cd ~
git clone https://github.com/XIZAINB/AmazingHand_Rhinopi_A1.git
cd AmazingHand_Rhinopi_A1
```

仓库分两部分：

| 目录 | 内容 |
|---|---|
| `upstream/AmazingHand-main/` | 上游 Pollen Robotics 原始资料快照（CAD / 固件 / 官方示例 / 装配文档） |
| `tools/` | 本仓库为 QCM6490 (AidLux) 板卡适配的可运行工具 |

下文所有命令均在**仓库根目录** `~/AmazingHand_Rhinopi_A1` 下执行。

### 4.2 创建虚拟环境

系统 Python 受 PEP 668 保护（`externally-managed-environment`），**必须使用虚拟环境**：

```bash
# 创建虚拟环境（继承系统已装的 numpy，省一次编译）
python3 -m venv .venv --system-site-packages

# 2) 升级 pip
.venv/bin/pip install -q --upgrade pip

# 3) 安装依赖（国内网络建议用镜像，直连 PyPI 会出现长时间无响应）
.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rustypot numpy

# 4) 验证
.venv/bin/python -c "import rustypot, numpy; print('ok')"
```

实测安装输出（aarch64 预编译轮子，无需编译）：

```
Downloading rustypot-1.13.1-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (2.4 MB)
Successfully installed rustypot-1.13.1
```

> **不要**使用 `--break-system-packages` 直接装到系统 Python，AidLux 镜像升级时容易冲突。

---

## 5. 冒烟测试：扫描舵机总线

```bash
cd ~/AmazingHand_Rhinopi_A1
.venv/bin/python tools/scan_bus.py /dev/ttyUSB0 1000000
```

若不传参数，默认就是 `/dev/ttyUSB0` + `1000000`，可简写为：

```bash
.venv/bin/python tools/scan_bus.py
```

正常输出（实测）：

```
端口=/dev/ttyUSB0 波特率=1000000
  ID     在线    位置(deg)    电压(V)    温度(C)     扭矩
   1    YES      92.87     51.0       22      1
   2    YES     -89.94     50.0       23      1
   3    YES     -39.55     50.0       23      1
   4    YES      27.25     49.0       23      1
   5    YES      87.89     51.0       23      1
   6    YES     -84.96     49.0       23      1
   7    YES     -11.72     49.0       23      1
   8    YES     -74.12     50.0       26      1

在线舵机: [1, 2, 3, 4, 5, 6, 7, 8]  共 8/8
```

判读标准：

- 电压列 `49~51` 表示 **4.9~5.1 V**（寄存器以 0.1V 为单位）；
- 温度 20~30 ℃ 属正常；> 55 ℃ 应停机散热；
- 扭矩列 `1` = 力矩使能（1=On，2=Off，3=Free）。

---

## 6. 运行手势 Demo

```bash
cd ~/AmazingHand_Rhinopi_A1

# ① 先做离线校验（不接硬件，只打印每帧目标角度）
.venv/bin/python tools/hand_demo.py --dry-run --loops 1

# ② 硬件实跑（指定串口，避免脚本去扫 /dev/ttyS0-3 那几个板载 UART 造成卡顿）
.venv/bin/python tools/hand_demo.py --port /dev/ttyUSB0 --side right --loops 1

# ③ 无限循环演示
.venv/bin/python tools/hand_demo.py --port /dev/ttyUSB0 --side right --loops 0
```

### 完整跑案例流程（从零到动起来）

```bash
cd ~
git clone https://github.com/XIZAINB/AmazingHand_Rhinopi_A1.git
cd AmazingHand_Rhinopi_A1
python3 -m venv .venv --system-site-packages
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rustypot numpy

.venv/bin/python tools/scan_bus.py                       # 确认 8/8 在线
.venv/bin/python tools/hand_demo.py --dry-run --loops 1  # 离线校验角度
.venv/bin/python tools/hand_demo.py --port /dev/ttyUSB0 --side right --loops 1
```

### 参数说明

| 参数 | 说明 |
|---|---|
| `--port` | 串口，板卡上固定用 `/dev/ttyUSB0`，也可用 `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` |
| `--side` | `right` / `left`，右手 = 原始 demo 的 `Side=1` |
| `--middle-pos` | 8 个舵机的标定中间位（度），顺序 ID1→ID8 |
| `--loops` | 循环次数，`0` 为无限循环 |
| `--dry-run` | 不连硬件，仅打印目标角度 |
| `--quiet` | 精简日志 |

### 实测运行日志（板卡上）

```
使用串口: /dev/ttyUSB0 @ 1000000 bps
在线舵机: [1, 2, 3, 4, 5, 6, 7, 8]
开始运行手势序列 | 硬件模式 | 手别: right
--- open_hand ---
--- close_hand ---
--- open_hand_progressive ---
--- spread_hand ---
--- clench_hand ---
--- open_hand ---
--- index_pointing ---
--- nonono ---
--- open_hand ---
--- perfect ---
--- open_hand ---
--- victory ---
--- scissors ---
--- open_hand ---
--- pinched ---
--- rock_sign ---
```

16 组手势全部下发完成，无异常退出。

---

## 7. 闭环验证：下发姿态并回读比对

确认机械结构装配到位后，跑一次闭环验证——下发 `open_hand` 姿态，等待 1.5 s 后回读实际位置，逐 ID 打印误差：

```bash
cd ~/AmazingHand_Rhinopi_A1
.venv/bin/python tools/verify_closed_loop.py
```

实测误差：8 个舵机均 **< 1.4°**，说明总线通信、力矩使能、机械传动均正常。

如果某个 ID 误差超过 5°，优先检查该手指的球头连杆是否装配到位。

## 8. 标定（MiddlePos）与安全注意事项

Demo 中 `MiddlePos` 是**每只手单独标定**的结果，默认值 `[3, 0, -5, -8, -2, 5, -12, 0]` 是原作者那只手的值。

标定流程（沿用官方 `AmazingHand_FingerTest.py`）：

1. 修改脚本中的 `ID_1` / `ID_2` 为当前要标定的手指对应舵机（1-2 食指、3-4 中指、5-6 无名指、7-8 拇指）；
2. 用 `AmazingHand_Hand_FingerMiddlePos.py` 把该手指摆到机械中位；
3. 回读 `read_present_position()` 的角度，换算成度后填入 `MiddlePos` 对应两项；
4. 四根手指全部做完，得到 8 个值，通过 `--middle-pos` 传入。

安全建议：

- 首次试机用 `--loops 1`，并**用手轻扶**观察是否顶到机械限位；
- 若某手指抖动/堵转，立即 `Ctrl+C`，检查该手指球头连杆是否装配到位；
- SCS0009 有堵转保护，但长时间顶死会发热，温度 > 55 ℃ 必须停机；
- 修改 `MiddlePos` 后先用 `--dry-run` 核对角度再上硬件。

---

## 9. 开机自启（可选，systemd）

```bash
sudo tee /etc/systemd/system/amazinghand.service > /dev/null <<'EOF'
[Unit]
Description=AmazingHand gesture demo
After=multi-user.target

[Service]
Type=simple
User=aidlux
WorkingDirectory=/home/aidlux/AmazingHand_Rhinopi_A1
ExecStart=/home/aidlux/AmazingHand_Rhinopi_A1/.venv/bin/python /home/aidlux/AmazingHand_Rhinopi_A1/tools/hand_demo.py --port /dev/ttyUSB0 --side right --loops 0
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now amazinghand.service
systemctl status amazinghand.service --no-pager
journalctl -u amazinghand.service -f          # 查看实时日志
```

调试期建议先手动运行确认动作正常，再启用开机自启。

---

## 10. 常见问题排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `error: externally-managed-environment` | Ubuntu 24.04 PEP 668 | 用 `python3 -m venv .venv --system-site-packages` 建虚拟环境 |
| `pip install` 长时间卡住 | 直连 PyPI 网络差 | 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `ModuleNotFoundError: rustypot` | 用了系统 python 而非 venv | 统一用 `.venv/bin/python` 运行 |
| `Permission denied: '/dev/ttyUSB0'` | 用户不在 `dialout` 组 | `sudo usermod -aG dialout $USER` 后重新登录 |
| `lsusb` 无 `1a86:7523` | USB 未插好 / 线材问题 | 换线换口，`dmesg \| tail` 看枚举日志 |
| 扫描 0 个舵机 | 波特率不对 / 未外部供电 / 未共地 | 确认 1 000 000 bps、5V 供电、GND 共地 |
| 部分 ID 不响应 | 舵机 ID 未设置或接线断 | 用 Feetech 上位机重设 ID（右手 1~8），检查总线串接 |
| `TypeError: must be real number, not list` | rustypot 1.13.1 的 `read_*` **返回 list** | 取值用 `read_present_position(id)[0]` |
| 舵机不动但通信正常 | 力矩未使能 | `write_torque_enable(id, 1)`（1=On，2=Off，3=Free） |
| 手指顶到限位 / 异响 | MiddlePos 标定值不匹配 | 重新标定，或先用当前回读角度作为中间位 |
| `--port` 不写时启动很慢 | 自动扫描会遍历 `/dev/ttyS0-3` 等板载 UART | 显式传 `--port /dev/ttyUSB0` |

---

## 11. 已知 API 差异（rustypot 1.13.1）

在 aarch64 上实测到的行为，编写脚本时需要注意：

| 接口 | 行为 |
|---|---|
| `scan([1..8])` | 返回 `dict`：`{1: 1284, 2: 1284, ...}`，**1284 = SCS0009 型号号** |
| `read_present_position(id)` | 参数为单个 ID，**返回 list**，需 `[0]` 取标量（弧度） |
| `read_present_voltage(id)` | 同上，返回 0.1V 单位整数 |
| `write_goal_position(id, rad)` | 入参为 `int` + `float`（**弧度**） |
| `write_goal_speed(id, spd)` | SCS0009 速度范围 1~7 |
| `write_torque_enable(id, v)` | `1`=On，`2`=Off，`3`=Free |

---

## 12. 仓库目录与文件清单

```
~/AmazingHand_Rhinopi_A1/
├── README.md                        # 项目总览
├── DEPLOY_qcm6490_aidlux.md         # 本文——QCM6490 / AidLux 实机部署指南
├── LICENSE                          # Apache 2.0
├── NOTICE                           # 上游归属声明
├── .venv/                           # 虚拟环境（rustypot 1.13.1 + numpy）
│
├── upstream/AmazingHand-main/       # 上游 Pollen Robotics 原始快照
│   ├── PythonExample/               #   官方 Python 示例（串口写死 COM11）
│   ├── ArduinoExample/              #   官方 Arduino 方案
│   ├── Demo/                        #   进阶 demo（IK/FK、Rust 控制、MuJoCo 仿真）
│   ├── cad/                         #   STEP / STL 打印件
│   └── docs/                        #   装配文档与 PDF
│
└── tools/                           # 本仓库适配层（在 QCM6490 上验证通过）
    ├── scan_bus.py                  #   总线扫描：位置 / 电压 / 温度 / 力矩
    ├── hand_demo.py                 #   可用化 demo：自动找口 / --side / --dry-run
    ├── verify_closed_loop.py        #   闭环验证：下发姿态并回读比对误差
    ├── probe_servos.py              #   多端口自动探测扫描（Linux + Windows）
    ├── requirements.txt             #   依赖清单
    ├── watch_usb.sh                 #   USB 热插拔监听（Linux）
    └── README.md                    #   参数手册与排障
```

---

## 13. 附：原始官方 demo 在板卡上的改动点

`upstream/AmazingHand-main/PythonExample/AmazingHand_Demo.py` 默认无法直接在 Linux 板卡运行，需改 2 处：

```python
Side = 1                                        # 1=右手, 2=左手

c = Scs0009PyController(
    serial_port="/dev/ttyUSB0",                 # 原为 "COM11"（Windows）
    baudrate=1000000,
    timeout=0.5,
)
```

`tools/hand_demo.py` 已把上述改动做成命令行参数，并额外增加了端口自动探测、`--dry-run`、环路使能、异常退出等健壮性处理。
