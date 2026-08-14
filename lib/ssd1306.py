# MicroPython SSD1306 OLED driver，I2C 和 SPI 接口（72x40）
from micropython import const
import framebuf


# register definitions
SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xA4)
SET_NORM_INV = const(0xA6)
SET_DISP = const(0xAE)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xA0)
SET_MUX_RATIO = const(0xA8)
SET_COM_OUT_DIR = const(0xC0)
SET_DISP_OFFSET = const(0xD3)
SET_COM_PIN_CFG = const(0xDA)
SET_DISP_CLK_DIV = const(0xD5)
SET_PRECHARGE = const(0xD9)
SET_VCOM_DESEL = const(0xDB)
SET_CHARGE_PUMP = const(0x8D)


class SSD1306:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = bytearray(self.pages * self.width)
        fb = framebuf.FrameBuffer(
            self.buffer, width, height, framebuf.MONO_VLSB
        )
        self.framebuf = fb
        self.init_display()
        self.show()

    def init_display(self):
        # 根据高度选择 MUX ratio 和 COM pin config
        # 64 行: MUX=0x3F, COMPIN=0x12
        # 40 行(0.42" 72x40): MUX=0x27, COMPIN=0x12
        # 32 行: MUX=0x1F, COMPIN=0x02
        if self.height == 64:
            mux = 0x3F
            compin = 0x12
        elif self.height == 40:
            mux = 0x27
            compin = 0x12
        else:  # 32
            mux = 0x1F
            compin = 0x02
        cmds = (
            0xAE,        # display off
            0x20, 0x00,  # memory addressing: horizontal
            0x40,        # start line 0
            0xA0 | 0x01, # segment remap 127->0
            0xC8,        # COM scan reversed
            0xA8, mux,   # mux ratio
            0xD3, 0x00,  # display offset 0
            0xDA, compin,# com pin cfg
            0xD5, 0x80,  # clock divide / osc
            0xD9, 0xF1,  # precharge
            0xDB, 0x30,  # vcomh deselect
            0x81, 0xFF,  # contrast max
            0xA4,        # output follows RAM
            0xA6,        # normal (not inverted) display
            0x8D, 0x95,  # charge pump on (Newvision N042 规格: 0x95)
            0xAF,        # display on
        )
        for c in cmds:
            self.write_cmd(c)

    def write_cmd(self, cmd):
        raise NotImplementedError

    def write_data(self, buf):
        raise NotImplementedError

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # 64px wide panels are shifted 32px to the right
            x0 += 32
            x1 += 32
        elif self.width == 72:
            # 72x40 屏幕: GRAM 128 列居中 72 列, 列偏移 28
            x0 += 28
            x1 += 28
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)

    def text(self, string, x, y, col=1):
        self.framebuf.text(string, x, y, col)

    def fill(self, col=0):
        self.framebuf.fill(col)

    def rect(self, x, y, w, h, col=1):
        self.framebuf.rect(x, y, w, h, col)

    def fill_rect(self, x, y, w, h, col=1):
        self.framebuf.fill_rect(x, y, w, h, col)

    def pixel(self, x, y, col=1):
        self.framebuf.pixel(x, y, col)

    def scroll(self, dx, dy):
        self.framebuf.scroll(dx, dy)


class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        super().__init__(width, height)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        # 数据段：Co=0, D/C#=1 → 控制字节 0x40 + 数据
        self.i2c.writeto(self.addr, b'\x40' + buf)
