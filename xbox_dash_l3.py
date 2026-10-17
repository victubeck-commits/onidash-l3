import os
import sys
import json
import subprocess
import locale
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, font as tkfont
import XInput
import vgamepad as vg

try:
    from i18n import T, detect_language
except Exception:
    def detect_language():
        return "pt"
    def T(code, key, **kw):
        return key

APP_NAME = "OniDash L3"
APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

GOLD = "#D8F35B"
LIGHT = "#F5F7FA"
TEXT = "#D9E2F2"
MUTED = "#94A3B8"
BG = "#11161D"
PANEL = "#181D27"
CARD = "#1F2631"
BORDER = "#2B3444"
DANGER = "#F87171"

BUTTON_INPUTS = ["A", "B", "X", "Y", "LB", "RB", "LS", "RS", "START", "BACK", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"]
AXIS_INPUTS = ["LS_UP", "LS_DOWN", "LS_LEFT", "LS_RIGHT", "RS_UP", "RS_DOWN", "RS_LEFT", "RS_RIGHT"]
TRIGGER_INPUTS = ["LT", "RT"]
ANALOG_INPUTS = AXIS_INPUTS + TRIGGER_INPUTS
ALL_INPUTS = BUTTON_INPUTS + ANALOG_INPUTS

INPUT_LABELS = {
    "A": "A", "B": "B", "X": "X", "Y": "Y", "LB": "LB", "RB": "RB",
    "LS": "LS / L3", "RS": "RS / R3", "START": "Start (Menu)", "BACK": "Back (View)",
    "DPAD_UP": "D-Pad \u2191", "DPAD_DOWN": "D-Pad \u2193", "DPAD_LEFT": "D-Pad \u2190", "DPAD_RIGHT": "D-Pad \u2192",
    "LS_UP": "LS \u2191", "LS_DOWN": "LS \u2193", "LS_LEFT": "LS \u2190", "LS_RIGHT": "LS \u2192",
    "RS_UP": "RS \u2191", "RS_DOWN": "RS \u2193", "RS_LEFT": "RS \u2190", "RS_RIGHT": "RS \u2192",
    "LT": "LT", "RT": "RT",
}

ACTION_TARGETS = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "LS", "RS", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "START", "BACK"]
ACTION_LABELS = {k: INPUT_LABELS.get(k, k) for k in ACTION_TARGETS}

XINPUT_BUTTON_NAMES = {
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "LB": "LEFT_SHOULDER", "RB": "RIGHT_SHOULDER",
    "LS": "LEFT_THUMB", "RS": "RIGHT_THUMB",
    "START": "START", "BACK": "BACK",
    "DPAD_UP": "DPAD_UP", "DPAD_DOWN": "DPAD_DOWN", "DPAD_LEFT": "DPAD_LEFT", "DPAD_RIGHT": "DPAD_RIGHT",
}

BUTTON_MAP = {
    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}
def config_defaults(lang=None):
    if lang is None:
        loc = locale.getdefaultlocale()[0] or "pt"
        lang = "es" if loc.startswith("es") else "en" if loc.startswith("en") else "pt"
    return {
        "language": lang,
        "controller_index": -1,
        "virtual_controller": True,
        "hidhide": False,
        "startup": False,
        "profile_name": "Default",
        "profiles": [{"name": "Default", "description": "Default profile", "mappings": []}],
        "analog": {
            "left": {"deadzone": 0.08, "sensitivity": 1.0, "curve": 1.0, "invert_x": False, "invert_y": False, "threshold": 0.78, "hysteresis": 0.22},
            "right": {"deadzone": 0.08, "sensitivity": 1.0, "curve": 1.0, "invert_x": False, "invert_y": False, "threshold": 0.78, "hysteresis": 0.22},
        },
        "triggers": {
            "left": {"deadzone": 0.05, "sensitivity": 1.0, "invert": False},
            "right": {"deadzone": 0.05, "sensitivity": 1.0, "invert": False},
        },
        "mappings": [],
        "legacy": {},
        "poll_ms": 8,
    }


