import json
import os

VERSION = '2.1.0'

CONFIG_PATH = '/config.json'

DEFAULT_CONFIG = {
    'wifi': {'ssid': '', 'password': ''},
    'ap': {'enabled': True, 'ssid': 'ESP32-S3', 'password': ''},
    'auth': {'enabled': False, 'password': ''},
    'autostart': [],
}


# ---------- 芯片检测 ----------

def board():
    """返回芯片型号字符串：'esp32s3' / 'esp32c3' / 'esp32' / 'unknown'。

    基于 os.uname().machine 判断，用于运行时动态适配资源参数。
    """
    try:
        m = os.uname().machine.lower()
    except Exception:
        return 'unknown'
    if 'esp32s3' in m:
        return 'esp32s3'
    if 'esp32c3' in m:
        return 'esp32c3'
    if 'esp32' in m:
        return 'esp32'
    return 'unknown'


def is_c3():
    """是否为 ESP32-C3（内存最紧张，需降级资源参数）。"""
    return board() == 'esp32c3'


# ---------- 动态资源参数（S3 高性能，C3 自动降级省内存） ----------

def console_max_lines():
    """控制台日志缓冲行数。C3 降级以省内存。"""
    return 150 if is_c3() else 500


def hub_max_queue():
    """WebSocket 离线消息队列上限。C3 降级以省内存。"""
    return 300 if is_c3() else 2000


# ---------- 配置读写 ----------

def _deep_copy(cfg):
    try:
        return json.loads(json.dumps(cfg))
    except Exception:
        return {
            'wifi': {'ssid': '', 'password': ''},
            'ap': {'enabled': True, 'ssid': 'ESP32-S3', 'password': ''},
            'auth': {'enabled': False, 'password': ''},
            'autostart': [],
        }


def load():
    cfg = _deep_copy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
        for key, val in data.items():
            if key in cfg:
                if isinstance(cfg[key], dict) and isinstance(val, dict):
                    cfg[key].update(val)
                else:
                    cfg[key] = val
    except OSError:
        pass
    except Exception:
        pass
    return cfg


def save(cfg):
    tmp = CONFIG_PATH + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(cfg, f)
        try:
            os.remove(CONFIG_PATH)
        except OSError:
            pass
        os.rename(tmp, CONFIG_PATH)
    except Exception:
        pass