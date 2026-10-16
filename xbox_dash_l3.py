"""Xbox Dash -> L3 helper.

Detecta dois empurres rapidos do analogico esquerdo para frente e simula o
clique do stick esquerdo (L3/LS) em um controle Xbox virtual (ViGEmBus).
"""
import json
import os
import subprocess
try:
    from i18n import T, detect_language
except Exception:
    T = lambda code, key, **kw: key
    def detect_language():
        return "pt"
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

APP_NAME = "XboxDashL3"
APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

try:
    import XInput
except Exception as e:
    XInput = None
    _XINPUT_ERR = str(e)
else:
    _XINPUT_ERR = None

try:
    from vgamepad import VX360Gamepad, XUSB_BUTTON
except Exception as e:
    VX360Gamepad = None
    XUSB_BUTTON = None
    _VGAMEPAD_ERR = str(e)
else:
    _VGAMEPAD_ERR = None


def config_defaults():
    return {
        "controller_index": 0,
        "interval_ms": 320,
        "threshold": 0.78,
        "hold_ms": 130,
        "l3_mode": "hold",
        "hysteresis": 0.22,
        "invert_y": False,
        "enabled": True,
        "use_hidhide": False,
        "push_count": 2,
        "trigger_button": "Nenhum",
        "trigger_button_count": 2,
        "delay_enabled": False,
        "delay_activate_ms": 0,
        "delay_deactivate_ms": 0,
        "language": detect_language(),
        "poll_ms": 8,
    }


def load_config():
    cfg = config_defaults()
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg.update({k: data[k] for k in cfg if k in data})
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


BTN_MAP = {
    "A": "XUSB_GAMEPAD_A",
    "B": "XUSB_GAMEPAD_B",
    "X": "XUSB_GAMEPAD_X",
    "Y": "XUSB_GAMEPAD_Y",
    "DPAD_UP": "XUSB_GAMEPAD_DPAD_UP",
    "DPAD_DOWN": "XUSB_GAMEPAD_DPAD_DOWN",
    "DPAD_LEFT": "XUSB_GAMEPAD_DPAD_LEFT",
    "DPAD_RIGHT": "XUSB_GAMEPAD_DPAD_RIGHT",
    "START": "XUSB_GAMEPAD_START",
    "BACK": "XUSB_GAMEPAD_BACK",
    "LEFT_SHOULDER": "XUSB_GAMEPAD_LEFT_SHOULDER",
    "RIGHT_SHOULDER": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "LEFT_THUMB": "XUSB_GAMEPAD_LEFT_THUMB",
    "RIGHT_THUMB": "XUSB_GAMEPAD_RIGHT_THUMB",
}


def f2i(v):
    v = max(-1.0, min(1.0, float(v)))
    if v >= 0:
        return int(v * 32767 + 0.5)
    return int(v * 32768 - 0.5)


def find_hidhide_cli():
    candidates = []
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            hh = os.path.join(base, "Nefarius Software Solutions", "HidHide")
            candidates.append(os.path.join(hh, "HidHideCLI.exe"))
            candidates.append(os.path.join(hh, "x64", "HidHideCLI.exe"))
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidates.append(os.path.join(p, "HidHideCLI.exe"))
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def run_hidhide(cli, *args, timeout=15):
    if not cli:
        return (1, "", "cli not found")
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except Exception as e:
        return 999, "", str(e)


