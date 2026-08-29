"""
LANForge UI Micro-Animation Engine
Smooth, low-CPU interpolation helpers, pulsing lights, floating toasts, sliding tab pills.
"""

import math
import customtkinter as ctk

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"

def lerp_color(color_a, color_b, t):
    """Linear interpolation between two hex colors (0.0 <= t <= 1.0)"""
    r1, g1, b1 = hex_to_rgb(color_a)
    r2, g2, b2 = hex_to_rgb(color_b)
    r = r1 + (r2 - r1) * t
    g = g1 + (g2 - g1) * t
    b = b1 + (b2 - b1) * t
    return rgb_to_hex((r, g, b))


class SlidingTabIndicator:
    """Animates a highlight pill sliding under the active tab buttons."""
    def __init__(self, parent_container, pill_widget):
        self.container = parent_container
        self.pill = pill_widget
        self.current_x = 4
        self.target_x = 4
        self.current_w = 82
        self.target_w = 82
        self.animating = False

    def slide_to(self, target_x, target_w):
        self.target_x = target_x
        self.target_w = target_w

        if not self.animating:
            self.animating = True
            self._step(0, 6, self.current_x, self.current_w)

    def _step(self, step_idx, total_steps, start_x, start_w):
        if step_idx <= total_steps:
            t = step_idx / total_steps
            ease = 1 - math.pow(1 - t, 3)
            new_x = int(start_x + (self.target_x - start_x) * ease)
            new_w = int(start_w + (self.target_w - start_w) * ease)

            self.pill.configure(width=new_w)
            self.pill.place_configure(x=new_x)
            self.current_x = new_x
            self.current_w = new_w
            self.container.after(16, lambda: self._step(step_idx + 1, total_steps, start_x, start_w))
        else:
            self.pill.configure(width=self.target_w)
            self.pill.place_configure(x=self.target_x)
            self.current_x = self.target_x
            self.current_w = self.target_w
            self.animating = False


class ToastNotification(ctk.CTkFrame):
    """Sleek floating brutalist toast notification that slides in from top."""
    def __init__(self, parent, text="Уведомление", toast_type="info", duration_ms=2500):
        accent_col = "#ff5500" if toast_type == "orange" else ("#22c55e" if toast_type == "green" else "#3b82f6")
        
        super().__init__(
            parent,
            fg_color="#18181c",
            corner_radius=8,
            border_width=1,
            border_color=accent_col
        )
        self.parent = parent
        self.duration_ms = duration_ms
        self.step = 0
        self.total_steps = 7
        self.current_y = -60
        self.target_y = 16

        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(padx=18, pady=10)

        icon = "●"
        ctk.CTkLabel(
            pad,
            text=icon,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=accent_col
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            pad,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left")

        self.place(relx=0.5, y=self.current_y, anchor="n")
        self._slide_in()

    def _slide_in(self):
        if self.step <= self.total_steps:
            t = self.step / self.total_steps
            ease = 1 - math.pow(1 - t, 3)
            y = self.current_y + (self.target_y - self.current_y) * ease
            self.place_configure(y=y)
            self.step += 1
            self.after(16, self._slide_in)
        else:
            self.after(self.duration_ms, self._slide_out)

    def _slide_out(self):
        self.step = 0
        self._animate_out()

    def _animate_out(self):
        if self.step <= self.total_steps:
            t = self.step / self.total_steps
            ease = math.pow(t, 2)
            y = self.target_y - (70 * ease)
            self.place_configure(y=y)
            self.step += 1
            self.after(16, self._animate_out)
        else:
            self.destroy()


class PulseDotController:
    """Smooth breathing pulse animation for status indicators."""
    def __init__(self, widget, color_on="#22c55e", color_off="#0d4a22", interval_ms=120):
        self.widget = widget
        self.color_on = color_on
        self.color_off = color_off
        self.interval_ms = interval_ms
        self.t = 0.0
        self.running = True
        self._tick()

    def _tick(self):
        if not self.running or not self.widget.winfo_exists():
            return

        factor = (math.sin(self.t) + 1.0) / 2.0
        current_color = lerp_color(self.color_off, self.color_on, factor)
        try:
            self.widget.configure(text_color=current_color)
        except Exception:
            return

        self.t += 0.25
        self.widget.after(self.interval_ms, self._tick)

    def stop(self):
        self.running = False


class RadarScannerAnimation:
    """Animated radar sweep status and scanning frames."""
    SCAN_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label_widget, base_text="Сканирование сети активно"):
        self.label_widget = label_widget
        self.base_text = base_text
        self.idx = 0
        self.running = True
        self._tick()

    def _tick(self):
        if not self.running or not self.label_widget.winfo_exists():
            return

        frame = self.SCAN_FRAMES[self.idx % len(self.SCAN_FRAMES)]
        try:
            self.label_widget.configure(text=f"{frame} {self.base_text}")
        except Exception:
            return

        self.idx += 1
        self.label_widget.after(140, self._tick)

    def stop(self):
        self.running = False
