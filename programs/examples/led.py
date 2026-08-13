#type:async
# 板上可开关的异步程序示例：GPIO48 上的 WS2812 彩虹呼吸灯
# 改引脚：把 48 改成你的板子的 LED GPIO（灯珠数量按实际改）
import uvm
import machine
from neopixel import NeoPixel

pin = machine.Pin(48, machine.Pin.OUT)
np = NeoPixel(pin, 1)

# 亮度系数 0.05
BRIGHTNESS = 0.05


def hsv_to_rgb(h, s, v):
    """
    h: 0~360 度
    s: 0~1
    v: 0~1
    返回 (r, g, b) 0~255
    """
    if s == 0:
        return (int(v * 255), int(v * 255), int(v * 255))
    h = h / 60
    i = int(h)
    f = h - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    # 应用亮度系数
    return (int(r * 255 * BRIGHTNESS), int(g * 255 * BRIGHTNESS),
            int(b * 255 * BRIGHTNESS))


async def main():
    print('[led] started, WS2812 @ GPIO48')
    hue = 0
    while not uvm.should_stop():
        r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
        np[0] = (r, g, b)
        np.write()
        hue = (hue + 1) % 360  # 每次增加 1°
        await uvm.sleep_ms(20)  # 数字越小变化越快
    np[0] = (0, 0, 0)
    np.write()
    print('[led] stopped')
