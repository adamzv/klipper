# Support for ST7789V (240x320 RGB) LCD displays
#
# Copyright (C) 2026  Adam Zverka <adamzverka@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from .. import bus
from . import font8x14

BACKGROUND_PRIORITY_CLOCK = 0x7fffffff00000000

ST7789V_WIDTH = 240
ST7789V_HEIGHT = 320
CELL_WIDTH = 8
CELL_HEIGHT = 16
DEFAULT_COLS = 20
DEFAULT_ROWS = 4
SPI_CHUNK_SIZE = 56

ST7789V_CMD_SLPOUT = 0x11
ST7789V_CMD_DISPON = 0x29
ST7789V_CMD_CASET = 0x2a
ST7789V_CMD_RASET = 0x2b
ST7789V_CMD_RAMWR = 0x2c
ST7789V_CMD_MADCTL = 0x36
ST7789V_CMD_COLMOD = 0x3a

TextGlyphs = {'right_arrow': b'\x1a', 'degrees': b'\xf8'}

class ST7789V:
    def __init__(self, config):
        self.spi = bus.MCU_SPI_from_config(config, 0, default_speed=3000000)
        self.mcu_rs = bus.MCU_bus_digital_out(
            self.spi.get_mcu(), config.get('rs_pin'),
            self.spi.get_command_queue())
        self.mcu_reset = bus.MCU_bus_digital_out(
            self.spi.get_mcu(), config.get('rst_pin'),
            self.spi.get_command_queue())
        self.columns = config.getint('columns', DEFAULT_COLS, minval=1,
                                     maxval=ST7789V_WIDTH // CELL_WIDTH)
        self.rows = config.getint('rows', DEFAULT_ROWS, minval=1,
                                  maxval=ST7789V_HEIGHT // CELL_HEIGHT)
        default_x = (ST7789V_WIDTH - self.columns * CELL_WIDTH) // 2
        default_y = ST7789V_HEIGHT - self.rows * CELL_HEIGHT - CELL_HEIGHT
        self.x_offset = config.getint('x_offset', default_x, minval=0,
                                      maxval=ST7789V_WIDTH - 1)
        self.y_offset = config.getint('y_offset', default_y, minval=0,
                                      maxval=ST7789V_HEIGHT - 1)
        if self.x_offset + self.columns * CELL_WIDTH > ST7789V_WIDTH:
            raise config.error("ST7789V text area exceeds display width")
        if self.y_offset + self.rows * CELL_HEIGHT > ST7789V_HEIGHT:
            raise config.error("ST7789V text area exceeds display height")
        self.fg = b'\xff\xff'
        self.bg = b'\x00\x00'
        self.blank_cell = self._render_bitmap([0] * CELL_HEIGHT)
        self.cells = [[bytearray(self.blank_cell) for c in range(self.columns)]
                      for r in range(self.rows)]
        self.remote_cells = [[bytearray(b'~' * len(self.blank_cell))
                              for c in range(self.columns)]
                             for r in range(self.rows)]
        self.dirty = set((r, c) for r in range(self.rows)
                         for c in range(self.columns))
        self.icons = {}

    def _render_bitmap(self, rows):
        cell = bytearray()
        rows = bytearray(rows)
        if len(rows) < CELL_HEIGHT:
            rows += bytearray(CELL_HEIGHT - len(rows))
        for row_bits in rows[:CELL_HEIGHT]:
            for bit in range(7, -1, -1):
                if row_bits & (1 << bit):
                    cell.extend(self.fg)
                else:
                    cell.extend(self.bg)
        return cell

    def _set_cell(self, row, col, data):
        if row < 0 or row >= self.rows or col < 0 or col >= self.columns:
            return
        if self.cells[row][col] != data:
            self.cells[row][col] = bytearray(data)
            self.dirty.add((row, col))

    def _send(self, data):
        data = bytearray(data)
        while data:
            self.spi.spi_send(data[:SPI_CHUNK_SIZE],
                              reqclock=BACKGROUND_PRIORITY_CLOCK)
            data = data[SPI_CHUNK_SIZE:]

    def _cmd(self, cmd, data=None):
        self.mcu_rs.update_digital_out(0, reqclock=BACKGROUND_PRIORITY_CLOCK)
        self.spi.spi_send([cmd], reqclock=BACKGROUND_PRIORITY_CLOCK)
        if data is not None:
            self.mcu_rs.update_digital_out(1,
                                           reqclock=BACKGROUND_PRIORITY_CLOCK)
            self._send(data)

    def _set_window(self, x0, y0, x1, y1):
        self._cmd(ST7789V_CMD_CASET,
                  [x0 >> 8, x0 & 0xff, x1 >> 8, x1 & 0xff])
        self._cmd(ST7789V_CMD_RASET,
                  [y0 >> 8, y0 & 0xff, y1 >> 8, y1 & 0xff])

    def init(self):
        mcu = self.mcu_reset.get_mcu()
        curtime = mcu.get_printer().get_reactor().monotonic()
        print_time = mcu.estimated_print_time(curtime)
        self.mcu_rs.update_digital_out(
            1, minclock=mcu.print_time_to_clock(print_time))
        self.mcu_reset.update_digital_out(
            1, minclock=mcu.print_time_to_clock(print_time))
        print_time += 0.005
        self.mcu_reset.update_digital_out(
            0, minclock=mcu.print_time_to_clock(print_time))
        print_time += 0.015
        self.mcu_reset.update_digital_out(
            1, minclock=mcu.print_time_to_clock(print_time))
        print_time += 0.010
        self.mcu_reset.update_digital_out(
            1, minclock=mcu.print_time_to_clock(print_time))
        self._cmd(ST7789V_CMD_SLPOUT)
        self._cmd(ST7789V_CMD_MADCTL, [0xc0])
        self._cmd(ST7789V_CMD_COLMOD, [0x05])
        self._cmd(ST7789V_CMD_DISPON)
        self.clear()
        self.flush()

    def flush(self):
        for row, col in sorted(self.dirty):
            if self.cells[row][col] == self.remote_cells[row][col]:
                continue
            x0 = self.x_offset + col * CELL_WIDTH
            y0 = self.y_offset + row * CELL_HEIGHT
            self._set_window(x0, y0, x0 + CELL_WIDTH - 1,
                             y0 + CELL_HEIGHT - 1)
            self._cmd(ST7789V_CMD_RAMWR)
            self.mcu_rs.update_digital_out(1,
                                           reqclock=BACKGROUND_PRIORITY_CLOCK)
            self._send(self.cells[row][col])
            self.remote_cells[row][col] = bytearray(self.cells[row][col])
        self.dirty.clear()
        return True

    def set_glyphs(self, glyphs):
        for glyph_name, glyph_data in glyphs.items():
            icon = glyph_data.get('icon16x16')
            if icon is not None:
                self.icons[glyph_name] = (
                    self._render_bitmap(icon[0]),
                    self._render_bitmap(icon[1]))

    def write_text(self, x, y, data):
        if x + len(data) > self.columns:
            data = data[:self.columns - min(x, self.columns)]
        for i, char in enumerate(bytearray(data)):
            if char >= len(font8x14.VGA_FONT):
                char = ord(' ')
            self._set_cell(y, x + i, self._render_bitmap(
                font8x14.VGA_FONT[char]))

    def write_graphics(self, x, y, data):
        if len(data) != CELL_HEIGHT:
            return
        self._set_cell(y, x, self._render_bitmap(data))

    def write_glyph(self, x, y, glyph_name):
        icon = self.icons.get(glyph_name)
        if icon is not None and x < self.columns - 1:
            self._set_cell(y, x, icon[0])
            self._set_cell(y, x + 1, icon[1])
            return 2
        char = TextGlyphs.get(glyph_name)
        if char is not None:
            self.write_text(x, y, char)
            return 1
        return 0

    def clear(self):
        for row in range(self.rows):
            for col in range(self.columns):
                self._set_cell(row, col, self.blank_cell)

    def get_dimensions(self):
        return self.columns, self.rows
