import json

CONFIG_PATH = '/config.json'

DEFAULT_CONFIG = {
    'wifi': {'ssid': '', 'password': ''},
    'ap': {'ssid': 'ESP32-S3', 'password': ''},
    'auth': {'enabled': False, 'password': ''},
    'autostart': [],
}


def _deep_copy(cfg):
    try:
        return json.loads(json.dumps(cfg))
    except Exception:
        return {
            'wifi': {'ssid': '', 'password': ''},
            'ap': {'ssid': 'ESP32-S3', 'password': ''},
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
        import os
        try:
            os.remove(CONFIG_PATH)
        except OSError:
            pass
        os.rename(tmp, CONFIG_PATH)
    except Exception:
        pass