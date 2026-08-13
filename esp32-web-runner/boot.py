# boot.py —— 开机最小初始化（网络在 main.py 里统一处理）
import gc
import sys

sys.path.append('/lib')
sys.path.append('/programs')

gc.collect()

print('MicroPython boot ok')