#type:async
# 板上可开关的异步程序示例：让板载 LED 每秒闪烁
# 改引脚：把 48 改成你的板子的 LED GPIO（很多 S3 板子是 48）
import uvm
import machine

led = machine.Pin(48, machine.Pin.OUT)


async def main():
    print('[blink] started, LED @ GPIO48')
    while not uvm.should_stop():
        led.value(not led.value())
        await uvm.sleep_ms(500)
    led.value(0)
    print('[blink] stopped')