def load_config():
    defaults = config_defaults()
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _deep_update(defaults, data)
            migrate(defaults)
    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _deep_update(a, b):
    """Merge b into a in place: dicts merge recursively, everything else replaces."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _deep_update(a[k], v)
        else:
            a[k] = v


def default_mapping():
    return {
        "id": 0,
        "enabled": True,
        "name": "",
        "input": "A",
        "modifier": "",
        "condition": {"type": "direct", "count": 2, "interval_ms": 320, "threshold": 0.78},
        "mode": "hold",
        "action": "B",
        "tap_ms": 80,
        "repeat": {"count": 3, "interval_ms": 300, "press_ms": 60, "continuous": False},
        "delay": {"enabled": False, "activate_ms": 0, "deactivate_ms": 0},
        "hold_while_moving": False,
    }


OLD_BUTTON_ALIASES = {"L3": "LS", "R3": "RS", "Start": "START", "Back": "BACK"}


def normalize_mapping(m):
    """Convert old-format mappings to the current format and fill missing fields."""
    if not isinstance(m, dict):
        m = {}
    d = default_mapping()
    if "condition" in m and isinstance(m.get("action"), str):
        out = dict(d)
        for k, v in m.items():
            if k not in ("condition", "repeat", "delay"):
                out[k] = v
        out["condition"] = {**d["condition"], **(m.get("condition") or {})}
        out["repeat"] = {**d["repeat"], **(m.get("repeat") or {})}
        out["delay"] = {**d["delay"], **(m.get("delay") or {})}
        if out.get("input") not in ALL_INPUTS:
            out["input"] = "A"
        if out.get("action") not in ACTION_TARGETS:
            out["action"] = "B"
        if out.get("mode") not in ("hold", "tap", "toggle", "repeat", "threshold"):
            out["mode"] = "hold"
        return out
    # ----- old format conversion -----
    inp = m.get("input", "A")
    if inp == "left_stick_forward":
        inp = "LS_UP"
    elif inp == "button":
        inp = m.get("button", "A")
    inp = OLD_BUTTON_ALIASES.get(inp, inp)
    if inp not in ALL_INPUTS:
        inp = "A"
    trig = m.get("trigger") or {}
    act = m.get("action") if isinstance(m.get("action"), dict) else {}
    mode = act.get("mode", "hold")
    if mode not in ("hold", "tap", "toggle", "repeat", "threshold"):
        mode = "hold"
    target = act.get("target", "LS")
    if target not in ACTION_TARGETS:
        target = "LS"
    ctype = "direct"
    count = 2
    interval = 320
    ttype = trig.get("type", "tap")
    try:
        thr = float(trig.get("threshold", 0.78) or 0.78)
    except Exception:
        thr = 0.78
    if ttype == "threshold":
        ctype = "threshold"
    elif ttype == "tap":
        try:
            cnt = int(trig.get("tap_count", 2) or 2)
        except Exception:
            cnt = 2
        if cnt >= 2:
            ctype = "sequence"
            count = min(5, cnt)
            try:
                interval = int(trig.get("interval_ms", 320) or 320)
            except Exception:
                interval = 320
    try:
        press = int(trig.get("hold_ms", 130) or 130)
    except Exception:
        press = 130
    try:
        rep_interval = int(trig.get("interval_ms", 300) or 300)
    except Exception:
        rep_interval = 300
    rep_interval = max(40, rep_interval)
    press = max(20, min(press, rep_interval - 10))
    return {
        "id": m.get("id", 0),
        "enabled": bool(m.get("enabled", True)),
        "name": m.get("name", ""),
        "input": inp,
        "modifier": "",
        "condition": {"type": ctype, "count": count, "interval_ms": interval, "threshold": max(0.05, min(0.98, thr))},
        "mode": mode,
        "action": target,
        "tap_ms": max(20, press),
        "repeat": {"count": 3, "interval_ms": rep_interval, "press_ms": press, "continuous": False},
        "delay": {
            "enabled": bool(trig.get("delay_enabled", False)),
            "activate_ms": int(trig.get("delay_activate_ms", 0) or 0),
            "deactivate_ms": int(trig.get("delay_deactivate_ms", 0) or 0),
        },
        "hold_while_moving": False,
    }
def migrate(cfg):
    legacy = cfg.get("legacy", {})
    # Preserve old L3 settings into mappings if no mappings yet.
    if not cfg.get("mappings"):
        old = {}
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    old = json.load(f)
        except Exception:
            old = {}
        if old.get("push_count") is not None or old.get("trigger_button") is not None:
            mapping = {
                "id": 1,
                "enabled": bool(old.get("enabled", True)),
                "name": "Double tap to run",
                "input": "left_stick_forward",
                "trigger": {
                    "type": "tap" if int(old.get("push_count", 2)) > 0 else "hold",
                    "tap_count": int(old.get("push_count", 2)) if int(old.get("push_count", 2)) > 0 else 1,
                    "interval_ms": int(old.get("interval_ms", 320)),
                    "threshold": float(old.get("threshold", 0.78)),
                    "hold_ms": int(old.get("hold_ms", 130)),
                    "delay_activate_ms": int(old.get("delay_activate_ms", 0)),
                    "delay_deactivate_ms": int(old.get("delay_deactivate_ms", 0)),
                    "delay_enabled": bool(old.get("delay_enabled", False)),
                },
                "action": {"type": "button", "target": "LS", "mode": old.get("l3_mode", "hold")},
                "button": old.get("trigger_button", "None"),
                "button_count": int(old.get("trigger_button_count", 2)),
            }
            cfg["mappings"].append(mapping)
            cfg["legacy"] = old
    # Normalize profiles
    if not cfg.get("profiles"):
        cfg["profiles"] = [{"name": cfg.get("profile_name", "Default"), "description": "", "mappings": list(cfg.get("mappings", []))}]
    names = [p.get("name") for p in cfg["profiles"]]
    if cfg.get("profile_name") not in names:
        cfg["profile_name"] = names[0] if names else "Default"
    # Normalize all mappings to the current format
    cfg["mappings"] = [normalize_mapping(m) for m in cfg.get("mappings", [])]
    for p in cfg["profiles"]:
        p["mappings"] = [normalize_mapping(m) for m in p.get("mappings", [])]
    # If the active profile is empty but top-level mappings exist, mirror them
    active = None
    for p in cfg["profiles"]:
        if p.get("name") == cfg.get("profile_name"):
            active = p
            break
    if active is None and cfg["profiles"]:
        active = cfg["profiles"][0]
        cfg["profile_name"] = active.get("name", "Default")
    if active is not None and not active.get("mappings") and cfg["mappings"]:
        active["mappings"] = [json.loads(json.dumps(m)) for m in cfg["mappings"]]
    # Ensure unique ids within each profile
    for p in cfg["profiles"]:
        seen = set()
        for m in p.get("mappings", []):
            mid = m.get("id")
            if not mid or mid in seen:
                nid = 1
                while nid in seen:
                    nid += 1
                m["id"] = nid
            seen.add(m["id"])


def input_state(key, vals):
    """Return (value, is_analog) for a physical input key given controller values."""
    if key in BUTTON_INPUTS:
        return (1.0 if vals.get("buttons", {}).get(key) else 0.0, False)
    if key == "LT":
        return (float(vals.get("lt", 0.0)), True)
    if key == "RT":
        return (float(vals.get("rt", 0.0)), True)
    lx = float(vals.get("lx", 0.0))
    ly = float(vals.get("ly", 0.0))
    rx = float(vals.get("rx", 0.0))
    ry = float(vals.get("ry", 0.0))
    if key == "LS_UP":
        return (max(0.0, ly), True)
    if key == "LS_DOWN":
        return (max(0.0, -ly), True)
    if key == "LS_LEFT":
        return (max(0.0, -lx), True)
    if key == "LS_RIGHT":
        return (max(0.0, lx), True)
    if key == "RS_UP":
        return (max(0.0, ry), True)
    if key == "RS_DOWN":
        return (max(0.0, -ry), True)
    if key == "RS_LEFT":
        return (max(0.0, -rx), True)
    if key == "RS_RIGHT":
        return (max(0.0, rx), True)
    return (0.0, False)
def evaluate_mapping(m, st, vals, now):
    """Evaluate one mapping. Mutates st (per-mapping persistent state). Returns True if the action must be active."""
    mode = m.get("mode", "hold")
    if mode not in ("hold", "tap", "toggle", "repeat", "threshold"):
        mode = "hold"
    cond = m.get("condition") or {}
    ctype = cond.get("type", "direct")
    if ctype not in ("direct", "threshold", "sequence"):
        ctype = "direct"
    try:
        thr = float(cond.get("threshold", 0.5) or 0.5)
    except Exception:
        thr = 0.5
    v, is_analog = input_state(m.get("input", "A"), vals)
    level = thr if (is_analog and (ctype == "threshold" or mode == "threshold")) else 0.5
    pressed = (v >= level) if is_analog else (v > 0.5)

    mod = m.get("modifier", "") or ""
    mod_ok = True
    if mod:
        mv, _ = input_state(mod, vals)
        mod_ok = mv > 0.5

    edge = False
    held = False
    if not mod_ok:
        st["prev_pressed"] = False
        st["seq_count"] = 0
        st.pop("armed_at", None)
    elif ctype == "sequence":
        if pressed and not st.get("prev_pressed"):
            interval = max(0.05, float(cond.get("interval_ms", 320) or 320) / 1000.0)
            if st.get("seq_last") and (now - st["seq_last"]) <= interval:
                st["seq_count"] = int(st.get("seq_count", 0)) + 1
            else:
                st["seq_count"] = 1
            st["seq_last"] = now
            if st["seq_count"] >= max(2, int(cond.get("count", 2) or 2)):
                st["seq_count"] = 0
                st["armed_at"] = now
                edge = True
        if st.get("armed_at") is not None and pressed:
            held = True
        else:
            st.pop("armed_at", None)
        st["prev_pressed"] = pressed
    else:
        held = pressed
        edge = pressed and not st.get("prev_pressed", False)
        st["prev_pressed"] = pressed

    if mode == "hold" and m.get("hold_while_moving", False):
        try:
            mx = max(abs(float(vals.get("lx", 0.0) or 0.0)), abs(float(vals.get("ly", 0.0) or 0.0)))
        except Exception:
            mx = 0.0
        moving = mx >= 0.2
        if moving:
            st["mw_last_move"] = now
        if edge:
            st["mw_latch"] = True
            st["mw_last_move"] = now
        if st.get("mw_latch"):
            if (now - float(st.get("mw_last_move", 0.0) or 0.0)) > 0.5:
                st["mw_latch"] = False
        held = bool(st.get("mw_latch"))

    d = m.get("delay") or {}
    delay_on = bool(d.get("enabled", False))
    try:
        dact = (int(d.get("activate_ms", 0) or 0) / 1000.0) if delay_on else 0.0
        dde = (int(d.get("deactivate_ms", 0) or 0) / 1000.0) if delay_on else 0.0
    except Exception:
        dact = 0.0
        dde = 0.0

    out = False
    if mode in ("hold", "threshold"):
        if held:
            st.pop("off_at", None)
            if st.get("on_at") is None:
                st["on_at"] = now + dact
            out = now >= st["on_at"]
        else:
            st["on_at"] = None
            if st.get("out"):
                if st.get("off_at") is None:
                    st["off_at"] = now + dde
                out = now < st["off_at"]
                if not out:
                    st["off_at"] = None
            else:
                st["off_at"] = None
        st["out"] = out
    elif mode == "tap":
        if edge and now >= st.get("pulse_until", 0.0):
            st["pulse_from"] = now + dact
            try:
                tap_ms = int(m.get("tap_ms", 80) or 80)
            except Exception:
                tap_ms = 80
            st["pulse_until"] = st["pulse_from"] + max(0.02, tap_ms / 1000.0)
        out = st.get("pulse_from", 0.0) <= now < st.get("pulse_until", 0.0)
        st["out"] = out
    elif mode == "toggle":
        if edge:
            st["toggled"] = not st.get("toggled", False)
            if st["toggled"]:
                st["on_at"] = now + dact
                st.pop("off_at", None)
            else:
                st["off_at"] = now + dde
                st.pop("on_at", None)
        if st.get("toggled"):
            out = now >= (st.get("on_at") or 0.0)
        else:
            out = now < (st.get("off_at") or 0.0)
        st["out"] = out
    elif mode == "repeat":
        r = m.get("repeat") or {}
        try:
            interval = max(0.04, int(r.get("interval_ms", 300) or 300) / 1000.0)
            press = int(r.get("press_ms", 60) or 60) / 1000.0
        except Exception:
            interval = 0.3
            press = 0.06
        press = max(0.02, min(press, interval - 0.01))
        continuous = bool(r.get("continuous", False))
        if continuous:
            if held and not st.get("cont_running"):
                st["cont_running"] = True
                st["pulses_left"] = 10 ** 9
                st["pulse_next_at"] = now + dact
            elif not held and st.get("cont_running"):
                st["cont_running"] = False
                st["pulses_left"] = 0
                st["pulse_next_at"] = None
        else:
            running = int(st.get("pulses_left", 0) or 0) > 0 or now < st.get("pulse_until", 0.0)
            if edge and not running:
                try:
                    count = int(r.get("count", 3) or 3)
                except Exception:
                    count = 3
                st["pulses_left"] = max(1, min(20, count))
                st["pulse_next_at"] = now + dact
        if int(st.get("pulses_left", 0) or 0) > 0 and st.get("pulse_next_at") is not None and now >= st["pulse_next_at"]:
            st["pulse_until"] = now + press
            st["pulses_left"] = int(st["pulses_left"]) - 1
            st["pulse_next_at"] = (now + interval) if int(st["pulses_left"]) > 0 else None
        out = now < st.get("pulse_until", 0.0)
        st["out"] = out
    return out
def find_hidhide_cli():
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            hh = os.path.join(base, "Nefarius Software Solutions", "HidHide")
            for p in (os.path.join(hh, "HidHideCLI.exe"), os.path.join(hh, "x64", "HidHideCLI.exe")):
                if os.path.exists(p):
                    return p
    return None


def run_hidhide(cli, *args):
    if not cli:
        return (1, "", "cli not found")
    try:
        r = subprocess.run([cli, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except Exception as e:
        return 999, "", str(e)


def _pnp_parent_path(instance_path):
    """Return the parent PnP device instance path, or None."""
    try:
        import ctypes
        from ctypes import wintypes
        cm = ctypes.WinDLL("cfgmgr32")
        devinst = wintypes.DWORD()
        if cm.CM_Locate_DevNodeW(ctypes.byref(devinst), ctypes.c_wchar_p(str(instance_path)), 0) != 0:
            return None
        parent = wintypes.DWORD()
        if cm.CM_Get_Parent(ctypes.byref(parent), devinst, 0) != 0:
            return None
        buf = ctypes.create_unicode_buffer(512)
        if cm.CM_Get_Device_IDW(parent, buf, 512, 0) != 0:
            return None
        return buf.value or None
    except Exception:
        return None


def _device_service(instance_path):
    """Driver service bound to a device (from the PnP Enum registry key)."""
    try:
        import winreg
        key = "SYSTEM\\CurrentControlSet\\Enum\\" + str(instance_path)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            return str(winreg.QueryValueEx(k, "Service")[0])
    except Exception:
        return ""


def _is_vigem_device(instance_path):
    """True when the device (or any parent) is enumerated by the ViGEm bus."""
    cur = str(instance_path or "")
    for _ in range(10):
        if not cur:
            return False
        if _device_service(cur).lower() == "vigembus":
            return True
        cur = _pnp_parent_path(cur) or ""
    return False


class Engine:
    def __init__(self, cfg, status_cb, visual_cb):
        self.cfg = cfg
        self.status_cb = status_cb
        self.visual_cb = visual_cb
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._vg = None
        self._dash_count = 0
        self._state = {}
        self._test_lock = threading.Lock()
        self._test_pulses = []
        self._hidhide_cli = None
        self._hidhide_cloaked = False
        self._hidhide_paths = []
        self._hidhide_turned_on = False
        self._hidhide_lock = threading.Lock()
        self._hidhide_real_paths = []
        self._hidhide_boot_retry_done = False
        self._virtual_slot = None

    def set_config(self, cfg):
        with self._lock:
            self.cfg = cfg

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        self._hidhide_uncloak()
        self._release_vg()

    def trigger_once(self):
        self._press_ls(120)

    def _press_ls(self, ms):
        vgpad = self._vg
        if vgpad is None:
            return
        try:
            vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
            vgpad.update()
            time.sleep(ms / 1000.0)
            vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
            vgpad.update()
        except Exception:
            pass

    def _ensure_vg(self):
        if self._vg is not None:
            return self._vg
        self._vg = vg.VX360Gamepad()
        self._vg.left_joystick(0, 0)
        self._vg.right_joystick(0, 0)
        self._vg.left_trigger(0)
        self._vg.right_trigger(0)
        self._vg.update()
        return self._vg

    def _release_vg(self):
        vgpad = self._vg
        self._vg = None
        if vgpad is not None:
            try:
                vgpad.reset()
                vgpad.update()
            except Exception:
                pass

    def _scale_axis(self, value, deadzone, sensitivity, curve, invert):
        if invert:
            value = -value
        av = abs(value)
        if av < deadzone:
            return 0.0
        av = (av - deadzone) / (1.0 - deadzone)
        av = (av ** curve) * sensitivity
        av = min(1.0, max(0.0, av))
        return av if value >= 0 else -av

    def test_mapping(self, m):
        """Schedule one activation of mapping m on the virtual pad. Returns True if scheduled."""
        if self._vg is None:
            return False
        now = time.perf_counter()
        target = m.get("action", "LS")
        mode = m.get("mode", "hold")
        d = m.get("delay") or {}
        dact = (int(d.get("activate_ms", 0) or 0) / 1000.0) if d.get("enabled") else 0.0
        pulses = []
        if mode == "repeat":
            r = m.get("repeat") or {}
            count = max(1, min(int(r.get("count", 3) or 3), 20))
            interval = max(0.04, int(r.get("interval_ms", 300) or 300) / 1000.0)
            press = max(0.02, min(int(r.get("press_ms", 60) or 60) / 1000.0, interval - 0.01))
            for i in range(count):
                a = now + dact + i * interval
                pulses.append((target, a, a + press))
        elif mode == "tap":
            dur = max(0.02, int(m.get("tap_ms", 80) or 80) / 1000.0)
            pulses.append((target, now + dact, now + dact + dur))
        else:
            pulses.append((target, now + dact, now + dact + 0.8))
        with self._test_lock:
            self._test_pulses.extend(pulses)
        return True

    def reset_mapping_state(self, mapping_id=None):
        with self._lock:
            states = self._state.get("mappings")
            if not states:
                return
            if mapping_id is None:
                states.clear()
            else:
                states.pop(mapping_id, None)

    def _hidhide_collect_paths(self):
        cli = self._hidhide_cli or find_hidhide_cli()
        if not cli:
            return []
        self._hidhide_cli = cli
        run_hidhide(cli, "--app-reg", os.path.abspath(sys.executable))
        code, out, err = run_hidhide(cli, "--dev-gaming")
        if code != 0 or not out.strip():
            return []
        try:
            data = json.loads(out)
        except Exception:
            return []
        paths = []
        seen = set()

        def add_path(p):
            p = str(p or "")
            if p and p not in seen:
                seen.add(p)
                paths.append(p)

        containers = data if isinstance(data, list) else [data]
        for cont in containers:
            devices = cont.get("devices", []) if isinstance(cont, dict) else []
            for dev in devices:
                if not isinstance(dev, dict):
                    continue
                if dev.get("present") is False:
                    continue
                base = str(dev.get("baseContainerDeviceInstancePath", "") or "")
                # Never hide the ViGEm virtual controller: all of its devices sit
                # below the ViGEmBus driver (the real pad hangs off a USB hub).
                if base and _is_vigem_device(base):
                    continue
                friendly = (" " + str(cont.get("friendlyName", "")) + " " + " ".join(str(dev.get(k, "")) for k in ("description", "vendor", "product"))).lower()
                if not ("xbox" in friendly or "xinput" in friendly or str(dev.get("vendor", "")).lower().find("0x45e") >= 0):
                    continue
                for key in ("deviceInstancePath", "baseContainerDeviceInstancePath", "xusbDeviceInstancePath"):
                    v = dev.get(key)
                    if not v:
                        continue
                    add_path(v)
                    parent = _pnp_parent_path(v)
                    if parent and "VID_045E&PID_028E" in parent.upper():
                        add_path(parent)
        return paths

    def _hidhide_apply(self, want):
        """Turn the temporary cloaking on or off. Returns (ok, reason)."""
        with self._hidhide_lock:
            cli = self._hidhide_cli or find_hidhide_cli()
            if not cli:
                return False, "no-cli"
            self._hidhide_cli = cli
            if not want:
                self._hidhide_remove_locked(cli)
                return True, "off"
            run_hidhide(cli, "--app-reg", os.path.abspath(sys.executable))
            # Paths are collected at startup BEFORE the virtual pad exists, and any
            # ViGEm-bus device is always excluded, so only the real pad is hidden.
            paths = list(self._hidhide_real_paths)
            if not paths and self._vg is None:
                paths = self._hidhide_collect_paths()
                self._hidhide_real_paths = list(paths)
            if not paths:
                return False, "no-paths"
            code, out, err = run_hidhide(cli, "--cloak-state")
            was_on = (code == 0 and "--cloak-on" in (out or ""))
            hidden = self._hidhide_hidden_paths(cli) or []
            keep = set(paths)
            args = []
            for p in hidden:
                # Drop leftovers pointing at other instances (older sessions,
                # replaced devnodes or older versions that hid the virtual).
                if "VID_045E&PID_028E" in p.upper() and p not in keep:
                    args += ["--dev-unhide", p]
            for p in paths:
                args += ["--dev-hide", p]
            if not was_on:
                args += ["--cloak-on"]
            code, out, err = run_hidhide(cli, *args)
            if code != 0:
                return False, (err or out or "cli-error")
            self._hidhide_paths = paths
            self._hidhide_turned_on = not was_on
            self._hidhide_cloaked = True
            return True, "on"

    def _hidhide_hidden_paths(self, cli):
        code, out, err = run_hidhide(cli, "--dev-list")
        if code != 0:
            return None
        paths = []
        for line in (out or "").splitlines():
            line = line.strip()
            if line.startswith("--dev-hide"):
                first = line.find("\"")
                last = line.rfind("\"")
                if 0 <= first < last:
                    paths.append(line[first + 1:last])
        return paths

    def _hidhide_remove_locked(self, cli):
        if not self._hidhide_cloaked and not self._hidhide_paths:
            return
        hidden = self._hidhide_hidden_paths(cli) or []
        to_unhide = []
        for p in list(self._hidhide_paths) + [p for p in hidden if "VID_045E&PID_028E" in p.upper()]:
            if p not in to_unhide:
                to_unhide.append(p)
        if to_unhide:
            args = []
            for p in to_unhide:
                args += ["--dev-unhide", p]
            run_hidhide(cli, *args)
        remaining = [p for p in hidden if p not in to_unhide]
        if self._hidhide_turned_on or not remaining:
            run_hidhide(cli, "--cloak-off")
        self._hidhide_cloaked = False
        self._hidhide_paths = []
        self._hidhide_turned_on = False

    def _hidhide_uncloak(self):
        with self._hidhide_lock:
            cli = self._hidhide_cli or find_hidhide_cli()
            if cli and (self._hidhide_cloaked or self._hidhide_paths):
                self._hidhide_remove_locked(cli)

    def _hidhide_heal(self, cli):
        """Undo leftovers from a previous session that was killed while cloaking was on."""
        code, out, err = run_hidhide(cli, "--cloak-state")
        if code != 0 or "--cloak-on" not in (out or ""):
            return
        hidden = self._hidhide_hidden_paths(cli)
        if not hidden:
            return
        ours = [p for p in hidden if "VID_045E&PID_028E" in p.upper()]
        if not ours:
            return
        args = []
        for p in ours:
            args += ["--dev-unhide", p]
        run_hidhide(cli, *args)
        if len(ours) == len(hidden):
            run_hidhide(cli, "--cloak-off")

    def _hidhide_bootstrap(self, cfg):
        cli = find_hidhide_cli()
        if not cli:
            return
        self._hidhide_cli = cli
        run_hidhide(cli, "--app-reg", os.path.abspath(sys.executable))
        self._hidhide_real_paths = self._hidhide_collect_paths()
        if cfg.get("hidhide", False):
            ok, why = self._hidhide_apply(True)
            if not ok and why != "no-paths":
                self.status_cb("hidhide_fail")
        else:
            self._hidhide_heal(cli)

    def apply_hidhide_async(self):
        """Apply the current hidhide setting right away, without restarting the app."""
        def work():
            with self._lock:
                want = bool(self.cfg.get("hidhide", False))
            if want:
                ok, why = self._hidhide_apply(True)
                if ok:
                    self.status_cb("hidhide_on")
                elif why == "no-paths":
                    self.status_cb("hidhide_deferred")
                else:
                    self.status_cb("hidhide_fail")
            else:
                self._hidhide_apply(False)
                self.status_cb("hidhide_off")
        threading.Thread(target=work, daemon=True).start()
    def _loop(self):
        self.status_cb("starting")
        with self._lock:
            cfg0 = json.loads(json.dumps(self.cfg))
        self._hidhide_bootstrap(cfg0)
        slots_before = list(XInput.get_connected())
        try:
            vgpad = self._ensure_vg()
        except Exception as e:
            self.status_cb("virtual_error", e=e)
            self._hidhide_uncloak()
            return
        self._virtual_slot = None
        detect_deadline = time.time() + 2.5
        while self._running and time.time() < detect_deadline:
            current = XInput.get_connected()
            for i in range(4):
                if current[i] and (i >= len(slots_before) or not slots_before[i]):
                    self._virtual_slot = i
                    break
            if self._virtual_slot is not None:
                break
            time.sleep(0.15)
        connected_once = False
        states = self._state.setdefault("mappings", {})
        last_visual = 0.0
        while self._running:
            with self._lock:
                cfg = json.loads(json.dumps(self.cfg))
            try:
                want_idx = int(cfg.get("controller_index", -1))
            except Exception:
                want_idx = -1
            poll = max(0.004, int(cfg.get("poll_ms", 8)) / 1000.0)
            connected_list = XInput.get_connected()
            auto = want_idx < 0
            idx = None
            if auto:
                for i, c in enumerate(connected_list):
                    if c and i != self._virtual_slot:
                        idx = i
                        break
            else:
                idx = max(0, min(3, want_idx))
                if idx >= len(connected_list) or not connected_list[idx]:
                    idx = None
            if idx is None:
                self._hidhide_boot_retry_done = False
                if connected_once:
                    if auto:
                        self.status_cb("real_disconnected_auto")
                    else:
                        self.status_cb("real_disconnected", idx=max(0, min(3, want_idx)))
                else:
                    if auto:
                        self.status_cb("waiting_real_auto")
                    else:
                        self.status_cb("waiting_real", idx=max(0, min(3, want_idx)))
                try:
                    vgpad.reset()
                    vgpad.update()
                except Exception:
                    pass
                for stt in states.values():
                    stt.clear()
                time.sleep(0.3)
                continue
            connected_once = True
            if cfg.get("hidhide", False) and not self._hidhide_boot_retry_done and self._hidhide_cli:
                # (Re)sync HidHide every time the real controller connects: it may
                # have been absent at startup or return on another port with new
                # instance paths. Attempted once per connect cycle.
                self._hidhide_boot_retry_done = True
                fresh = self._hidhide_collect_paths()
                if fresh:
                    self._hidhide_real_paths = fresh
                ok, why = self._hidhide_apply(True)
                if ok:
                    self.status_cb("hidhide_on")
                elif why == "no-paths":
                    self.status_cb("hidhide_deferred")
                else:
                    self.status_cb("hidhide_fail")
            try:
                xstate = XInput.get_state(idx)
                left, right = XInput.get_thumb_values(xstate)
                (lx, ly), (rx, ry) = left, right
                lt, rt = XInput.get_trigger_values(xstate)
                btns = XInput.get_button_values(xstate)
            except Exception as e:
                self.status_cb("reading_error", e=e)
                time.sleep(0.2)
                continue

            la = cfg.get("analog", {}).get("left", {})
            ra = cfg.get("analog", {}).get("right", {})
            tl = cfg.get("triggers", {}).get("left", {})
            tr = cfg.get("triggers", {}).get("right", {})
            lx_o = self._scale_axis(lx, la.get("deadzone", 0.08), la.get("sensitivity", 1.0), la.get("curve", 1.0), la.get("invert_x", False))
            ly_o = self._scale_axis(ly, la.get("deadzone", 0.08), la.get("sensitivity", 1.0), la.get("curve", 1.0), la.get("invert_y", False))
            rx_o = self._scale_axis(rx, ra.get("deadzone", 0.08), ra.get("sensitivity", 1.0), ra.get("curve", 1.0), ra.get("invert_x", False))
            ry_o = self._scale_axis(ry, ra.get("deadzone", 0.08), ra.get("sensitivity", 1.0), ra.get("curve", 1.0), ra.get("invert_y", False))
            lt_o = self._scale_axis(lt, tl.get("deadzone", 0.05), tl.get("sensitivity", 1.0), 1.0, tl.get("invert", False))
            rt_o = self._scale_axis(rt, tr.get("deadzone", 0.05), tr.get("sensitivity", 1.0), 1.0, tr.get("invert", False))

            now = time.perf_counter()
            profile_name = cfg.get("profile_name", "Default")
            active_profile = None
            for p in cfg.get("profiles", []):
                if p.get("name") == profile_name:
                    active_profile = p
                    break
            if active_profile is None and cfg.get("profiles"):
                active_profile = cfg["profiles"][0]
            mappings = active_profile.get("mappings", []) if active_profile else cfg.get("mappings", [])

            vals = {"buttons": {}, "lx": lx, "ly": ly, "rx": rx, "ry": ry, "lt": lt, "rt": rt}
            for bkey, xname in XINPUT_BUTTON_NAMES.items():
                vals["buttons"][bkey] = bool(btns.get(xname, False))

            injected = set()
            lt_inject = False
            rt_inject = False
            live_ids = set()
            for m in mappings:
                if not m.get("enabled", True):
                    continue
                mid = m.get("id")
                if mid is None:
                    mid = id(m)
                live_ids.add(mid)
                st = states.setdefault(mid, {})
                try:
                    act = evaluate_mapping(m, st, vals, now)
                except Exception:
                    act = False
                if act:
                    target = m.get("action", "")
                    if target == "LT":
                        lt_inject = True
                    elif target == "RT":
                        rt_inject = True
                    elif target:
                        injected.add(target)
            for k in [k for k in states if k not in live_ids]:
                states.pop(k, None)

            with self._test_lock:
                for p in list(self._test_pulses):
                    tgt, a, b = p
                    if a <= now < b:
                        if tgt == "LT":
                            lt_inject = True
                        elif tgt == "RT":
                            rt_inject = True
                        else:
                            injected.add(tgt)
                    elif now - b > 0.5:
                        self._test_pulses.remove(p)

            out_buttons = dict(vals["buttons"])
            for t in injected:
                if t in out_buttons:
                    out_buttons[t] = True
            lt_out = max(lt_o, 1.0 if lt_inject else 0.0)
            rt_out = max(rt_o, 1.0 if rt_inject else 0.0)
            try:
                for key, xbtn in BUTTON_MAP.items():
                    if out_buttons.get(key, False):
                        vgpad.press_button(xbtn)
                    else:
                        vgpad.release_button(xbtn)
                vgpad.left_joystick(int(lx_o * 32767), int(ly_o * 32767))
                vgpad.right_joystick(int(rx_o * 32767), int(ry_o * 32767))
                vgpad.left_trigger(int(max(0.0, min(1.0, lt_out)) * 255))
                vgpad.right_trigger(int(max(0.0, min(1.0, rt_out)) * 255))
                vgpad.update()
            except Exception as e:
                self.status_cb("virtual_error", e=e)
                time.sleep(0.1)
                continue
            if now - last_visual >= 0.05:
                last_visual = now
                try:
                    pressed = {k for k, v in out_buttons.items() if v}
                    if lt_out > 0.5:
                        pressed.add("LT")
                    if rt_out > 0.5:
                        pressed.add("RT")
                    self.visual_cb({
                        "connected": True,
                        "pressed": pressed,
                        "buttons": dict(vals["buttons"]),
                        "lx": lx, "ly": ly, "rx": rx, "ry": ry,
                        "lt": lt, "rt": rt,
                        "active_profile": cfg.get("profile_name", "Default"),
                    })
                except Exception:
                    pass
            time.sleep(poll)
class RoundedCard(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, **kwargs)


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.lang = self.cfg.get("language", detect_language())
        self.profile_name = self.cfg.get("profile_name", "Default")
        self.last_visual = None
        self.root.title("OniDash L3")
        self.root.geometry("1280x820")
        self.root.minsize(1080, 700)
        self._build_style()
        self.engine = Engine(self.cfg, self._status_callback, self._visual_callback)
        self._build_layout()
        self.engine.start()
        self._poll_visual()

    def _build_style(self):
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TButton", background=PANEL, foreground=LIGHT, bordercolor=BORDER, padding=(12, 8))
        style.map("TButton", background=[("active", CARD)], foreground=[("active", GOLD)])
        style.configure("TEntry", fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER)
        style.map("TEntry", fieldbackground=[("disabled", PANEL)], foreground=[("disabled", MUTED)])
        style.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER, padding=6, arrowcolor=TEXT)
        style.map("TCombobox",
                  fieldbackground=[("readonly", CARD), ("disabled", PANEL)],
                  foreground=[("readonly", TEXT), ("disabled", MUTED)],
                  selectbackground=[("readonly", CARD), ("!readonly", CARD)],
                  selectforeground=[("readonly", TEXT), ("!readonly", TEXT)],
                  background=[("readonly", PANEL), ("active", CARD)],
                  arrowcolor=[("active", GOLD)])
        style.configure("TSpinbox", fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER, arrowcolor=TEXT)
        style.map("TSpinbox", fieldbackground=[("disabled", PANEL)], foreground=[("disabled", MUTED)], arrowcolor=[("active", GOLD)])
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2A3446")
        self.root.option_add("*TCombobox*Listbox.selectForeground", GOLD)
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.configure("TLabelframe", background=BG, foreground=TEXT)
        style.configure("TLabelframe.Label", background=BG, foreground=GOLD, font=("Segoe UI", 11, "bold"))
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT, bordercolor=BORDER, rowheight=34)
        style.configure("Treeview.Heading", background=PANEL, foreground=GOLD, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2A3446")])
        try:
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass

    def _build_layout(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.sidebar = tk.Frame(self.root, bg=PANEL, width=210)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.topbar = tk.Frame(self.root, bg=BG, height=56)
        self.topbar.grid(row=0, column=1, sticky="new")
        self.topbar.grid_propagate(False)
        self.content_host = tk.Frame(self.root, bg=BG)
        self.content_host.grid(row=0, column=1, sticky="nsew", pady=(56, 0))
        self.pages = {}
        for name in ("home", "mapping", "analog", "triggers", "profiles", "settings"):
            f = tk.Frame(self.content_host, bg=BG)
            self.pages[name] = f
            f.grid(row=0, column=0, sticky="nsew")
        self.content_host.rowconfigure(0, weight=1)
        self.content_host.columnconfigure(0, weight=1)
        self._build_sidebar()
        self._build_home(self.pages["home"])
        self._build_mapping(self.pages["mapping"])
        self._build_analog(self.pages["analog"])
        self._build_triggers(self.pages["triggers"])
        self._build_profiles(self.pages["profiles"])
        self._build_settings(self.pages["settings"])
        self._show_page("home")

    def _build_sidebar(self):
        title = tk.Label(self.sidebar, text="OniDash L3", bg=PANEL, fg=GOLD, font=("Segoe UI", 14, "bold"))
        title.pack(anchor="w", padx=18, pady=(18, 10))
        subtitle = tk.Label(self.sidebar, text=T(self.lang, "universal_controller"), bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        subtitle.pack(anchor="w", padx=18, pady=(0, 16))
        self.status_label = tk.Label(self.sidebar, text=T(self.lang, "stopped"), bg=PANEL, fg=DANGER, font=("Segoe UI", 9, "bold"), wraplength=170, justify="left")
        self.status_label.pack(anchor="w", padx=18, pady=(0, 14))
        for key, label_key in [("home", "nav_home"), ("mapping", "nav_mapping"), ("analog", "nav_analog"), ("triggers", "nav_triggers"), ("profiles", "nav_profiles"), ("settings", "nav_settings")]:
            btn = tk.Button(self.sidebar, text=T(self.lang, label_key), bg=PANEL, fg=TEXT, relief="flat", anchor="w", padx=18, pady=10,
                            activebackground=CARD, activeforeground=GOLD, command=lambda k=key: self._show_page(k))
            btn.pack(fill="x")

    def _show_page(self, name):
        self.pages[name].tkraise()
    def _build_home(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        header = tk.Label(parent, text=T(self.lang, "home_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        self.canvas = tk.Canvas(body, bg=CARD, highlightthickness=0, width=560, height=360)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._draw_controller()
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.card_profile = RoundedCard(right)
        self.card_profile.pack(fill="x", pady=(0, 12))
        tk.Label(self.card_profile, text=T(self.lang, "active_profile"), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        self.profile_value = tk.Label(self.card_profile, text=self.profile_name, bg=CARD, fg=GOLD, font=("Segoe UI", 16, "bold"))
        self.profile_value.pack(anchor="w", padx=16, pady=(0, 12))
        self.card_conn = RoundedCard(right)
        self.card_conn.pack(fill="x", pady=(0, 12))
        tk.Label(self.card_conn, text=T(self.lang, "controller_status"), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        self.conn_value = tk.Label(self.card_conn, text=T(self.lang, "checking"), bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.conn_value.pack(anchor="w", padx=16, pady=(0, 12))
        self.card_mapper = RoundedCard(right)
        self.card_mapper.pack(fill="x")
        tk.Label(self.card_mapper, text=T(self.lang, "quick_actions"), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        for lbl, page in [(T(self.lang, "open_mapping"), "mapping"), (T(self.lang, "edit_analogs"), "analog"), (T(self.lang, "profiles_title"), "profiles")]:
            b = tk.Button(self.card_mapper, text=lbl, bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=lambda p=page: self._show_page(p))
            b.pack(fill="x", padx=16, pady=4)
        tk.Frame(self.card_mapper, bg=CARD, height=8).pack()

    def _draw_controller(self):
        c = self.canvas
        c.delete("all")
        body = "#1A202A"
        pad = "#2A3342"
        # symmetric Xbox-style body (centered at x=280)
        points = [160, 140, 190, 100, 280, 88, 370, 100, 400, 140,
                  412, 190, 400, 290, 365, 335, 320, 305, 300, 255,
                  280, 245, 260, 255, 240, 305, 195, 335, 160, 290, 148, 190]
        c.create_polygon(points, smooth=True, fill=body, outline=BORDER, width=2)
        # shoulders (symmetric around x=280)
        c.create_rectangle(175, 78, 235, 90, fill=PANEL, outline=BORDER, tags="fLT")
        c.create_text(205, 84, text="LT", fill=MUTED, font=("Segoe UI", 7, "bold"), tags="tLT")
        c.create_rectangle(325, 78, 385, 90, fill=PANEL, outline=BORDER, tags="fRT")
        c.create_text(355, 84, text="RT", fill=MUTED, font=("Segoe UI", 7, "bold"), tags="tRT")
        c.create_rectangle(180, 96, 230, 112, fill=PANEL, outline=BORDER, tags="fLB")
        c.create_text(205, 104, text="LB", fill=MUTED, font=("Segoe UI", 8, "bold"), tags="tLB")
        c.create_rectangle(330, 96, 380, 112, fill=PANEL, outline=BORDER, tags="fRB")
        c.create_text(355, 104, text="RB", fill=MUTED, font=("Segoe UI", 8, "bold"), tags="tRB")
        # analog trigger bars (fill grows with the trigger value)
        c.create_rectangle(190, 114, 220, 146, fill="#10151D", outline=BORDER, tags="trigbgLT")
        c.create_rectangle(192, 146, 218, 146, fill=GOLD, outline="", tags="trigfillLT")
        c.create_rectangle(340, 114, 370, 146, fill="#10151D", outline=BORDER, tags="trigbgRT")
        c.create_rectangle(342, 146, 368, 146, fill=GOLD, outline="", tags="trigfillRT")
        # back / start (symmetric around x=280)
        c.create_oval(250, 120, 266, 136, fill=PANEL, outline=BORDER, tags="fBACK")
        c.create_text(258, 128, text="\u25c0", fill=MUTED, font=("Segoe UI", 6), tags="tBACK")
        c.create_oval(294, 120, 310, 136, fill=PANEL, outline=BORDER, tags="fSTART")
        c.create_text(302, 128, text="\u25b6", fill=MUTED, font=("Segoe UI", 6), tags="tSTART")
        # d-pad (left, centered at 205,185)
        cx, cy = 205, 185
        c.create_rectangle(cx - 9, cy - 34, cx + 9, cy - 4, fill=pad, outline=BORDER, tags="fDPAD_UP")
        c.create_rectangle(cx - 9, cy + 4, cx + 9, cy + 34, fill=pad, outline=BORDER, tags="fDPAD_DOWN")
        c.create_rectangle(cx - 34, cy - 9, cx - 4, cy + 9, fill=pad, outline=BORDER, tags="fDPAD_LEFT")
        c.create_rectangle(cx + 4, cy - 9, cx + 34, cy + 9, fill=pad, outline=BORDER, tags="fDPAD_RIGHT")
        c.create_rectangle(cx - 6, cy - 6, cx + 6, cy + 6, fill="#10151D", outline=BORDER)
        # abxy (right, centered at 355,185)
        bx, by = 355, 185
        for key, dx, dy in (("B", 0, -28), ("A", 28, 0), ("X", -28, 0), ("Y", 0, 28)):
            c.create_oval(bx + dx - 15, by + dy - 15, bx + dx + 15, by + dy + 15, fill=pad, outline=BORDER, tags="f" + key)
            c.create_text(bx + dx, by + dy, text=key, fill=MUTED, font=("Segoe UI", 9, "bold"), tags="t" + key)
        # analog sticks (symmetric)
        for key, sx, sy in (("LS", 205, 265), ("RS", 355, 265)):
            c.create_oval(sx - 32, sy - 32, sx + 32, sy + 32, fill="#10151D", outline=BORDER)
            c.create_oval(sx - 20, sy - 20, sx + 20, sy + 20, fill=pad, outline=BORDER, tags="f" + key)
            c.create_text(sx, sy, text="L3" if key == "LS" else "R3", fill=MUTED, font=("Segoe UI", 8, "bold"), tags="t" + key)
            c.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill=GOLD, outline="", tags="dot" + key)
    def _build_mapping(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)
        header = tk.Label(parent, text=T(self.lang, "mapping_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        tk.Label(parent, text=T(self.lang, "desc_mapping"), bg=BG, fg=MUTED, wraplength=900, justify="left", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 6))
        for key, cmd in (("add_mapping", self._add_mapping), ("edit", self._edit_mapping), ("map_toggle", self._toggle_mapping), ("duplicate", self._duplicate_mapping), ("remove", self._remove_mapping)):
            tk.Button(toolbar, text=T(self.lang, key), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=cmd).pack(side="left", padx=(0, 8))
        presets = tk.Frame(parent, bg=BG)
        presets.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 8))
        tk.Label(presets, text=T(self.lang, "presets_label"), bg=BG, fg=GOLD, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        tk.Button(presets, text=T(self.lang, "preset_ls_double"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=5, command=self._add_preset_double_push).pack(side="left", padx=(0, 8))
        tk.Button(presets, text=T(self.lang, "preset_b_double"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=5, command=self._add_preset_b_two).pack(side="left")
        self.map_tree = ttk.Treeview(parent, columns=("summary", "status"), show="headings", height=16)
        self.map_tree.heading("summary", text=T(self.lang, "map_summary"))
        self.map_tree.heading("status", text=T(self.lang, "map_status"))
        self.map_tree.column("summary", width=780, anchor="w")
        self.map_tree.column("status", width=120, anchor="center")
        self.map_tree.grid(row=4, column=0, sticky="nsew", padx=24, pady=(0, 6))
        self.map_tree.bind("<Double-1>", lambda e: self._edit_mapping())
        self.map_tree.tag_configure("inactive", foreground=MUTED)
        tk.Label(parent, text=T(self.lang, "map_hint"), bg=BG, fg=MUTED, font=("Segoe UI", 9)).grid(row=5, column=0, sticky="w", padx=24, pady=(0, 16))
        self._refresh_mappings()

    def _active_profile(self):
        name = self.cfg.get("profile_name", "Default")
        profiles = self.cfg.setdefault("profiles", [])
        if not profiles:
            profiles.append({"name": name, "description": "", "mappings": []})
        for p in profiles:
            if p.get("name") == name:
                return p
        self.cfg["profile_name"] = profiles[0].get("name", "Default")
        return profiles[0]

    def _current_mappings(self):
        return self._active_profile().setdefault("mappings", [])

    def _sync_mappings(self):
        self.cfg["mappings"] = [json.loads(json.dumps(m)) for m in self._current_mappings()]
        save_config(self.cfg)
        self.engine.set_config(self.cfg)

    def _refresh_mappings(self, select_idx=None):
        for i in self.map_tree.get_children():
            self.map_tree.delete(i)
        mappings = self._current_mappings()
        if not mappings:
            self.map_tree.insert("", "end", iid="__none", values=(T(self.lang, "map_none"), ""))
            return
        for idx, m in enumerate(mappings):
            enabled = m.get("enabled", True)
            self.map_tree.insert("", "end", iid=str(idx),
                                 values=(self._mapping_summary(m), T(self.lang, "map_active") if enabled else T(self.lang, "map_inactive")),
                                 tags=() if enabled else ("inactive",))
        if select_idx is not None and 0 <= select_idx < len(mappings):
            try:
                self.map_tree.selection_set(str(select_idx))
                self.map_tree.see(str(select_idx))
            except Exception:
                pass

    def _selected_mapping(self):
        sel = self.map_tree.selection()
        if not sel or sel[0] == "__none":
            return None
        try:
            idx = int(sel[0])
        except Exception:
            return None
        if 0 <= idx < len(self._current_mappings()):
            return idx
        return None

    def _mapping_summary(self, m):
        lang = self.lang
        inp = INPUT_LABELS.get(m.get("input", ""), m.get("input", ""))
        act = ACTION_LABELS.get(m.get("action", ""), m.get("action", ""))
        parts = ["%s %s %s" % (inp, T(lang, "map_to"), act)]
        cond = m.get("condition") or {}
        mode = m.get("mode", "hold")
        if mode == "hold":
            parts.append(T(lang, "sum_hold"))
        elif mode == "tap":
            parts.append(T(lang, "sum_tap", ms=m.get("tap_ms", 80)))
        elif mode == "toggle":
            parts.append(T(lang, "sum_toggle"))
        elif mode == "repeat":
            r = m.get("repeat") or {}
            parts.append(T(lang, "sum_repeat_cont") if r.get("continuous") else T(lang, "sum_repeat", n=r.get("count", 3)))
            parts.append(T(lang, "sum_interval", ms=r.get("interval_ms", 300)))
            parts.append(T(lang, "sum_press", ms=r.get("press_ms", 60)))
        elif mode == "threshold":
            try:
                pct = int(round(float(cond.get("threshold", 0.5) or 0.5) * 100))
            except Exception:
                pct = 50
            parts.append(T(lang, "sum_threshold", pct=pct))
        if cond.get("type") == "sequence":
            parts.append(T(lang, "sum_seq", n=cond.get("count", 2), ms=cond.get("interval_ms", 320)))
        elif cond.get("type") == "threshold" and mode != "threshold":
            try:
                pct = int(round(float(cond.get("threshold", 0.5) or 0.5) * 100))
            except Exception:
                pct = 50
            parts.append(T(lang, "sum_threshold", pct=pct))
        if m.get("modifier"):
            parts.append(T(lang, "sum_modifier", btn=INPUT_LABELS.get(m["modifier"], m["modifier"])))
        if mode == "hold" and m.get("hold_while_moving"):
            parts.append(T(lang, "sum_while_moving"))
        d = m.get("delay") or {}
        if d.get("enabled"):
            parts.append(T(lang, "sum_delays", a=d.get("activate_ms", 0), d=d.get("deactivate_ms", 0)))
        return " \u00b7 ".join(parts)
    def _add_mapping(self):
        MappingEditor(self, None, on_save=self._store_new_mapping)

    def _store_new_mapping(self, m):
        mappings = self._current_mappings()
        m["id"] = self._next_mapping_id(mappings)
        mappings.append(m)
        self._sync_mappings()
        self._refresh_mappings(len(mappings) - 1)
        self.engine.reset_mapping_state()

    def _next_mapping_id(self, mappings):
        used = set()
        for x in mappings:
            try:
                used.add(int(x.get("id", 0) or 0))
            except Exception:
                pass
        nid = 1
        while nid in used:
            nid += 1
        return nid

    def _edit_mapping(self):
        idx = self._selected_mapping()
        if idx is None:
            return
        m = self._current_mappings()[idx]
        MappingEditor(self, m, on_save=lambda nm: self._store_edited_mapping(idx, nm))

    def _store_edited_mapping(self, idx, m):
        mappings = self._current_mappings()
        if not (0 <= idx < len(mappings)):
            return
        old = mappings[idx]
        m["id"] = old.get("id", m.get("id"))
        m["enabled"] = old.get("enabled", True)
        mappings[idx] = m
        self._sync_mappings()
        self._refresh_mappings(idx)
        self.engine.reset_mapping_state(m.get("id"))

    def _toggle_mapping(self):
        idx = self._selected_mapping()
        if idx is None:
            return
        m = self._current_mappings()[idx]
        m["enabled"] = not m.get("enabled", True)
        self._sync_mappings()
        self._refresh_mappings(idx)
        self.engine.reset_mapping_state(m.get("id"))

    def _duplicate_mapping(self):
        idx = self._selected_mapping()
        if idx is None:
            return
        src = self._current_mappings()[idx]
        new = json.loads(json.dumps(src))
        mappings = self._current_mappings()
        new["id"] = self._next_mapping_id(mappings)
        mappings.append(new)
        self._sync_mappings()
        self._refresh_mappings(len(mappings) - 1)

    def _remove_mapping(self):
        idx = self._selected_mapping()
        if idx is None:
            return
        del self._current_mappings()[idx]
        self._sync_mappings()
        remaining = len(self._current_mappings())
        self._refresh_mappings(min(idx, remaining - 1) if remaining else None)
        self.engine.reset_mapping_state()

    def _add_preset_double_push(self):
        self._add_preset_mapping(T(self.lang, "preset_ls_double"), {
            "input": "LS_UP",
            "condition": {"type": "sequence", "count": 2, "interval_ms": 320, "threshold": 0.78},
            "mode": "hold",
            "action": "LS",
            "tap_ms": 130,
            "delay": {"enabled": False, "activate_ms": 0, "deactivate_ms": 0},
        })

    def _add_preset_b_two(self):
        self._add_preset_mapping(T(self.lang, "preset_b_double"), {
            "input": "B",
            "condition": {"type": "sequence", "count": 2, "interval_ms": 320, "threshold": 0.78},
            "mode": "hold",
            "action": "LS",
            "tap_ms": 130,
            "delay": {"enabled": True, "activate_ms": 350, "deactivate_ms": 0},
            "hold_while_moving": True,
        })

    def _add_preset_mapping(self, name, spec):
        m = default_mapping()
        m.update(spec)
        m["name"] = name
        mappings = self._current_mappings()
        m["id"] = self._next_mapping_id(mappings)
        mappings.append(m)
        self._sync_mappings()
        self._refresh_mappings(len(mappings) - 1)
        self.engine.reset_mapping_state()
    def _build_analog(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text=T(self.lang, "analogs_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        tk.Label(parent, text=T(self.lang, "desc_analog"), bg=BG, fg=MUTED, wraplength=900, justify="left", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))
        container = tk.Frame(parent, bg=BG)
        container.grid(row=2, column=0, sticky="nsew", padx=24, pady=10)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        self.analog_value_labels = {}
        for side, col, title in (("left", 0, "Left Stick (L3)"), ("right", 1, "Right Stick (R3)")):
            card = RoundedCard(container)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0 if col == 1 else 8))
            tk.Label(card, text=title, bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
            cfg = self.cfg["analog"][side]
            specs = [
                (T(self.lang, "deadzone") + " (0-50)", "deadzone", 0, 50),
                (T(self.lang, "sensitivity") + " (25-250)", "sensitivity", 25, 250),
                (T(self.lang, "curve") + " (25-300)", "curve", 25, 300),
                (T(self.lang, "threshold") + " (25-98)", "threshold", 25, 98),
            ]
            for label, key, frm, to in specs:
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=16, pady=4)
                tk.Label(row, text=label, bg=CARD, fg=TEXT, width=24, anchor="w").pack(side="left")
                val_label = tk.Label(row, text="", bg=CARD, fg=MUTED, width=5)
                val_label.pack(side="right")
                scale = ttk.Scale(row, from_=frm, to=to, orient="horizontal")
                scale.pack(side="left", fill="x", expand=True, padx=8)
                try:
                    cur = float(cfg.get(key, 0.08 if key == "deadzone" else 1.0)) * 100.0
                except Exception:
                    cur = float(frm)
                scale.set(cur)
                val_label.config(text=str(int(round(cur))))
                self.analog_value_labels[(side, key)] = val_label
                scale.configure(command=lambda v, s=side, k=key, lab=val_label: self._set_analog_scale(s, k, v, lab))
            for opt in ("invert_x", "invert_y"):
                var = tk.BooleanVar(value=bool(cfg.get(opt, False)))
                tk.Checkbutton(card, text="%s %s" % (T(self.lang, "invert"), opt.split("_")[1].upper()), variable=var, bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD,
                               command=lambda s=side, o=opt, v=var: self._set_analog(s, o, v.get())).pack(anchor="w", padx=16, pady=2)
        tk.Label(container, text=T(self.lang, "changes_apply"), bg=BG, fg=MUTED, font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _set_analog_scale(self, side, key, value, label):
        try:
            fv = float(value)
        except Exception:
            return
        self.cfg["analog"][side][key] = fv / 100.0
        try:
            label.config(text=str(int(round(fv))))
        except Exception:
            pass
        save_config(self.cfg)

    def _set_analog(self, side, key, value):
        self.cfg["analog"][side][key] = value
        save_config(self.cfg)

    def _build_triggers(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text=T(self.lang, "triggers_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        tk.Label(parent, text=T(self.lang, "desc_triggers"), bg=BG, fg=MUTED, wraplength=900, justify="left", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=2, column=0, sticky="nsew", padx=24, pady=10)
        for side, title in (("left", "Left Trigger (LT)"), ("right", "Right Trigger (RT)")):
            card = RoundedCard(body)
            card.pack(fill="x", pady=(0, 12))
            tk.Label(card, text=title, bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
            cfg = self.cfg["triggers"][side]
            for label, key, frm, to in ((T(self.lang, "deadzone") + " (0-100)", "deadzone", 0, 100), (T(self.lang, "sensitivity") + " (25-250)", "sensitivity", 25, 250)):
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=16, pady=4)
                tk.Label(row, text=label, bg=CARD, fg=TEXT, width=24, anchor="w").pack(side="left")
                val_label = tk.Label(row, text="", bg=CARD, fg=MUTED, width=5)
                val_label.pack(side="right")
                scale = ttk.Scale(row, from_=frm, to=to, orient="horizontal")
                scale.pack(side="left", fill="x", expand=True, padx=8)
                try:
                    cur = float(cfg.get(key, 0.05)) * 100.0
                except Exception:
                    cur = float(frm)
                scale.set(cur)
                val_label.config(text=str(int(round(cur))))
                scale.configure(command=lambda v, s=side, k=key, lab=val_label: self._set_trigger_scale(s, k, v, lab))
            inv = tk.BooleanVar(value=bool(cfg.get("invert", False)))
            tk.Checkbutton(card, text=T(self.lang, "invert"), variable=inv, bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD,
                           command=lambda s=side, v=inv: self._set_trigger(s, "invert", v.get())).pack(anchor="w", padx=16, pady=6)

    def _set_trigger_scale(self, side, key, value, label):
        try:
            fv = float(value)
        except Exception:
            return
        self.cfg["triggers"][side][key] = fv / 100.0
        try:
            label.config(text=str(int(round(fv))))
        except Exception:
            pass
        save_config(self.cfg)

    def _set_trigger(self, side, key, value):
        self.cfg["triggers"][side][key] = value
        save_config(self.cfg)
    def _build_profiles(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text=T(self.lang, "profiles_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        tk.Label(parent, text=T(self.lang, "desc_profiles"), bg=BG, fg=MUTED, wraplength=900, justify="left", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        for key, cmd in (("profile_new", self._new_profile), ("duplicate", self._duplicate_profile), ("profile_import", self._import_profile), ("profile_export", self._export_profile)):
            tk.Button(toolbar, text=T(self.lang, key), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=cmd).pack(side="left", padx=(0, 8))
        self.profile_cards = tk.Frame(parent, bg=BG)
        self.profile_cards.grid(row=3, column=0, sticky="nsew", padx=24, pady=10)
        parent.rowconfigure(3, weight=1)
        self._refresh_profiles()

    def _refresh_profiles(self):
        for w in self.profile_cards.winfo_children():
            w.destroy()
        for prof in self.cfg.get("profiles", []):
            card = RoundedCard(self.profile_cards)
            card.pack(fill="x", pady=(0, 10))
            active = prof.get("name") == self.cfg.get("profile_name")
            title = prof.get("name", "Profile") + (" \u2713" if active else "")
            tk.Label(card, text=title, bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
            tk.Label(card, text=prof.get("description", ""), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 8))
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=16, pady=(0, 12))
            tk.Button(row, text=T(self.lang, "use"), bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=4, command=lambda p=prof: self._use_profile(p)).pack(side="left", padx=(0, 6))
            tk.Button(row, text=T(self.lang, "edit"), bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=4, command=lambda p=prof: self._edit_profile(p)).pack(side="left", padx=(0, 6))
            tk.Button(row, text=T(self.lang, "delete"), bg=PANEL, fg=DANGER, relief="flat", padx=10, pady=4, command=lambda p=prof: self._delete_profile(p)).pack(side="left")

    def _use_profile(self, prof):
        self.cfg["profile_name"] = prof.get("name")
        self.profile_name = prof.get("name")
        try:
            self.profile_value.config(text=self.profile_name)
        except Exception:
            pass
        self._sync_mappings()
        self._refresh_profiles()
        self._refresh_mappings()
        self.engine.reset_mapping_state()

    def _new_profile(self):
        profiles = self.cfg.setdefault("profiles", [])
        name = T(self.lang, "profile_new_name", n=len(profiles) + 1)
        existing = {p.get("name") for p in profiles}
        n = len(profiles) + 1
        while name in existing:
            n += 1
            name = T(self.lang, "profile_new_name", n=n)
        prof = {"name": name, "description": T(self.lang, "profile_new_desc"), "mappings": []}
        profiles.append(prof)
        self._use_profile(prof)

    def _duplicate_profile(self):
        profiles = self.cfg.get("profiles", [])
        if not profiles:
            return
        src = None
        for p in profiles:
            if p.get("name") == self.cfg.get("profile_name"):
                src = p
                break
        if src is None:
            src = profiles[-1]
        name = "%s (%s)" % (src.get("name", "Profile"), T(self.lang, "profile_copy"))
        prof = {"name": name, "description": src.get("description", ""), "mappings": json.loads(json.dumps(src.get("mappings", [])))}
        profiles.append(prof)
        self._refresh_profiles()
        save_config(self.cfg)

    def _edit_profile(self, prof):
        name = simpledialog.askstring(T(self.lang, "profile_edit_title"), T(self.lang, "profile_name"), initialvalue=prof.get("name", ""), parent=self.root)
        if name:
            prof["name"] = name
            desc = simpledialog.askstring(T(self.lang, "profile_edit_title"), T(self.lang, "profile_desc"), initialvalue=prof.get("description", ""), parent=self.root)
            if desc is not None:
                prof["description"] = desc
            if self.cfg.get("profile_name") != name and self.cfg.get("profile_name") in [p.get("name") for p in self.cfg.get("profiles", [])]:
                pass
            self._refresh_profiles()
            save_config(self.cfg)

    def _delete_profile(self, prof):
        if len(self.cfg.get("profiles", [])) <= 1:
            messagebox.showwarning(T(self.lang, "profiles_title"), T(self.lang, "cannot_delete_last_profile"))
            return
        was_active = prof.get("name") == self.cfg.get("profile_name")
        self.cfg["profiles"] = [p for p in self.cfg["profiles"] if p is not prof]
        if was_active and self.cfg["profiles"]:
            self.cfg["profile_name"] = self.cfg["profiles"][0].get("name", "Default")
            self.profile_name = self.cfg["profile_name"]
            try:
                self.profile_value.config(text=self.profile_name)
            except Exception:
                pass
        self.cfg["mappings"] = [json.loads(json.dumps(m)) for m in self._current_mappings()]
        self._refresh_profiles()
        self._refresh_mappings()
        save_config(self.cfg)
        self.engine.set_config(self.cfg)

    def _import_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "name" not in data or "mappings" not in data:
                raise ValueError(T(self.lang, "invalid_profile"))
            data["mappings"] = [normalize_mapping(m) for m in data.get("mappings", [])]
            self.cfg.setdefault("profiles", []).append(data)
            self._refresh_profiles()
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror(T(self.lang, "profile_import"), T(self.lang, "import_error", e=e))

    def _export_profile(self):
        profile = self._active_profile()
        if not profile:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror(T(self.lang, "profile_export"), T(self.lang, "export_error", e=e))
    def _build_settings(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text=T(self.lang, "settings_title"), bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 4))
        tk.Label(parent, text=T(self.lang, "desc_settings"), bg=BG, fg=MUTED, wraplength=900, justify="left", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=2, column=0, sticky="nsew", padx=24, pady=10)
        L1 = RoundedCard(body)
        L1.pack(fill="x", pady=(0, 12))
        tk.Label(L1, text=T(self.lang, "language"), bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        lang = ttk.Combobox(L1, values=["Portugues", "English", "Espanol"], state="readonly", width=28)
        lang.set({"pt": "Portugues", "en": "English", "es": "Espanol"}.get(self.lang, "Portugues"))
        lang.pack(anchor="w", padx=16, pady=(0, 12))
        lang.bind("<<ComboboxSelected>>", lambda e: self._set_setting("language", {"Portugues": "pt", "English": "en", "Espanol": "es"}.get(lang.get(), self.lang)))
        C1 = RoundedCard(body)
        C1.pack(fill="x", pady=(0, 12))
        tk.Label(C1, text=T(self.lang, "controller_and_virtual"), bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        dev_row = tk.Frame(C1, bg=CARD)
        dev_row.pack(fill="x", padx=16, pady=4)
        tk.Label(dev_row, text=T(self.lang, "xinput_slot"), bg=CARD, fg=TEXT).pack(side="left")
        try:
            cur_idx = int(self.cfg.get("controller_index", -1))
        except Exception:
            cur_idx = -1
        auto_label = T(self.lang, "slot_auto")
        sc = ttk.Combobox(dev_row, values=[auto_label, "0", "1", "2", "3"], state="readonly", width=14)
        sc.set(auto_label if cur_idx < 0 else str(cur_idx))
        sc.pack(side="right")
        sc.bind("<<ComboboxSelected>>", lambda e: self._set_setting("controller_index", -1 if sc.get() == auto_label else int(sc.get())))
        vc = tk.BooleanVar(value=self.cfg.get("virtual_controller", True))
        tk.Checkbutton(C1, text=T(self.lang, "create_virtual"), variable=vc, bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD, command=lambda: self._set_setting("virtual_controller", vc.get())).pack(anchor="w", padx=16, pady=4)
        hh = tk.BooleanVar(value=self.cfg.get("hidhide", False))
        tk.Checkbutton(C1, text=T(self.lang, "use_hidhide"), variable=hh, bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD, command=lambda: self._toggle_hidhide(hh.get())).pack(anchor="w", padx=16, pady=4)
        tk.Label(C1, text=T(self.lang, "hidhide_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=560, justify="left").pack(anchor="w", padx=16, pady=(0, 8))
        st = tk.BooleanVar(value=self.cfg.get("startup", False))
        tk.Checkbutton(C1, text=T(self.lang, "start_with_app"), variable=st, bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD, command=lambda: self._set_setting("startup", st.get())).pack(anchor="w", padx=16, pady=(4, 12))
        D1 = RoundedCard(body)
        D1.pack(fill="x", pady=(0, 12))
        tk.Label(D1, text=T(self.lang, "diagnostics"), bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        tk.Button(D1, text=T(self.lang, "test_ls"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self.engine.trigger_once).pack(anchor="w", padx=16, pady=4)
        tk.Button(D1, text=T(self.lang, "save_settings"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self._save_settings_clicked).pack(anchor="w", padx=16, pady=(4, 12))

    def _toggle_hidhide(self, value):
        self._set_setting("hidhide", value)
        self.engine.apply_hidhide_async()

    def _save_settings_clicked(self):
        save_config(self.cfg)
        self.engine.set_config(self.cfg)
        self._status_callback("settings_saved")

    def _set_setting(self, key, value):
        self.cfg[key] = value
        save_config(self.cfg)
        self.engine.set_config(self.cfg)
        if key == "language":
            self.lang = value
            for w in self.root.winfo_children():
                w.destroy()
            self._build_style()
            self._build_layout()
            self.engine.status_cb = self._status_callback

    def _status_callback(self, key, **kw):
        try:
            text = T(self.lang, key, **kw)
            if text == key:
                text = str(key)
            self.root.after(0, lambda t=text: self.status_label.config(text=t))
        except Exception:
            pass

    def _visual_callback(self, state):
        try:
            self.root.after(0, lambda: self._update_visual(state))
        except Exception:
            pass

    def _update_visual(self, state):
        self.last_visual = state
        try:
            self.conn_value.config(text=T(self.lang, "status_connected") if state.get("connected") else T(self.lang, "status_disconnected"))
            self.profile_value.config(text=state.get("active_profile", self.profile_name))
        except Exception:
            pass
        pressed = state.get("pressed", set())
        c = self.canvas
        try:
            for key in ("A", "B", "X", "Y"):
                on = key in pressed
                c.itemconfig("f" + key, fill=GOLD if on else "#2A3342")
                c.itemconfig("t" + key, fill="#101318" if on else MUTED)
            for key in ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"):
                c.itemconfig("f" + key, fill=GOLD if key in pressed else "#2A3342")
            for key in ("LB", "RB", "LT", "RT", "BACK", "START"):
                on = key in pressed
                c.itemconfig("f" + key, fill=GOLD if on else PANEL)
                c.itemconfig("t" + key, fill="#101318" if on else MUTED)
            lx = float(state.get("lx", 0.0) or 0.0)
            ly = float(state.get("ly", 0.0) or 0.0)
            rx = float(state.get("rx", 0.0) or 0.0)
            ry = float(state.get("ry", 0.0) or 0.0)
            for key, sx, sy, ax, ay in (("LS", 205, 265, lx, ly), ("RS", 355, 265, rx, ry)):
                on = key in pressed
                dx = int(ax * 14)
                dy = -int(ay * 14)
                c.coords("f" + key, sx + dx - 20, sy + dy - 20, sx + dx + 20, sy + dy + 20)
                c.coords("t" + key, sx + dx, sy + dy)
                c.itemconfig("f" + key, fill=GOLD if on else "#2A3342")
                c.itemconfig("t" + key, fill="#101318" if on else MUTED)
            # analog trigger bars (fill grows with the trigger value)
            for tag, val in (("LT", float(state.get("lt", 0.0) or 0.0)),
                             ("RT", float(state.get("rt", 0.0) or 0.0))):
                x0, x1 = (192, 218) if tag == "LT" else (342, 368)
                bottom, top = 146, 114
                h = max(0, int((bottom - top) * max(0.0, min(1.0, val))))
                c.coords("trigfill" + tag, x0, bottom - h, x1, bottom)
                c.itemconfig("trigfill" + tag, fill=GOLD if val > 0.5 else MUTED)
            # stick direction dots
            for key, sx, sy, ax, ay in (("LS", 205, 265, lx, ly), ("RS", 355, 265, rx, ry)):
                dx = int(ax * 10)
                dy = -int(ay * 10)
                c.coords("dot" + key, sx + dx - 3, sy + dy - 3, sx + dx + 3, sy + dy + 3)
            # dim the pad when no controller is connected
            c.config(bg=CARD if state.get("connected") else "#0D1117")
        except Exception:
            pass

    def _poll_visual(self):
        self.root.after(2000, self._poll_visual)

    def on_close(self):
        self.engine.stop()
        self.root.destroy()
class MappingEditor(tk.Toplevel):
    MODE_KEYS = ["hold", "tap", "toggle", "repeat", "threshold"]

    def __init__(self, app, mapping=None, on_save=None):
        super().__init__(app.root)
        self.app = app
        self.lang = app.lang
        self.on_save = on_save
        self.editing = mapping is not None
        self.src = normalize_mapping(mapping) if mapping else default_mapping()
        self.detecting = False
        self.title(T(self.lang, "editor_edit") if self.editing else T(self.lang, "editor_new"))
        self.configure(bg=BG)
        self.geometry("720x670")
        self.minsize(680, 620)
        self.transient(app.root)
        self._vars()
        self._build()
        self._load()
        self._refresh_editor()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        try:
            self.grab_set()
        except Exception:
            pass

    def _vars(self):
        self.var_input = tk.StringVar()
        self.var_action = tk.StringVar()
        self.var_cond = tk.StringVar()
        self.var_mode = tk.StringVar()
        self.var_modifier = tk.StringVar()
        self.var_tap = tk.StringVar()
        self.var_rep_count = tk.StringVar()
        self.var_rep_interval = tk.StringVar()
        self.var_rep_press = tk.StringVar()
        self.var_continuous = tk.BooleanVar()
        self.var_threshold = tk.DoubleVar()
        self.var_seq_count = tk.StringVar()
        self.var_seq_interval = tk.StringVar()
        self.var_delay_enabled = tk.BooleanVar()
        self.var_delay_act = tk.StringVar()
        self.var_delay_deact = tk.StringVar()
        self.var_hold_moving = tk.BooleanVar()

    def _section(self, parent, title_key, row, col, pady=(0, 10), pad=(4, 4)):
        card = RoundedCard(parent)
        card.grid(row=row, column=col, sticky="nsew", pady=pady, padx=pad)
        tk.Label(card, text=T(self.lang, title_key), bg=CARD, fg=GOLD, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        return card

    def _spin(self, parent, var, frm, to, step=1):
        sp = ttk.Spinbox(parent, from_=frm, to=to, increment=step, textvariable=var, width=7)
        return sp

    def _build(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        # ---------- input ----------
        card = self._section(body, "editor_input", 0, 0)
        self.cb_input = ttk.Combobox(card, textvariable=self.var_input, state="readonly", width=28, values=[INPUT_LABELS[k] for k in ALL_INPUTS])
        self.cb_input.pack(anchor="w", padx=14)
        self.cb_input.bind("<<ComboboxSelected>>", lambda e: self._refresh_editor())
        tk.Label(card, text=T(self.lang, "editor_input_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left").pack(anchor="w", padx=14, pady=(6, 2))
        self.btn_detect = tk.Button(card, text=T(self.lang, "editor_detect"), bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=5, command=self._toggle_detect)
        self.btn_detect.pack(anchor="w", padx=14, pady=(4, 2))
        self.lbl_detect = tk.Label(card, text="", bg=CARD, fg=GOLD, font=("Segoe UI", 9, "bold"), wraplength=300, justify="left")
        self.lbl_detect.pack(anchor="w", padx=14, pady=(0, 10))
        # ---------- action ----------
        card = self._section(body, "editor_action", 1, 0)
        self.cb_action = ttk.Combobox(card, textvariable=self.var_action, state="readonly", width=28, values=[ACTION_LABELS[k] for k in ACTION_TARGETS])
        self.cb_action.pack(anchor="w", padx=14)
        tk.Label(card, text=T(self.lang, "editor_action_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left").pack(anchor="w", padx=14, pady=(6, 10))
        # ---------- condition ----------
        card = self._section(body, "editor_condition", 2, 0)
        self.cb_cond = ttk.Combobox(card, textvariable=self.var_cond, state="readonly", width=28)
        self.cb_cond.pack(anchor="w", padx=14)
        self.cb_cond.bind("<<ComboboxSelected>>", lambda e: self._refresh_editor())
        self.lbl_cond_desc = tk.Label(card, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left")
        self.lbl_cond_desc.pack(anchor="w", padx=14, pady=(4, 2))
        self.frame_seq = tk.Frame(card, bg=CARD)
        tk.Label(self.frame_seq, text=T(self.lang, "editor_seq_count"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=2)
        self.sp_seq_count = self._spin(self.frame_seq, self.var_seq_count, 2, 5)
        self.sp_seq_count.grid(row=0, column=1, padx=(8, 0))
        tk.Label(self.frame_seq, text=T(self.lang, "editor_seq_interval"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=2)
        self.sp_seq_interval = self._spin(self.frame_seq, self.var_seq_interval, 50, 2000, 10)
        self.sp_seq_interval.grid(row=1, column=1, padx=(8, 0))
        tk.Label(self.frame_seq, text=T(self.lang, "editor_seq_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=290, justify="left").grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
        # ---------- modifier ----------
        card = self._section(body, "editor_modifier", 3, 0)
        self.cb_modifier = ttk.Combobox(card, textvariable=self.var_modifier, state="readonly", width=28)
        self.cb_modifier.pack(anchor="w", padx=14)
        tk.Label(card, text=T(self.lang, "editor_modifier_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left").pack(anchor="w", padx=14, pady=(6, 10))
        self._build_mode(body)
        self._build_delays(body)
        self._build_bottom()
    def _build_mode(self, body):
        card = self._section(body, "editor_mode", 0, 1)
        for key in self.MODE_KEYS:
            rb = tk.Radiobutton(card, text=T(self.lang, "mode_" + key + "_short"), variable=self.var_mode, value=key,
                                bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD, activeforeground=GOLD,
                                anchor="w", command=self._refresh_editor)
            rb.pack(anchor="w", padx=14, pady=1)
            if key == "threshold":
                self.rb_mode_thresh = rb
        self.lbl_mode_desc = tk.Label(card, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=300, justify="left")
        self.lbl_mode_desc.pack(anchor="w", padx=14, pady=(4, 2))
        self.frame_tap = tk.Frame(card, bg=CARD)
        tk.Label(self.frame_tap, text=T(self.lang, "editor_tap_ms"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).pack(side="left")
        self.sp_tap = self._spin(self.frame_tap, self.var_tap, 20, 5000, 10)
        self.sp_tap.pack(side="left", padx=(8, 0))
        self.frame_repeat = tk.Frame(card, bg=CARD)
        tk.Label(self.frame_repeat, text=T(self.lang, "editor_repeat_count"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=2)
        self.sp_rep_count = self._spin(self.frame_repeat, self.var_rep_count, 1, 20)
        self.sp_rep_count.grid(row=0, column=1, padx=(8, 0))
        tk.Label(self.frame_repeat, text=T(self.lang, "editor_repeat_interval"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=2)
        self.sp_rep_interval = self._spin(self.frame_repeat, self.var_rep_interval, 40, 5000, 10)
        self.sp_rep_interval.grid(row=1, column=1, padx=(8, 0))
        tk.Label(self.frame_repeat, text=T(self.lang, "editor_repeat_press"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=2)
        self.sp_rep_press = self._spin(self.frame_repeat, self.var_rep_press, 20, 5000, 10)
        self.sp_rep_press.grid(row=2, column=1, padx=(8, 0))
        tk.Checkbutton(self.frame_repeat, text=T(self.lang, "editor_continuous"), variable=self.var_continuous,
                       bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        tk.Label(self.frame_repeat, text=T(self.lang, "editor_continuous_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=290, justify="left").grid(row=4, column=0, columnspan=2, sticky="w")
        self.frame_threshold = tk.Frame(card, bg=CARD)
        trow = tk.Frame(self.frame_threshold, bg=CARD)
        trow.pack(fill="x")
        tk.Label(trow, text=T(self.lang, "editor_threshold"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).pack(side="left")
        self.sc_thr = ttk.Scale(trow, from_=5, to=98, orient="horizontal", variable=self.var_threshold, command=lambda v: self._upd_thr_label())
        self.sc_thr.pack(side="left", fill="x", expand=True, padx=8)
        self.lbl_thr = tk.Label(trow, text="", bg=CARD, fg=MUTED, width=4)
        self.lbl_thr.pack(side="right")
        tk.Label(self.frame_threshold, text=T(self.lang, "editor_threshold_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=290, justify="left").pack(anchor="w", pady=(4, 0))
        self.frame_hold_moving = tk.Frame(card, bg=CARD)
        tk.Checkbutton(self.frame_hold_moving, text=T(self.lang, "editor_hold_while_moving"), variable=self.var_hold_moving,
                       bg=CARD, fg=TEXT, selectcolor=PANEL, activebackground=CARD, wraplength=290, justify="left").pack(anchor="w")
        tk.Label(self.frame_hold_moving, text=T(self.lang, "editor_hold_while_moving_help"), bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=290, justify="left").pack(anchor="w")
        self.var_rep_interval.trace_add("write", lambda *a: self._clamp_press())

    def _build_delays(self, body):
        card = self._section(body, "editor_delays", 1, 1)
        tk.Checkbutton(card, text=T(self.lang, "editor_delay_enable"), variable=self.var_delay_enabled, bg=CARD, fg=TEXT,
                       selectcolor=PANEL, activebackground=CARD, command=self._refresh_editor).pack(anchor="w", padx=14)
        tk.Label(card, text=T(self.lang, "editor_delay_activate"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(8, 2))
        self.sp_delay_act = self._spin(card, self.var_delay_act, 0, 3000, 10)
        self.sp_delay_act.pack(anchor="w", padx=14)
        tk.Label(card, text=T(self.lang, "editor_delay_deactivate"), bg=CARD, fg=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(8, 2))
        self.sp_delay_deact = self._spin(card, self.var_delay_deact, 0, 3000, 10)
        self.sp_delay_deact.pack(anchor="w", padx=14, pady=(0, 10))

    def _build_bottom(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14, pady=(2, 12))
        tk.Button(bar, text=T(self.lang, "editor_test"), bg=PANEL, fg=GOLD, relief="flat", padx=12, pady=6, command=self._test).pack(side="left")
        self.lbl_test = tk.Label(bar, text=T(self.lang, "editor_test_info"), bg=BG, fg=MUTED, font=("Segoe UI", 8), wraplength=260, justify="left")
        self.lbl_test.pack(side="left", padx=8)
        tk.Button(bar, text=T(self.lang, "editor_reset"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self._reset).pack(side="left", padx=(10, 0))
        tk.Button(bar, text=T(self.lang, "editor_save"), bg=GOLD, fg="#101318", relief="flat", padx=16, pady=6, command=self._save).pack(side="right")
        tk.Button(bar, text=T(self.lang, "editor_cancel"), bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self._cancel).pack(side="right", padx=(0, 8))

    def _int(self, var, default=0, lo=0, hi=99999):
        try:
            return max(lo, min(hi, int(float(var.get()))))
        except Exception:
            return default

    def _key_from_label(self, label, table, default=""):
        for k, v in table.items():
            if v == label:
                return k
        return default

    def _cond_key(self):
        m = {T(self.lang, "cond_direct"): "direct", T(self.lang, "cond_threshold"): "threshold", T(self.lang, "cond_sequence"): "sequence"}
        return m.get(self.var_cond.get(), "direct")

    def _load(self):
        s = self.src
        self.var_input.set(INPUT_LABELS.get(s.get("input", "A"), "A"))
        self.var_action.set(ACTION_LABELS.get(s.get("action", "B"), "B"))
        self.var_mode.set(s.get("mode", "hold"))
        cond = s.get("condition") or {}
        ctype = cond.get("type", "direct")
        if ctype not in ("direct", "threshold", "sequence"):
            ctype = "direct"
        self.var_cond.set(T(self.lang, {"direct": "cond_direct", "threshold": "cond_threshold", "sequence": "cond_sequence"}[ctype]))
        if s.get("modifier"):
            self.var_modifier.set(INPUT_LABELS.get(s["modifier"], T(self.lang, "editor_modifier_none")))
        else:
            self.var_modifier.set(T(self.lang, "editor_modifier_none"))
        self.var_tap.set(str(int(s.get("tap_ms", 80))))
        r = s.get("repeat") or {}
        self.var_rep_count.set(str(int(r.get("count", 3))))
        self.var_rep_interval.set(str(int(r.get("interval_ms", 300))))
        self.var_rep_press.set(str(int(r.get("press_ms", 60))))
        self.var_continuous.set(bool(r.get("continuous", False)))
        try:
            self.var_threshold.set(float(cond.get("threshold", 0.5)) * 100.0)
        except Exception:
            self.var_threshold.set(50.0)
        self.var_seq_count.set(str(int(cond.get("count", 2))))
        self.var_seq_interval.set(str(int(cond.get("interval_ms", 320))))
        d = s.get("delay") or {}
        self.var_delay_enabled.set(bool(d.get("enabled", False)))
        self.var_delay_act.set(str(int(d.get("activate_ms", 0))))
        self.var_delay_deact.set(str(int(d.get("deactivate_ms", 0))))
        self.var_hold_moving.set(bool(s.get("hold_while_moving", False)))

    def _upd_thr_label(self):
        try:
            self.lbl_thr.config(text="%d%%" % int(float(self.var_threshold.get())))
        except Exception:
            pass

    def _clamp_press(self):
        interval = self._int(self.var_rep_interval, 300, 40, 5000)
        press = self._int(self.var_rep_press, 60, 20, 5000)
        if press > interval - 10:
            self.var_rep_press.set(str(max(20, interval - 10)))

    def _refresh_editor(self):
        key = self._key_from_label(self.var_input.get(), INPUT_LABELS, "A")
        analog = key in ANALOG_INPUTS
        cond_vals = [T(self.lang, "cond_direct"), T(self.lang, "cond_sequence")]
        if analog:
            cond_vals.insert(1, T(self.lang, "cond_threshold"))
        self.cb_cond.configure(values=cond_vals)
        cond_key = self._cond_key()
        if cond_key == "threshold" and not analog:
            cond_key = "direct"
            self.var_cond.set(T(self.lang, "cond_direct"))
        self.rb_mode_thresh.config(state="normal" if analog else "disabled")
        if not analog and self.var_mode.get() == "threshold":
            self.var_mode.set("hold")
        mod_vals = [T(self.lang, "editor_modifier_none")] + [INPUT_LABELS[k] for k in BUTTON_INPUTS]
        self.cb_modifier.configure(values=mod_vals)
        mode = self.var_mode.get()
        for frame in (self.frame_hold_moving, self.frame_tap, self.frame_repeat, self.frame_threshold, self.frame_seq):
            frame.pack_forget()
        if mode == "hold":
            self.frame_hold_moving.pack(anchor="w", padx=14, pady=(2, 6))
        if mode == "tap":
            self.frame_tap.pack(anchor="w", padx=14, pady=(2, 6))
        if mode == "repeat":
            self.frame_repeat.pack(anchor="w", padx=14, pady=(2, 6))
        if mode == "threshold" or cond_key == "threshold":
            self.frame_threshold.pack(anchor="w", padx=14, pady=(2, 6))
        if cond_key == "sequence":
            self.frame_seq.pack(anchor="w", padx=14, pady=(2, 6))
        self.lbl_mode_desc.config(text=T(self.lang, "mode_" + mode + "_desc"))
        self.lbl_cond_desc.config(text=T(self.lang, "cond_" + cond_key + "_desc"))
        self._upd_thr_label()
        state = "normal" if self.var_delay_enabled.get() else "disabled"
        for w in (self.sp_delay_act, self.sp_delay_deact):
            try:
                w.configure(state=state)
            except Exception:
                pass
    def _toggle_detect(self):
        self.detecting = not self.detecting
        self.btn_detect.config(text=T(self.lang, "editor_detect_stop" if self.detecting else "editor_detect"))
        self.lbl_detect.config(text=T(self.lang, "editor_detect_wait") if self.detecting else "")
        if self.detecting:
            self._poll_detect()

    def _poll_detect(self):
        if not self.detecting:
            return
        vis = getattr(self.app, "last_visual", None)
        key = None
        if vis:
            buttons = vis.get("buttons", {})
            for k in BUTTON_INPUTS:
                if buttons.get(k):
                    key = k
                    break
            if key is None:
                try:
                    if float(vis.get("lt", 0.0)) >= 0.5:
                        key = "LT"
                    elif float(vis.get("rt", 0.0)) >= 0.5:
                        key = "RT"
                except Exception:
                    pass
            if key is None:
                try:
                    lx = float(vis.get("lx", 0.0))
                    ly = float(vis.get("ly", 0.0))
                    rx = float(vis.get("rx", 0.0))
                    ry = float(vis.get("ry", 0.0))
                    cands = [("LS_UP", ly), ("LS_DOWN", -ly), ("LS_LEFT", -lx), ("LS_RIGHT", lx),
                             ("RS_UP", ry), ("RS_DOWN", -ry), ("RS_LEFT", -rx), ("RS_RIGHT", rx)]
                    best = max(cands, key=lambda c: c[1])
                    if best[1] >= 0.6:
                        key = best[0]
                except Exception:
                    pass
        if key:
            self.detecting = False
            self.btn_detect.config(text=T(self.lang, "editor_detect"))
            self.lbl_detect.config(text="")
            self.var_input.set(INPUT_LABELS.get(key, key))
            self._refresh_editor()
            return
        self.after(60, self._poll_detect)

    def _collect(self):
        key = self._key_from_label(self.var_input.get(), INPUT_LABELS, "A")
        action = self._key_from_label(self.var_action.get(), ACTION_LABELS, "B")
        mode = self.var_mode.get()
        if mode not in ("hold", "tap", "toggle", "repeat", "threshold"):
            mode = "hold"
        cond_type = self._cond_key()
        if (mode == "threshold" or cond_type == "threshold") and key not in ANALOG_INPUTS:
            messagebox.showerror(T(self.lang, "editor_edit" if self.editing else "editor_new"), T(self.lang, "editor_threshold_needs_analog"), parent=self)
            return None
        m = default_mapping()
        m["input"] = key
        m["action"] = action
        m["mode"] = mode
        m["name"] = self.src.get("name", "")
        m["enabled"] = self.src.get("enabled", True)
        mod_label = self.var_modifier.get()
        m["modifier"] = "" if mod_label == T(self.lang, "editor_modifier_none") else self._key_from_label(mod_label, INPUT_LABELS, "")
        interval = self._int(self.var_rep_interval, 300, 40, 5000)
        press = self._int(self.var_rep_press, 60, 20, max(20, interval - 10))
        m["tap_ms"] = self._int(self.var_tap, 80, 20, 5000)
        try:
            thr = float(self.var_threshold.get()) / 100.0
        except Exception:
            thr = 0.5
        m["condition"] = {
            "type": cond_type,
            "count": self._int(self.var_seq_count, 2, 2, 5),
            "interval_ms": self._int(self.var_seq_interval, 320, 50, 2000),
            "threshold": max(0.05, min(0.98, thr)),
        }
        m["repeat"] = {"count": self._int(self.var_rep_count, 3, 1, 20), "interval_ms": interval, "press_ms": press, "continuous": bool(self.var_continuous.get())}
        m["delay"] = {"enabled": bool(self.var_delay_enabled.get()), "activate_ms": self._int(self.var_delay_act, 0, 0, 3000), "deactivate_ms": self._int(self.var_delay_deact, 0, 0, 3000)}
        m["hold_while_moving"] = bool(self.var_hold_moving.get())
        return m

    def _test(self):
        m = self._collect()
        if m is None:
            return
        ok = False
        try:
            ok = self.app.engine.test_mapping(m)
        except Exception:
            ok = False
        self.lbl_test.config(text=T(self.lang, "editor_test_sent") if ok else T(self.lang, "editor_test_fail"))

    def _save(self):
        m = self._collect()
        if m is None:
            return
        conflict = False
        for other in self.app._current_mappings():
            if self.editing and other.get("id") == self.src.get("id"):
                continue
            o_cond = (other.get("condition") or {}).get("type", "direct")
            if (other.get("input") == m["input"] and (other.get("modifier") or "") == m["modifier"]
                    and o_cond == m["condition"]["type"] and other.get("enabled", True)):
                conflict = True
                break
        if conflict:
            if not messagebox.askyesno(T(self.lang, "editor_conflict_title"), T(self.lang, "editor_conflict"), parent=self):
                return
        self.on_save(m)
        self._close()

    def _reset(self):
        self.src = default_mapping()
        self.editing = False
        self.title(T(self.lang, "editor_new"))
        self._load()
        self._refresh_editor()

    def _cancel(self):
        self._close()

    def _close(self):
        self.detecting = False
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def on_close_window(app):
    app.engine.stop()
    app.root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close_window(app))
    root.mainloop()


if __name__ == "__main__":
    main()
