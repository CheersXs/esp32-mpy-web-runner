from machine import Pin
from neopixel import NeoPixel
import time
import math

# 初始化 WS2812，GPIO48，1颗灯珠
pin = Pin(48, Pin.OUT)
np = NeoPixel(pin, 1)

# 亮度系数 0.1
BRIGHTNESS = 0.05


def hsv_to_rgb(h, s, v):
    """
    h: 0~360 度
    s: 0~1
    v: 0~1
    返回 (r, g, b) 0~255
    """
    if s == 0:
        return (int(v*255), int(v*255), int(v*255))
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
    return (int(r * 255 * BRIGHTNESS), int(g * 255 * BRIGHTNESS), int(b * 255 * BRIGHTNESS))


hue = 0
while True:
    # 饱和度=1，明度=1（最鲜艳）
    r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
    np[0] = (r, g, b)
    np.write()
    hue += 1          # 每次增加 1°
    if hue >= 360:
        hue = 0
    time.sleep_ms(20) # 调整速度，数字越小变化越快