class Engine:
    def __init__(self, cfg, status_cb=None):
        self.cfg = cfg
        self.status_cb = status_cb or (lambda s: None)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._vg = None
        self._connected_real = False
        self._lang = cfg.get("language", "pt")
        self._push_active = False
        self._last_push = None
        self._push_tap_count = 0
        self._push_hold_start = 0.0
        self._push_hold_triggered = False
        self._button_active = False
        self._button_tap_count = 0
        self._last_button_time = None
        self._activate_after = 0.0
        self._delay_deactivate = 0.0
        self._sprint_mode = False
        self._l3_mode = "hold"
        self._debug_state = "IDLE"
        self._hidhide_cli = find_hidhide_cli()
        self._hidhide_cloaked = False
        self._hidhide_paths = []
        self._hidhide_turned_on = False
        self._hidhide_last_cfg = False
        self._l3_pressed = False
        self._forced_until = 0.0
        self._dash_count = 0
        self.status = "Parado"

    def set_config(self, cfg):
        with self._lock:
            self.cfg = cfg
            self._lang = cfg.get("language", getattr(self, "_lang", "pt"))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._hidhide_uncloak()
        self._release_vg()

    def trigger_once(self):
        self._forced_until = time.perf_counter() + self.cfg.get("hold_ms", 130) / 1000.0

    def _status(self, s):
        self.status = s
        try:
            self.status_cb(s)
        except Exception:
            pass

    def _ensure_vg(self):
        if self._vg is not None:
            return self._vg
        if VX360Gamepad is None:
            raise RuntimeError(_VGAMEPAD_ERR or "vgamepad indisponivel")
        self._vg = VX360Gamepad()
        self._vg.left_joystick(0, 0)
        self._vg.right_joystick(0, 0)
        self._vg.left_trigger(0)
        self._vg.right_trigger(0)
        self._vg.update()
        return self._vg

    def _release_vg(self):
        vg = self._vg
        self._vg = None
        if vg is not None:
            try:
                vg.reset()
                vg.update()
            except Exception:
                pass

    def _hidhide_collect_paths(self):
        cli = self._hidhide_cli
        if not cli:
            return []
        exe = os.path.abspath(sys.executable)
        run_hidhide(cli, "--app-reg", exe)
        code, out, err = run_hidhide(cli, "--dev-gaming")
        if code != 0 or not out.strip():
            return []
        try:
            data = json.loads(out)
        except Exception:
            return []
        paths = set()
        containers = data if isinstance(data, list) else [data]
        for cont in containers:
            devices = cont.get("devices", []) if isinstance(cont, dict) else []
            for dev in devices:
                if not isinstance(dev, dict):
                    continue
                friendly = (" ".join(str(cont.get(k, "")) for k in ("friendlyName",)) + " " +
                            " ".join(str(dev.get(k, "")) for k in ("description", "vendor", "product"))).lower()
                is_xbox = (str(dev.get("vendor")).lower().find("0x45e") >= 0 or
                           "xbox" in friendly or "xinput" in friendly)
                if not is_xbox:
                    continue
                for key in ("deviceInstancePath", "baseContainerDeviceInstancePath", "xusbDeviceInstancePath"):
                    v = dev.get(key)
                    if v:
                        paths.add(v)
        return list(paths)

    def _hidhide_cloak(self, cfg):
        if not cfg.get("use_hidhide", False):
            return
        cli = self._hidhide_cli
        if not cli:
            self._status(T(self._lang, "hidhide_not_found"))
            return
        if self._hidhide_cloaked:
            return
        code, out, err = run_hidhide(cli, "--cloak-state")
        self._hidhide_turned_on = ("--cloak-off" in (out or ""))
        self._hidhide_paths = self._hidhide_collect_paths()
        if not self._hidhide_paths:
            self._status(T(self._lang, "hidhide_no_device"))
            return
        args = []
        for p in self._hidhide_paths:
            args += ["--dev-hide", p]
        args += ["--cloak-on"]
        code, out, err = run_hidhide(cli, *args)
        if code == 0:
            self._hidhide_cloaked = True
            self._hidhide_last_cfg = True
            self._status(T(self._lang, "hidhide_cloaked"))
        else:
            self._status(T(self._lang, "hidhide_error", msg=(err.strip() or out.strip())))

    def _hidhide_uncloak(self):
        cli = self._hidhide_cli
        if not cli or not self._hidhide_cloaked:
            return
        if self._hidhide_paths:
            args = []
            for p in self._hidhide_paths:
                args += ["--dev-unhide", p]
            run_hidhide(cli, *args)
        if self._hidhide_turned_on:
            run_hidhide(cli, "--cloak-off")
        self._hidhide_cloaked = False
        self._hidhide_paths = []
        self._hidhide_turned_on = False

    def _loop(self):
        self._status(T(self._lang, "starting"))
        with self._lock:
            cfg0 = dict(self.cfg)
        if cfg0.get("use_hidhide", False):
            self._hidhide_cloak(cfg0)
        try:
            vg = self._ensure_vg()
        except Exception as e:
            self._status(T(self._lang, "virtual_error", e=e))
            self._running = False
            self._hidhide_uncloak()
            return

        connected_at_least_once = False
        while self._running:
            with self._lock:
                cfg = dict(self.cfg)

            idx = int(cfg.get("controller_index", 0))
            idx = max(0, min(3, idx))
            poll = max(4, int(cfg.get("poll_ms", 8))) / 1000.0

            connected_list = XInput.get_connected() if XInput else []
            real_ok = bool(connected_list[idx]) if (XInput and idx < len(connected_list)) else False

            if not real_ok:
                if connected_at_least_once:
                    self._status(T(self._lang, "real_disconnected", idx=idx))
                else:
                    self._status(T(self._lang, "waiting_real", idx=idx))
                try:
                    vg.reset(); vg.update()
                except Exception:
                    pass
                time.sleep(0.25)
                continue
            connected_at_least_once = True

            try:
                st = XInput.get_state(idx)
            except Exception as e:
                self._status(T(self._lang, "reading_error", e=e))
                time.sleep(0.25)
                continue

            try:
                left_thumb = XInput.get_thumb_values(st)
                (lx, ly), (rx, ry) = left_thumb
                lt, rt = XInput.get_trigger_values(st)
                btns = XInput.get_button_values(st)
            except Exception:
                (lx, ly), (rx, ry) = ((0.0, 0.0), (0.0, 0.0))
                lt, rt = (0, 0)
                btns = {}

            invert = bool(cfg.get("invert_y", False))
            ly_det = -ly if invert else ly

            threshold = float(cfg.get("threshold", 0.78))
            hyst = float(cfg.get("hysteresis", 0.22))
            release_level = threshold - hyst

            enabled = bool(cfg.get("enabled", True))
            self._l3_mode = cfg.get("l3_mode", self._l3_mode)

            now = time.perf_counter()
            interval = float(cfg.get("interval_ms", 320)) / 1000.0
            delay_enabled = bool(cfg.get("delay_enabled", False))
            delay_activate = (float(cfg.get("delay_activate_ms", 0)) / 1000.0) if delay_enabled else 0.0
            self._delay_deactivate = (float(cfg.get("delay_deactivate_ms", 0)) / 1000.0) if delay_enabled else 0.0

            min_gap = 0.04
            button_mode = cfg.get("trigger_button", "Nenhum")
            button_is_axis = (button_mode in ("LT", "RT"))

            def button_pressed():
                if button_mode == "Nenhum":
                    return False
                if button_mode == "LT":
                    return lt >= 0.5
                if button_mode == "RT":
                    return rt >= 0.5
                key_map = {
                    "A": "A", "B": "B", "X": "X", "Y": "Y",
                    "LB": "LEFT_SHOULDER", "RB": "RIGHT_SHOULDER",
                    "L3 (LS)": "LEFT_THUMB", "R3 (RS)": "RIGHT_THUMB",
                    "Start": "START", "Back": "BACK",
                    "DPAD_UP": "DPAD_UP", "DPAD_DOWN": "DPAD_DOWN",
                    "DPAD_LEFT": "DPAD_LEFT", "DPAD_RIGHT": "DPAD_RIGHT",
                }
                return bool(btns.get(key_map.get(button_mode, button_mode), False))

            if enabled:
                self._l3_mode = cfg.get("l3_mode", self._l3_mode)
                l3_hold_mode = (self._l3_mode == "hold")

                if button_mode != "Nenhum":
                    btarget = max(1, min(4, int(cfg.get("trigger_button_count", 2))))
                    if self._last_button_time is not None and (now - self._last_button_time) > interval:
                        self._button_tap_count = 0
                        self._last_button_time = None
                    bpressed = button_pressed()
                    if bpressed and not self._button_active:
                        self._button_active = True
                        if self._last_button_time is None or (now - self._last_button_time) >= min_gap:
                            if (self._last_button_time is None or
                                    (now - self._last_button_time) <= interval):
                                self._button_tap_count += 1
                            else:
                                self._button_tap_count = 1
                            self._last_button_time = now
                            self._debug_state = f"BTN tap {self._button_tap_count}/{btarget}"
                            if self._button_tap_count >= btarget:
                                self._activate_after = now + delay_activate
                                self._forced_until = self._activate_after + float(cfg.get("hold_ms", 130)) / 1000.0
                                self._dash_count += 1
                                self._sprint_mode = l3_hold_mode
                                self._button_tap_count = 0
                                self._last_button_time = None
                                self._debug_state = "BTN OK -> L3"
                    elif not bpressed:
                        self._button_active = False
                        if l3_hold_mode and self._sprint_mode and bpressed is False:
                            pass
                    if l3_hold_mode and self._sprint_mode and (bpressed or ly_det >= release_level):
                        self._forced_until = max(self._forced_until, now + 0.06)
                    if not bpressed and self._sprint_mode:
                        if ly_det < max(0.0, release_level - 0.1) and not bpressed:
                            if self._delay_deactivate > 0:
                                self._forced_until = max(self._forced_until, now + self._delay_deactivate)
                            self._sprint_mode = False
                else:
                    ptarget = int(cfg.get("push_count", 2))
                    ptarget = max(0, min(4, ptarget))
                    if ptarget == 0:
                        if ly_det >= threshold:
                            if not self._push_active:
                                self._push_active = True
                                self._push_hold_start = now
                                self._push_hold_triggered = False
                            if (self._push_active and (not self._push_hold_triggered) and
                                    (now - getattr(self, "_push_hold_start", now)) >= 0.15):
                                self._activate_after = now + delay_activate
                                self._forced_until = self._activate_after + float(cfg.get("hold_ms", 130)) / 1000.0
                                self._dash_count += 1
                                self._push_hold_triggered = True
                                self._sprint_mode = l3_hold_mode
                                self._debug_state = "HOLD -> L3"
                            if l3_hold_mode and self._sprint_mode and ly_det >= release_level:
                                self._forced_until = max(self._forced_until, now + 0.06)
                        else:
                            self._push_active = False
                            self._push_hold_triggered = False
                            if self._sprint_mode and ly_det < max(0.0, release_level - 0.1):
                                if self._delay_deactivate > 0:
                                    self._forced_until = max(self._forced_until, now + self._delay_deactivate)
                                self._sprint_mode = False
                            self._debug_state = "SOLTOU" if ly_det < release_level else "NEUTRO"
                    else:
                        if self._last_push is not None and (now - self._last_push) > interval:
                            self._push_tap_count = 0
                            self._last_push = None
                        rising = ly_det >= threshold and not self._push_active
                        if rising:
                            self._push_active = True
                            if self._last_push is None or (now - self._last_push) >= min_gap:
                                if (self._last_push is None or (now - self._last_push) <= interval):
                                    self._push_tap_count = (self._push_tap_count or 0) + 1
                                else:
                                    self._push_tap_count = 1
                                self._last_push = now
                                self._debug_state = f"PUSH {self._push_tap_count}/{ptarget}"
                                if self._push_tap_count >= ptarget:
                                    self._activate_after = now + delay_activate
                                    self._forced_until = self._activate_after + float(cfg.get("hold_ms", 130)) / 1000.0
                                    self._dash_count += 1
                                    self._sprint_mode = l3_hold_mode
                                    self._push_tap_count = 0
                                    self._last_push = None
                                    self._debug_state = "PUSH OK -> L3"
                        elif ly_det < release_level:
                            self._push_active = False
                            self._push_tap_count = self._push_tap_count if (self._last_push is not None and
                                                                           (now - (self._last_push or now)) <= interval) else 0
                            if self._sprint_mode and ly_det < max(0.0, release_level - 0.1):
                                if self._delay_deactivate > 0:
                                    self._forced_until = max(self._forced_until, now + self._delay_deactivate)
                                self._sprint_mode = False
                            self._debug_state = "SOLTOU"
                        else:
                            if self._sprint_mode:
                                self._debug_state = "SEGURANDO (sprint)"
                            elif self._push_active:
                                self._debug_state = "SEGURANDO (push)"
                            else:
                                self._debug_state = "NEUTRO"
                        if self._sprint_mode and ly_det >= release_level:
                            self._forced_until = max(self._forced_until, now + 0.06)

                if self._sprint_mode and ly_det < max(0.0, release_level - 0.1) and button_mode == "Nenhum":
                    if ly_det < max(0.0, release_level - 0.1):
                        pass

            forced = self._activate_after <= now < self._forced_until
            self._l3_pressed = bool(forced)

            try:
                vg.left_joystick(f2i(lx), f2i(ly))
                vg.right_joystick(f2i(rx), f2i(ry))
                vg.left_trigger(int(max(0, min(1, lt)) * 255 + 0.5))
                vg.right_trigger(int(max(0, min(1, rt)) * 255 + 0.5))

                for xname, xusb_name in BTN_MAP.items():
                    pressed = bool(btns.get(xname, False))
                    xbtn = getattr(XUSB_BUTTON, xusb_name)
                    if pressed:
                        vg.press_button(xbtn)
                    else:
                        vg.release_button(xbtn)

                if forced:
                    vg.press_button(XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
                elif not btns.get("LEFT_THUMB", False):
                    pass
                vg.update()
            except Exception as e:
                self._status(T(self._lang, "error_virtual", e=e))
                time.sleep(0.1)
                continue

            if self._sprint_mode and forced:
                self._status(f"Ativo – CORRENDO L3 (#{self._dash_count}) [{self._debug_state}] ly={ly_det:+.2f}")
            elif forced:
                self._status(f"Ativo – DASH L3 (#{self._dash_count}) [{self._debug_state}] ly={ly_det:+.2f}")
            else:
                self._status(f"Ativo – slot {idx} [{self._debug_state}] ly={ly_det:+.2f}")

            time.sleep(poll)

        self._status(T(self._lang, "stopped"))
        self._release_vg()


def list_controllers(lang="pt"):
    """Retorna lista de (index, descricao) para XInput."""
    out = []
    if XInput is None:
        return out
    try:
        connected = XInput.get_connected()
    except Exception:
        return out
    for i in range(4):
        ok = bool(connected[i]) if i < len(connected) else False
        if not ok:
            out.append((i, f"Slot {i} – {T(lang, 'conn_disconnected')}"))
            continue
        desc = f"Slot {i} – {T(lang, 'conn_connected')}"
        try:
            bt = XInput.get_battery_information(i) if hasattr(XInput, "get_battery_information") else None
        except Exception:
            bt = None
        if bt is not None:
            try:
                btype = bt[0] if isinstance(bt, tuple) else getattr(bt, "BatteryType", None)
                wired = str(btype).upper().find("WIRED") >= 0
                if wired:
                    desc += f" {T(lang, 'usb_cable')}"
                else:
                    desc += f" {T(lang, 'wireless')}"
            except Exception:
                pass
        out.append((i, desc))
    return out


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.lang_code = self.cfg.get("language", detect_language())
        self.root.title(T(self.lang_code, "app_title"))
        self.root.geometry("460x1000")
        self.root.resizable(False, False)
        try:
            self.root.attributes("-alpha", 0.95)
        except Exception:
            pass
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            ico = os.path.join(base, "app.ico")
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass
        self.jp_font = self._pick_jp_font()
        self.cfg = load_config()
        self.lang_code = self.cfg.get("language", detect_language())
        self.engine = Engine(self.cfg, status_cb=self._status_threadsafe)
        self._status_var = tk.StringVar(value=T(self.lang_code, "initial_status"))
        self._apply_dark_gold_theme()

        if XInput is None or VX360Gamepad is None:
            msg = T(self.lang_code, "dependency_bad")
            if XInput is None:
                msg += f" - XInput-Python: {_XINPUT_ERR}\n"
            if VX360Gamepad is None:
                msg += f" - vgamepad/ViGEm: {_VGAMEPAD_ERR}\n"
            msg += "\n" + T(self.lang_code, "deps_prompt")
            messagebox.showerror(T(self.lang_code, "deps_title"), msg)

        self._build_ui()
        self._refresh_controllers()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_status()

    def _pick_jp_font(self):
        available = {f.lower(): f for f in tkfont.families(self.root)}
        candidates = ["Yu Mincho", "MS PMincho", "HGSMinchoE", "MS Mincho", "Yu Gothic", "Meiryo", "Segoe UI"]
        for c in candidates:
            if c.lower() in available:
                return available[c.lower()]
        return "Segoe UI"

    def _apply_dark_gold_theme(self):
        GOLD = "#D4AF37"
        GOLD_BRIGHT = "#FFD700"
        BLACK = "#1F170D"
        PANEL = "#2A2012"
        DEEP = "#332716"
        self.root.configure(bg=BLACK)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=BLACK, foreground=GOLD, font=(self.jp_font, 9))
        style.configure("TFrame", background=BLACK)
        style.configure("TLabel", background=BLACK, foreground=GOLD, font=(self.jp_font, 9))
        style.configure("TButton", background=DEEP, foreground=GOLD_BRIGHT, bordercolor=GOLD,
                        focusthickness=0, padding=(10, 6), font=(self.jp_font, 9, "bold"))
        style.map("TButton", background=[("active", "#2A220F"), ("pressed", "#3A3015")],
                  foreground=[("active", GOLD_BRIGHT)])
        style.configure("TCheckbutton", background=BLACK, foreground=GOLD, font=(self.jp_font, 9))
        style.map("TCheckbutton", background=[("active", BLACK)], foreground=[("active", GOLD_BRIGHT)])
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=GOLD_BRIGHT,
                        bordercolor=GOLD, arrowcolor=GOLD_BRIGHT, padding=4, font=(self.jp_font, 9))
        style.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", GOLD_BRIGHT)])
        style.configure("TScale", background=BLACK, troughcolor=PANEL, sliderlength=18, sliderrelief="flat")
        style.map("TScale", background=[("active", GOLD)], sliderrelief=[("active", "flat")])
        style.configure("TSeparator", background=GOLD)
        style.configure("Horizontal.TScale", background=BLACK)
        self.root.option_add("*TCombobox*Listbox*Background", PANEL)
        self.root.option_add("*TCombobox*Listbox*Foreground", GOLD_BRIGHT)
        self.root.option_add("*TCombobox*Listbox*selectBackground", GOLD)
        self.root.option_add("*TCombobox*Listbox*selectForeground", BLACK)

    def _build_ui(self):
        pad = 8
        hdr = ttk.Label(self.root, text="ONIDASH  L3", font=(self.jp_font, 18, "bold"), anchor="center", foreground="#FFD700")
        hdr.pack(fill="x", pady=(10, 2))
        frm = ttk.Frame(self.root, padding=pad)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=T(self.lang_code, "controllers_label")).grid(row=0, column=0, sticky="w")
        LANG_CODES = ["pt", "en", "es"]
        LANG_NAMES = [T(self.lang_code, f"lang_{c}") for c in LANG_CODES]
        ttk.Label(frm, text=T(self.lang_code, "language_label")).grid(row=33, column=0, sticky="w", pady=(8, 0))
        self.lang_var = tk.StringVar(value=LANG_NAMES[LANG_CODES.index(self.lang_code)] if self.lang_code in LANG_CODES else LANG_NAMES[0])
        self.lang_combo = ttk.Combobox(frm, textvariable=self.lang_var, state="readonly", values=LANG_NAMES, width=18)
        self.lang_combo.grid(row=33, column=1, sticky="e", pady=(8, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_cfg())
        self.ctrl_var = tk.StringVar()
        self.ctrl_combo = ttk.Combobox(frm, textvariable=self.ctrl_var, state="readonly", width=42)
        self.ctrl_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        btnrow = ttk.Frame(frm)
        btnrow.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(btnrow, text=T(self.lang_code, "refresh"), command=self._refresh_controllers).pack(side="left")
        ttk.Button(btnrow, text=T(self.lang_code, "test_ls"), command=self._test_ls).pack(side="right")

        self.enabled_var = tk.BooleanVar(value=bool(self.cfg.get("enabled", True)))
        cb = ttk.Checkbutton(frm, text=T(self.lang_code, "enable"), variable=self.enabled_var,
                             command=self._apply_cfg)
        cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(frm, text=T(self.lang_code, "interval_label")).grid(row=4, column=0, sticky="w")
        self.interval_var = tk.IntVar(value=int(self.cfg.get("interval_ms", 320)))
        sc = ttk.Scale(frm, from_=150, to=900, orient="horizontal", variable=self.interval_var, command=lambda _=None: self._apply_cfg())
        sc.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        self.interval_lbl = ttk.Label(frm, text=f"{self.interval_var.get()} ms")
        self.interval_lbl.grid(row=6, column=0, sticky="w")

        ttk.Label(frm, text=T(self.lang_code, "threshold_label")).grid(row=7, column=0, sticky="w", pady=(6, 0))
        self.thr_var = tk.DoubleVar(value=float(self.cfg.get("threshold", 0.72)))
        ttk.Scale(frm, from_=0.3, to=0.95, orient="horizontal", variable=self.thr_var, command=lambda _=None: self._apply_cfg()).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        self.thr_lbl = ttk.Label(frm, text=f"{self.thr_var.get():.2f}")
        self.thr_lbl.grid(row=9, column=0, sticky="w")

        ttk.Label(frm, text=T(self.lang_code, "hold_label")).grid(row=10, column=0, sticky="w", pady=(6, 0))
        self.hold_var = tk.IntVar(value=int(self.cfg.get("hold_ms", 130)))
        ttk.Scale(frm, from_=60, to=300, orient="horizontal", variable=self.hold_var, command=lambda _=None: self._apply_cfg()).grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 2))
        self.hold_lbl = ttk.Label(frm, text=f"{self.hold_var.get()} ms")
        self.hold_lbl.grid(row=12, column=0, sticky="w")

        self.invert_var = tk.BooleanVar(value=bool(self.cfg.get("invert_y", False)))
        ttk.Checkbutton(frm, text=T(self.lang_code, "invert"), variable=self.invert_var,
                        command=self._apply_cfg).grid(row=13, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Separator(frm, orient="horizontal").grid(row=14, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(frm, text=T(self.lang_code, "status")).grid(row=15, column=0, sticky="w")
        ttk.Label(frm, textvariable=self._status_var, foreground="#1a7f37").grid(row=16, column=0, columnspan=2, sticky="w")

        note = ttk.Label(frm, text=T(self.lang_code, "hint_game"),
                         foreground="#D4AF37", justify="left")
        note.grid(row=17, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Label(frm, text=T(self.lang_code, "ls_indicator")).grid(row=18, column=0, sticky="w", pady=(8, 0))
        self.l3_indicator = tk.Label(frm, text=T(self.lang_code, "ls_released"), bg="#d1242f", fg="white", width=14, relief="groove", font=(self.jp_font, 9, "bold"))
        self.l3_indicator.grid(row=18, column=1, sticky="e", pady=(8, 0))

        ttk.Label(frm, text=T(self.lang_code, "mode_label")).grid(row=19, column=0, sticky="w", pady=(8, 0))
        self.l3mode_var = tk.StringVar()
        initial_mode = T(self.lang_code, "mode_hold") if str(self.cfg.get("l3_mode", "hold")).lower().startswith("h") else T(self.lang_code, "mode_tap")
        self.l3mode_var.set(initial_mode)
        self.l3mode_combo = ttk.Combobox(frm, textvariable=self.l3mode_var, state="readonly", values=[T(self.lang_code, "mode_hold"), T(self.lang_code, "mode_tap")], width=18)
        self.l3mode_combo.grid(row=19, column=1, sticky="e", pady=(8, 0))
        self.l3mode_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_cfg())

        self.hidhide_var = tk.BooleanVar(value=bool(self.cfg.get("use_hidhide", False)))
        cb_hh = ttk.Checkbutton(frm, text=T(self.lang_code, "hidhide_check"), variable=self.hidhide_var,
                                command=self._apply_cfg)
        cb_hh.grid(row=20, column=0, columnspan=2, sticky="w", pady=(8, 0))
        cli = find_hidhide_cli()
        status_txt = (T(self.lang_code, "hidhide_found") if cli else T(self.lang_code, "hidhide_missing"))
        self.hidhide_status = ttk.Label(frm, text=status_txt, foreground=("#1a7f37" if cli else "#d1242f"), font=(self.jp_font, 8))
        self.hidhide_status.grid(row=21, column=0, columnspan=2, sticky="w")
        note_hh = ttk.Label(frm, text=T(self.lang_code, "hidhide_reconnect"),
                            foreground="#D4AF37", font=(self.jp_font, 8))
        note_hh.grid(row=22, column=0, columnspan=2, sticky="w")

        ttk.Label(frm, text=T(self.lang_code, "trigger_push_label")).grid(row=23, column=0, columnspan=2, sticky="w", pady=(8, 0))
        pcfg = max(0, min(4, int(self.cfg.get("push_count", 2))))
        self.push_count_var = tk.IntVar(value=pcfg)
        self.push_count_scale = ttk.Scale(frm, from_=0, to=4, orient="horizontal", variable=self.push_count_var,
                                         command=lambda _: self._apply_cfg())
        self.push_count_scale.grid(row=24, column=0, columnspan=2, sticky="ew", pady=(0, 0))
        self.push_count_lbl = ttk.Label(frm, text=f"{pcfg}")
        self.push_count_lbl.grid(row=24, column=2, sticky="e")

        ttk.Label(frm, text=T(self.lang_code, "trigger_button_label")).grid(row=25, column=0, sticky="w", pady=(6, 0))
        _bt = str(self.cfg.get("trigger_button", "Nenhum"))
        self.button_trigger_var = tk.StringVar(value=(T(self.lang_code, "none") if _bt == "Nenhum" else _bt))
        button_options = [T(self.lang_code, "none"), "A", "B", "X", "Y", "LB", "RB", "LT", "RT", "L3 (LS)", "R3 (RS)", "Start", "Back",
                          "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"]
        if self.button_trigger_var.get() not in button_options:
            self.button_trigger_var.set("Nenhum")
        self.button_trigger_combo = ttk.Combobox(frm, textvariable=self.button_trigger_var, state="readonly",
                                                 values=button_options, width=18)
        self.button_trigger_combo.grid(row=25, column=1, sticky="e", pady=(6, 0))
        self.button_trigger_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_cfg())

        ttk.Label(frm, text=T(self.lang_code, "button_count_label")).grid(row=26, column=0, columnspan=2, sticky="w", pady=(6, 0))
        bcfg = max(1, min(4, int(self.cfg.get("trigger_button_count", 2))))
        self.button_count_var = tk.IntVar(value=bcfg)
        self.button_count_scale = ttk.Scale(frm, from_=1, to=4, orient="horizontal", variable=self.button_count_var,
                                           command=lambda _: self._apply_cfg())
        self.button_count_scale.grid(row=27, column=0, columnspan=2, sticky="ew")
        self.button_count_lbl = ttk.Label(frm, text=f"{bcfg}")
        self.button_count_lbl.grid(row=27, column=2, sticky="e")

        self.delay_enabled_var = tk.BooleanVar(value=bool(self.cfg.get("delay_enabled", False)))
        ttk.Checkbutton(frm, text=T(self.lang_code, "delay_enabled"), variable=self.delay_enabled_var,
                        command=self._apply_cfg).grid(row=28, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(frm, text=T(self.lang_code, "delay_activate")).grid(row=29, column=0, columnspan=2, sticky="w", pady=(6, 0))
        actv = max(0, min(1000, int(self.cfg.get("delay_activate_ms", 0))))
        self.delay_act_var = tk.IntVar(value=actv)
        self.delay_act_scale = ttk.Scale(frm, from_=0, to=1000, orient="horizontal", variable=self.delay_act_var,
                                        command=lambda _: self._apply_cfg())
        self.delay_act_scale.grid(row=30, column=0, columnspan=2, sticky="ew")
        self.delay_act_lbl = ttk.Label(frm, text=f"{actv} ms")
        self.delay_act_lbl.grid(row=30, column=2, sticky="e")
        ttk.Label(frm, text=T(self.lang_code, "delay_deactivate")).grid(row=31, column=0, columnspan=2, sticky="w", pady=(6, 0))
        deactv = max(0, min(1000, int(self.cfg.get("delay_deactivate_ms", 0))))
        self.delay_deact_var = tk.IntVar(value=deactv)
        self.delay_deact_scale = ttk.Scale(frm, from_=0, to=1000, orient="horizontal", variable=self.delay_deact_var,
                                          command=lambda _: self._apply_cfg())
        self.delay_deact_scale.grid(row=32, column=0, columnspan=2, sticky="ew")
        self.delay_deact_lbl = ttk.Label(frm, text=f"{deactv} ms")
        self.delay_deact_lbl.grid(row=32, column=2, sticky="e")

        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        self.ctrl_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_cfg())

    def _refresh_controllers(self):
        items = list_controllers()
        labels = [d for (_, d) in items]
        self.ctrl_combo["values"] = labels
        saved = int(self.cfg.get("controller_index", 0))
        if 0 <= saved < len(labels):
            self.ctrl_combo.current(saved)
        else:
            if labels:
                self.ctrl_combo.current(0)
        self._apply_cfg()

    def _selected_index(self):
        i = self.ctrl_combo.current()
        if i is None or i < 0:
            i = int(self.cfg.get("controller_index", 0))
        return max(0, min(3, i))

    def _apply_cfg(self):
        self.interval_lbl.config(text=f"{self.interval_var.get()} ms")
        self.thr_lbl.config(text=f"{self.thr_var.get():.2f}")
        self.hold_lbl.config(text=f"{self.hold_var.get()} ms")

        cfg = {
            "controller_index": self._selected_index(),
            "interval_ms": int(self.interval_var.get()),
            "threshold": float(self.thr_var.get()),
            "hold_ms": int(self.hold_var.get()),
            "hysteresis": float(self.cfg.get("hysteresis", 0.22)),
            "invert_y": bool(self.invert_var.get()),
            "enabled": bool(self.enabled_var.get()),
            "poll_ms": int(self.cfg.get("poll_ms", 8)),
            "l3_mode": "hold" if "hold" in str(self.l3mode_var.get()).lower() else "tap",
            "use_hidhide": bool(self.hidhide_var.get()),
            "push_count": int(self.push_count_var.get()),
            "trigger_button": ("Nenhum" if str(self.button_trigger_var.get()) in (T(self.lang_code, "none"), "None", "Ninguno", "Nenhum") else str(self.button_trigger_var.get())),
            "trigger_button_count": int(self.button_count_var.get()),
            "delay_enabled": bool(self.delay_enabled_var.get()),
            "delay_activate_ms": int(self.delay_act_var.get()),
            "delay_deactivate_ms": int(self.delay_deact_var.get()),
            "language": (["pt", "en", "es"][self.lang_combo.current()] if self.lang_combo.current() >= 0 else self.lang_code),
        }
        self.push_count_lbl.config(text=str(self.push_count_var.get()))
        self.button_count_lbl.config(text=str(self.button_count_var.get()))
        self.delay_act_lbl.config(text=f"{self.delay_act_var.get()} ms")
        self.delay_deact_lbl.config(text=f"{self.delay_deact_var.get()} ms")
        new_lang = cfg.get("language", self.lang_code)
        self.cfg = cfg
        save_config(cfg)
        self.engine.set_config(cfg)
        if new_lang != self.lang_code:
            self.lang_code = new_lang
            for _w in self.root.winfo_children():
                _w.destroy()
            self._build_ui()
            self._refresh_controllers()
            self._status_var.set("")

    def _test_ls(self):
        self.engine.trigger_once()

    def _status_threadsafe(self, s):
        self.root.after(0, lambda: self._status_var.set(s))

    def _poll_status(self):
        try:
            pressed = bool(getattr(self.engine, "_l3_pressed", False))
            if pressed:
                self.l3_indicator.config(text=T(self.lang_code, "ls_pressed"), bg="#1a7f37")
            else:
                self.l3_indicator.config(text=T(self.lang_code, "ls_released"), bg="#d1242f")
        except Exception:
            pass
        self.root.after(50, self._poll_status)

    def run(self):
        self.engine.start()
        self.root.mainloop()

    def _on_close(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
