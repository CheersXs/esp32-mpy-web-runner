#type:sync
# 同步脚本示例：在线程里计数 20 次后结束
import uvm

print('[counter] start')
i = 0
while not uvm.should_stop() and i < 20:
    i += 1
    print('[counter] tick', i)
    uvm.sleep_ms(400)
print('[counter] done, total', i)