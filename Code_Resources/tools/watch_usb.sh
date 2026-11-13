#!/usr/bin/env bash
# 监听 USB / 串口设备变化。运行后插拔转接板，可直接看到系统有没有反应。
# 用法: sudo ./watch_usb.sh [监听秒数，默认60]

DURATION="${1:-60}"
END=$((SECONDS + DURATION))

snapshot() {
    {
        echo "--- USB 设备 ---"
        ls /sys/bus/usb/devices/ 2>/dev/null || true
        echo "--- 串口节点 ---"
        ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyCH34* 2>/dev/null || true
        echo "--- UDC 状态 ---"
        cat /sys/class/udc/a600000.usb/state 2>/dev/null || true
    } | md5sum | awk '{print $1}'
}

echo "=== 开始监听 ${DURATION}s，请现在插拔转接板 ==="
PREV=$(snapshot)
echo "初始状态指纹: $PREV"
echo "初始 USB 设备: $(ls /sys/bus/usb/devices/ 2>/dev/null | tr '\n' ' ')[空]"
echo

while [ $SECONDS -lt $END ]; do
    CUR=$(snapshot)
    if [ "$CUR" != "$PREV" ]; then
        echo ">>> [$SECONDS s] 检测到变化！"
        echo "    USB 设备: $(ls /sys/bus/usb/devices/ 2>/dev/null | tr '\n' ' ')[空]"
        echo "    串口节点: $(ls /dev/ttyUSB* /dev/ttyACM* /dev/ttyCH34* 2>/dev/null | tr '\n' ' ')[空]"
        echo "    UDC 状态: $(cat /sys/class/udc/a600000.usb/state 2>/dev/null)"
        PREV=$CUR
        CHANGED=1
    fi
    sleep 0.3
done

echo
if [ -n "$CHANGED" ]; then
    echo "✅ 监听期间有设备变化，请把上面的串口节点告诉助手。"
else
    echo "❌ ${DURATION}s 内系统没有任何反应 —— 转接板未被枚举（确认是 USB Host 缺失）。"
    echo "   参考 DEPLOY.md 第 7 节。"
fi
