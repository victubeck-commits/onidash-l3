import os
import sys
import json
import subprocess
import locale
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
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


def config_defaults(lang=None):
    if lang is None:
        loc = locale.getdefaultlocale()[0] or "pt"
        lang = "es" if loc.startswith("es") else "en" if loc.startswith("en") else "pt"
    return {
        "language": lang,
        "controller_index": 0,
        "virtual_controller": True,
        "hidhide": False,
        "startup": False,
        "profile_name": "Default",
        "profiles": [{"name":"Default","description":"Default profile","mappings":[]}],
        "analog": {
            "left": {"deadzone":0.08,"sensitivity":1.0,"curve":1.0,"invert_x":False,"invert_y":False,"threshold":0.78,"hysteresis":0.22},
            "right": {"deadzone":0.08,"sensitivity":1.0,"curve":1.0,"invert_x":False,"invert_y":False,"threshold":0.78,"hysteresis":0.22},
        },
        "triggers": {
            "left": {"deadzone":0.05,"sensitivity":1.0,"invert":False},
            "right": {"deadzone":0.05,"sensitivity":1.0,"invert":False},
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
    if isinstance(a, dict) and isinstance(b, dict):
        for k, v in b.items():
            if k in a:
                _deep_update(a[k], v)
            else:
                a[k] = v
    elif isinstance(a, list):
        a.clear()
        a.extend(b)
    else:
        a = None if False else b


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
    cfg["profile_name"] = cfg["profiles"][0]["name"] if cfg["profiles"] else "Default"


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
        self._hidhide_cli = None
        self._hidhide_cloaked = False
        self._hidhide_paths = []
        self._hidhide_turned_on = False

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

    def _button_value(self, btns, lt, rt, key):
        mapping = {
            "A": btns.get("A", False),
            "B": btns.get("B", False),
            "X": btns.get("X", False),
            "Y": btns.get("Y", False),
            "LB": btns.get("LEFT_SHOULDER", False),
            "RB": btns.get("RIGHT_SHOULDER", False),
            "L3": btns.get("LEFT_THUMB", False),
            "R3": btns.get("RIGHT_THUMB", False),
            "Start": btns.get("START", False),
            "Back": btns.get("BACK", False),
            "DPAD_UP": btns.get("DPAD_UP", False),
            "DPAD_DOWN": btns.get("DPAD_DOWN", False),
            "DPAD_LEFT": btns.get("DPAD_LEFT", False),
            "DPAD_RIGHT": btns.get("DPAD_RIGHT", False),
            "LT": lt >= 0.5,
            "RT": rt >= 0.5,
            "LS": False,
            "RS": False,
        }
        return bool(mapping.get(key, False))

    def _hidhide_collect_paths(self):
        cli = self._hidhide_cli if hasattr(self, "_hidhide_cli") else find_hidhide_cli()
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
        paths = set()
        containers = data if isinstance(data, list) else [data]
        for cont in containers:
            devices = cont.get("devices", []) if isinstance(cont, dict) else []
            for dev in devices:
                if not isinstance(dev, dict):
                    continue
                friendly = (" " + str(cont.get("friendlyName", "")) + " " + " ".join(str(dev.get(k, "")) for k in ("description", "vendor", "product"))).lower()
                if not ("xbox" in friendly or "xinput" in friendly or str(dev.get("vendor")).lower().find("0x45e") >= 0):
                    continue
                for key in ("deviceInstancePath", "baseContainerDeviceInstancePath", "xusbDeviceInstancePath"):
                    v = dev.get(key)
                    if v:
                        paths.add(v)
        return list(paths)

    def _hidhide_cloak(self, cfg):
        if not cfg.get("hidhide", False):
            return
        cli = find_hidhide_cli()
        if not cli:
            return
        self._hidhide_cli = cli
        code, out, err = run_hidhide(cli, "--cloak-state")
        self._hidhide_turned_on = ("--cloak-off" in (out or ""))
        self._hidhide_paths = self._hidhide_collect_paths()
        if not self._hidhide_paths:
            return
        args = []
        for p in self._hidhide_paths:
            args += ["--dev-hide", p]
        args += ["--cloak-on"]
        run_hidhide(cli, *args)
        self._hidhide_cloaked = True

    def _hidhide_uncloak(self):
        cli = self._hidhide_cli or find_hidhide_cli()
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
        self.status_cb("starting")
        with self._lock:
            cfg0 = json.loads(json.dumps(self.cfg))
        if cfg0.get("hidhide", False):
            self._hidhide_cloak(cfg0)
        profile_name = self.cfg.get("profile_name", "Default")
        active_profile = None
        for p in self.cfg.get("profiles", []):
            if p.get("name") == profile_name:
                active_profile = p
                break
        if active_profile is None and self.cfg.get("profiles"):
            active_profile = self.cfg["profiles"][0]
        mappings = active_profile.get("mappings", []) if active_profile else self.cfg.get("mappings", [])
        vgpad = None
        try:
            vgpad = self._ensure_vg()
        except Exception as e:
            self.status_cb("virtual_error", e=e)
            self._hidhide_uncloak()
            return
        connected_once = False
        mapping_state = {}
        pressed_for_visual = set()
        last_mapping_time = time.perf_counter()
        while self._running:
            with self._lock:
                cfg = json.loads(json.dumps(self.cfg))
            idx = max(0, min(3, int(cfg.get("controller_index", 0))))
            poll = max(0.004, int(cfg.get("poll_ms", 8)) / 1000.0)
            connected_list = XInput.get_connected()
            real_ok = bool(connected_list[idx]) if idx < len(connected_list) else False
            if not real_ok:
                if connected_once:
                    self.status_cb("real_disconnected", idx=idx)
                else:
                    self.status_cb("waiting_real", idx=idx)
                try:
                    vgpad.reset()
                    vgpad.update()
                except Exception:
                    pass
                time.sleep(0.3)
                continue
            connected_once = True
            try:
                st = XInput.get_state(idx)
                left, right = XInput.get_thumb_values(st)
                (lx, ly), (rx, ry) = left, right
                lt, rt = XInput.get_trigger_values(st)
                btns = XInput.get_button_values(st)
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

            # update mapping values
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
            self._state.setdefault("mappings", {})
            states = self._state["mappings"]
            injected = {}
            pressed_for_visual = set()
            # pass through pressed buttons
            if btns.get("A"): pressed_for_visual.add("A")
            if btns.get("B"): pressed_for_visual.add("B")
            if btns.get("X"): pressed_for_visual.add("X")
            if btns.get("Y"): pressed_for_visual.add("Y")
            # mapping eval
            for m in mappings:
                if not m.get("enabled", True):
                    continue
                mid = m.get("id", id(m))
                st = states.setdefault(mid, {"tap": 0, "last": 0, "active": False, "toggled": False})
                input_key = m.get("input", "")
                trigger = m.get("trigger", {})
                action = m.get("action", {})
                # input pressed
                input_pressed = False
                if input_key == "left_stick_forward":
                    input_pressed = ly >= cfg.get("analog", {}).get("left", {}).get("threshold", 0.78)
                elif input_key == "LS":
                    input_pressed = bool(btns.get("LEFT_THUMB", False))
                elif input_key == "RS":
                    input_pressed = bool(btns.get("RIGHT_THUMB", False))
                elif input_key in ("LT", "RT"):
                    input_pressed = (lt if input_key == "LT" else rt) >= 0.5
                elif input_key == "button":
                    input_pressed = self._button_value(btns, lt, rt, m.get("button", "A"))
                trap = input_pressed
                # trigger allowed
                allowed = False
                if trigger.get("type", "tap") == "instant":
                    allowed = trap
                elif trigger.get("type") == "hold":
                    if trap:
                        allowed = True
                    else:
                        allowed = False
                elif trigger.get("type") == "tap":
                    count = int(trigger.get("tap_count", 2))
                    interval = float(trigger.get("interval_ms", 320)) / 1000.0
                    if trap and not st.get("input_down", False):
                        if st.get("last", 0) and now - st["last"] <= interval:
                            st["tap"] += 1
                        else:
                            st["tap"] = 1
                        st["last"] = now
                        if st["tap"] >= count:
                            st["tap"] = 0
                            st["activated_at"] = now
                            allowed = True
                    if not trap:
                        st["tap"] = st["tap"] if (st.get("last", 0) and now - st["last"] <= interval) else 0
                elif trigger.get("type") == "threshold":
                    thr = float(trigger.get("threshold", 0.78))
                    allowed = abs(ly if input_key == "left_stick_forward" else 0.0) >= thr
                st["input_down"] = trap
                # activation delay
                delay_act = float(trigger.get("delay_activate_ms", 0)) / 1000.0 if trigger.get("delay_enabled", False) else 0.0
                delay_de = float(trigger.get("delay_deactivate_ms", 0)) / 1000.0 if trigger.get("delay_enabled", False) else 0.0
                hold = float(trigger.get("hold_ms", 130)) / 1000.0
                now = time.perf_counter()
                # mode taps to inject
                if allowed:
                    if trigger.get("type") == "tap":
                        st["active_until"] = now + delay_act + hold
                        st["active_after"] = now + delay_act
                        self._dash_count += 1
                    else:
                        if "active_until" not in st:
                            st["active_until"] = now + hold
                            st["active_after"] = now + delay_act
                # toggle handling
                mode = action.get("mode", "tap")
                target = action.get("target", "LS")
                if mode == "toggle" and allowed:
                    st["toggled"] = not st.get("toggled", False)
                # inject
                is_active = st.get("active_after", 0) <= now < st.get("active_until", 0)
                if mode == "hold":
                    is_active = trap if trigger.get("type") in ("hold", "threshold", "instant") else is_active
                if mode == "toggle":
                    is_active = st.get("toggled", False)
                if mode == "repeat":
                    is_active = allowed
                if is_active:
                    injected[target] = injected.get(target, 0) or 1
                    pressed_for_visual.add(target)
                    if delay_de and not trap:
                        st["active_until"] = max(st.get("active_until", now), now + delay_de)
                if "active_until" in st and mode == "hold" and trap and delay_de > 0:
                    st["active_until"] = max(st["active_until"], now + 0.06)
            # write virtual
            try:
                vgpad.left_joystick(int(lx_o * 32767), int(ly_o * 32767))
                vgpad.right_joystick(int(rx_o * 32767), int(ry_o * 32767))
                vgpad.left_trigger(int(max(0, min(1, lt_o)) * 255))
                vgpad.right_trigger(int(max(0, min(1, rt_o)) * 255))
                # pass-through buttons
                for name, xbtn in {
                    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                }.items():
                    if btns.get(name, False):
                        vgpad.press_button(xbtn)
                    else:
                        vgpad.release_button(xbtn)
                if btns.get("LEFT_SHOULDER", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
                if btns.get("RIGHT_SHOULDER", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
                if btns.get("START", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_START)
                if btns.get("BACK", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
                if btns.get("DPAD_UP", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                if btns.get("DPAD_DOWN", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                if btns.get("DPAD_LEFT", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
                if btns.get("DPAD_RIGHT", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
                # LS/RS base mirroring
                if btns.get("LEFT_THUMB", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
                if btns.get("RIGHT_THUMB", False):
                    vgpad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)
                else:
                    vgpad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)
                # injected overrides
                target_map = {
                    "LS": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
                    "RS": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
                    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
                    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
                    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                    "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
                    "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
                    "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
                }
                for target, val in injected.items():
                    if target in target_map:
                        if val:
                            vgpad.press_button(target_map[target])
                        else:
                            pass
                vgpad.update()
            except Exception as e:
                self.status_cb("virtual_error", e=e)
                time.sleep(0.1)
                continue
            try:
                self.visual_cb({
                    "connected": True,
                    "pressed": pressed_for_visual,
                    "ly": ly,
                    "lx": lx,
                    "active_profile": cfg.get("profile_name", "Default"),
                })
            except Exception:
                pass
            time.sleep(poll)


class ProfileManager:
    pass


class RoundedCard(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, **kwargs)


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.lang = self.cfg.get("language", detect_language())
        self.profile_name = self.cfg.get("profile_name", "Default")
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
        style.configure("TCombobox", fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER, padding=6)
        style.configure("TSpinbox", fieldbackground=CARD, background=CARD, foreground=TEXT, bordercolor=BORDER)
        style.configure("TCheckbutton", background=BG, foreground=TEXT)
        style.configure("TLabelframe", background=BG, foreground=TEXT)
        style.configure("TLabelframe.Label", background=BG, foreground=GOLD, font=("Segoe UI", 11, "bold"))
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT, bordercolor=BORDER, rowheight=34)
        style.configure("Treeview.Heading", background=PANEL, foreground=GOLD, font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#2A3446")])

    def _build_layout(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        # sidebar
        self.sidebar = tk.Frame(self.root, bg=PANEL, width=210)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        # top bar
        self.topbar = tk.Frame(self.root, bg=BG, height=56)
        self.topbar.grid(row=0, column=1, sticky="new")
        self.topbar.grid_propagate(False)
        self.content_host = tk.Frame(self.root, bg=BG)
        self.content_host.grid(row=0, column=1, sticky="nsew", pady=(56, 0))
        # pages
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
        subtitle = tk.Label(self.sidebar, text="Universal Controller", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        subtitle.pack(anchor="w", padx=18, pady=(0, 16))
        self.status_label = tk.Label(self.sidebar, text="Stopped", bg=PANEL, fg=DANGER, font=("Segoe UI", 9, "bold"))
        self.status_label.pack(anchor="w", padx=18, pady=(0, 14))
        for key, label in [("home", "Home"), ("mapping", "Mapping"), ("analog", "Analogs"), ("triggers", "Triggers"), ("profiles", "Profiles"), ("settings", "Settings")]:
            btn = tk.Button(self.sidebar, text=label, bg=PANEL, fg=TEXT, relief="flat", anchor="w", padx=18, pady=10,
                            activebackground=CARD, activeforeground=GOLD, command=lambda k=key: self._show_page(k))
            btn.pack(fill="x")

    def _show_page(self, name):
        self.pages[name].tkraise()

    def _build_home(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        header = tk.Label(parent, text="Home", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        # visual controller
        self.canvas = tk.Canvas(body, bg=CARD, highlightthickness=0, width=560, height=360)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._draw_controller()
        # info cards
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.card_profile = RoundedCard(right)
        self.card_profile.pack(fill="x", pady=(0, 12))
        tk.Label(self.card_profile, text="Active Profile", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        self.profile_value = tk.Label(self.card_profile, text=self.profile_name, bg=CARD, fg=GOLD, font=("Segoe UI", 16, "bold"))
        self.profile_value.pack(anchor="w", padx=16, pady=(0, 12))
        self.card_conn = RoundedCard(right)
        self.card_conn.pack(fill="x", pady=(0, 12))
        tk.Label(self.card_conn, text="Controller Status", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        self.conn_value = tk.Label(self.card_conn, text="Checking...", bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"))
        self.conn_value.pack(anchor="w", padx=16, pady=(0, 12))
        self.card_mapper = RoundedCard(right)
        self.card_mapper.pack(fill="x")
        tk.Label(self.card_mapper, text="Quick Actions", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(12, 0))
        for lbl, page in [("Open Mapping", "mapping"), ("Edit Analogs", "analog"), ("Profiles", "profiles")]:
            b = tk.Button(self.card_mapper, text=lbl, bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=lambda p=page: self._show_page(p))
            b.pack(fill="x", padx=16, pady=4)
        tk.Frame(self.card_mapper, bg=CARD, height=8).pack()

    def _draw_controller(self):
        c = self.canvas
        c.delete("all")
        # body
        c.create_oval(180, 60, 380, 300, fill="#1A202A", outline=BORDER, width=2)
        c.create_rectangle(230, 90, 330, 270, fill="#1A202A", outline=BORDER, width=0)
        # dpad
        c.create_rectangle(210, 150, 260, 165, fill="#2A3342", outline=BORDER)
        c.create_rectangle(230, 130, 245, 180, fill="#2A3342", outline=BORDER)
        # abxy
        c.create_oval(315, 135, 345, 165, fill="#2A3342", outline=BORDER, tags="B")
        c.create_oval(345, 165, 375, 195, fill="#2A3342", outline=BORDER, tags="A")
        c.create_oval(285, 165, 315, 195, fill="#2A3342", outline=BORDER, tags="X")
        c.create_oval(315, 195, 345, 225, fill="#2A3342", outline=BORDER, tags="Y")
        # sticks
        c.create_oval(205, 195, 245, 235, fill="#10151D", outline=BORDER)
        c.create_oval(295, 235, 335, 275, fill="#10151D", outline=BORDER)
        c.create_text(330, 150, text="B", fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_text(360, 180, text="A", fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_text(300, 180, text="X", fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_text(330, 210, text="Y", fill=MUTED, font=("Segoe UI", 9, "bold"))

    def _build_mapping(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        header = tk.Label(parent, text="Mapping", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        for text, cmd in [("Add Mapping", self._add_mapping), ("Edit", self._edit_mapping), ("Duplicate", self._duplicate_mapping), ("Remove", self._remove_mapping)]:
            tk.Button(toolbar, text=text, bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=cmd).pack(side="left", padx=(0, 8))
        self.map_tree = ttk.Treeview(parent, columns=("input", "action", "mode", "configure"), show="headings", height=16)
        for col, head in (("input", "Physical Input"), ("action", "Assigned Action"), ("mode", "Mode"), ("configure", "Configure")):
            self.map_tree.heading(col, text=head)
            self.map_tree.column(col, width=260 if col in ("input", "action") else 160)
        self.map_tree.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 16))
        parent.rowconfigure(2, weight=1)
        btn_refresh = tk.Button(parent, text="Refresh", bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self._refresh_mappings)
        btn_refresh.grid(row=3, column=0, sticky="w", padx=24, pady=(0, 16))
        self._refresh_mappings()

    def _build_analog(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text="Analogs", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        container = tk.Frame(parent, bg=BG)
        container.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        for side, col in (("left", 0), ("right", 1)):
            card = RoundedCard(container)
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0 if col == 1 else 8))
            tk.Label(card, text=side.title() + " Stick", bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
            cfg = self.cfg["analog"][side]
            for label, key, frm, to in [("Deadzone", "deadzone", 0, 50), ("Sensitivity x100", "sensitivity", 25, 250), ("Curve x100", "curve", 25, 300), ("Threshold x100", "threshold", 25, 98)]:
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=16, pady=4)
                tk.Label(row, text=label, bg=CARD, fg=TEXT, width=20, anchor="w").pack(side="left")
                var = tk.IntVar(value=int(cfg[key] * (1 if key == "deadzone" or key == "threshold" else (100 if key in ("sensitivity", "curve") else 1))))
                # careful: keep value usable
                sc = ttk.Scale(row, from_=frm, to=to, orient="horizontal", variable=var)
                sc.pack(side="left", fill="x", expand=True, padx=8)
                val = tk.Label(row, text=str(cfg[key]), bg=CARD, fg=MUTED, width=6)
                val.pack(side="right")
                cfg[key] = cfg[key]
            for opt in ("invert_x", "invert_y"):
                var = tk.BooleanVar(value=cfg.get(opt, False))
                tk.Checkbutton(card, text=opt.replace("_", " ").title(), variable=var, bg=CARD, fg=TEXT, selectcolor=PANEL, command=lambda s=side, o=opt, v=var: self._set_analog(s, o, v.get())).pack(anchor="w", padx=16, pady=2)
        tk.Label(container, text="Changes apply to active configuration.", bg=BG, fg=MUTED, font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _set_analog(self, side, key, value):
        self.cfg["analog"][side][key] = value
        save_config(self.cfg)

    def _build_triggers(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text="Triggers", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        for side in ("left", "right"):
            card = RoundedCard(body)
            card.pack(fill="x", pady=(0, 12))
            tk.Label(card, text=side.title() + " Trigger", bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
            cfg = self.cfg["triggers"][side]
            for label, key in (("Deadzone", "deadzone"), ("Sensitivity", "sensitivity")):
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=16, pady=4)
                tk.Label(row, text=label, bg=CARD, fg=TEXT, width=16, anchor="w").pack(side="left")
                var = tk.IntVar(value=int(cfg.get(key, 0.05) * 100))
                scale = ttk.Scale(row, from_=0 if key == "deadzone" else 25, to=100 if key == "deadzone" else 250, orient="horizontal", variable=var)
                scale.pack(side="left", fill="x", expand=True, padx=8)
                tk.Label(row, text=str(var.get()), bg=CARD, fg=MUTED, width=4).pack(side="right")
                scale.configure(command=lambda v, s=side, k=key, va=var, lab=None: self._set_trigger(s, k, va.get() / (100.0 if k == "deadzone" else 100.0)))
            inv = tk.BooleanVar(value=cfg.get("invert", False))
            tk.Checkbutton(card, text="Invert", variable=inv, bg=CARD, fg=TEXT, selectcolor=PANEL, command=lambda s=side, v=inv: self._set_trigger(s, "invert", v.get())).pack(anchor="w", padx=16, pady=6)

    def _set_trigger(self, side, key, value):
        self.cfg["triggers"][side][key] = value
        save_config(self.cfg)

    def _build_profiles(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text="Profiles", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))
        for text, cmd in [("New", self._new_profile), ("Duplicate", self._duplicate_profile), ("Import", self._import_profile), ("Export", self._export_profile)]:
            tk.Button(toolbar, text=text, bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=cmd).pack(side="left", padx=(0, 8))
        self.profile_cards = tk.Frame(parent, bg=BG)
        self.profile_cards.grid(row=2, column=0, sticky="nsew", padx=24, pady=10)
        parent.rowconfigure(2, weight=1)
        self._refresh_profiles()

    def _refresh_profiles(self):
        for w in self.profile_cards.winfo_children():
            w.destroy()
        for prof in self.cfg.get("profiles", []):
            card = RoundedCard(self.profile_cards)
            card.pack(fill="x", pady=(0, 10))
            tk.Label(card, text=prof.get("name", "Profile"), bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
            tk.Label(card, text=prof.get("description", ""), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 8))
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=16, pady=(0, 12))
            tk.Button(row, text="Use", bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=4, command=lambda p=prof: self._use_profile(p)).pack(side="left", padx=(0, 6))
            tk.Button(row, text="Edit", bg=PANEL, fg=TEXT, relief="flat", padx=10, pady=4, command=lambda p=prof: self._edit_profile(p)).pack(side="left", padx=(0, 6))
            tk.Button(row, text="Delete", bg=PANEL, fg=DANGER, relief="flat", padx=10, pady=4, command=lambda p=prof: self._delete_profile(p)).pack(side="left")

    def _use_profile(self, prof):
        self.cfg["profile_name"] = prof.get("name")
        self.profile_name = prof.get("name")
        self.profile_value.config(text=self.profile_name)
        save_config(self.cfg)

    def _new_profile(self):
        name = "Profile " + str(len(self.cfg.get("profiles", [])) + 1)
        prof = {"name": name, "description": "New profile", "mappings": []}
        self.cfg.setdefault("profiles", []).append(prof)
        self._use_profile(prof)
        self._refresh_profiles()

    def _duplicate_profile(self):
        if not self.cfg.get("profiles"):
            return
        src = self.cfg["profiles"][-1]
        prof = {"name": src.get("name", "Profile") + " Copy", "description": src.get("description", ""), "mappings": [dict(m) for m in src.get("mappings", [])]}
        self.cfg["profiles"].append(prof)
        self._refresh_profiles()

    def _edit_profile(self, prof):
        name = tk.simpledialog.askstring("Edit Profile", "Name", initialvalue=prof.get("name", ""), parent=self.root)
        if name:
            prof["name"] = name
            desc = tk.simpledialog.askstring("Edit Profile", "Description", initialvalue=prof.get("description", ""), parent=self.root)
            if desc is not None:
                prof["description"] = desc
            self._refresh_profiles()
            save_config(self.cfg)

    def _delete_profile(self, prof):
        if len(self.cfg.get("profiles", [])) <= 1:
            messagebox.showwarning("Profiles", "Cannot delete the last profile.")
            return
        self.cfg["profiles"] = [p for p in self.cfg["profiles"] if p is not prof]
        self._refresh_profiles()
        save_config(self.cfg)

    def _import_profile(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "name" not in data or "mappings" not in data:
                raise ValueError("Invalid profile")
            self.cfg.setdefault("profiles", []).append(data)
            self._refresh_profiles()
            save_config(self.cfg)
        except Exception as e:
            messagebox.showerror("Import", str(e))

    def _export_profile(self):
        profile = None
        for p in self.cfg.get("profiles", []):
            if p.get("name") == self.cfg.get("profile_name", ""):
                profile = p
                break
        if profile is None and self.cfg.get("profiles"):
            profile = self.cfg["profiles"][0]
        if not profile:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Export", str(e))

    def _build_settings(self, parent):
        parent.columnconfigure(0, weight=1)
        header = tk.Label(parent, text="Settings", bg=BG, fg=LIGHT, font=("Segoe UI", 18, "bold"))
        header.grid(row=0, column=0, sticky="w", padx=24, pady=(20, 10))
        body = tk.Frame(parent, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=10)
        # language
        L1 = RoundedCard(body)
        L1.pack(fill="x", pady=(0, 12))
        tk.Label(L1, text="Language", bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        lang = ttk.Combobox(L1, values=["Portugues", "English", "Espanol"], state="readonly", width=28)
        lang.set({"pt": "Portugues", "en": "English", "es": "Espanol"}.get(self.lang, "Portugues"))
        lang.pack(anchor="w", padx=16, pady=(0, 12))
        lang.bind("<<ComboboxSelected>>", lambda e: self._set_setting("language", {"Portugues": "pt", "English": "en", "Espanol": "es"}.get(lang.get(), self.lang)))
        # controller
        C1 = RoundedCard(body)
        C1.pack(fill="x", pady=(0, 12))
        tk.Label(C1, text="Controller And Virtual", bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        dev_row = tk.Frame(C1, bg=CARD)
        dev_row.pack(fill="x", padx=16, pady=4)
        tk.Label(dev_row, text="XInput Slot", bg=CARD, fg=TEXT).pack(side="left")
        sc = ttk.Spinbox(dev_row, from_=0, to=3, width=6)
        sc.set(self.cfg.get("controller_index", 0))
        sc.pack(side="right")
        sc.bind("<FocusOut>", lambda e: self._set_setting("controller_index", int(sc.get())))
        vc = tk.BooleanVar(value=self.cfg.get("virtual_controller", True))
        tk.Checkbutton(C1, text="Create virtual controller", variable=vc, bg=CARD, fg=TEXT, selectcolor=PANEL, command=lambda: self._set_setting("virtual_controller", vc.get())).pack(anchor="w", padx=16, pady=4)
        hh = tk.BooleanVar(value=self.cfg.get("hidhide", False))
        tk.Checkbutton(C1, text="Use HidHide (hide real controller)", variable=hh, bg=CARD, fg=TEXT, selectcolor=PANEL, command=lambda: self._set_setting("hidhide", hh.get())).pack(anchor="w", padx=16, pady=4)
        st = tk.BooleanVar(value=self.cfg.get("startup", False))
        tk.Checkbutton(C1, text="Start engine with app", variable=st, bg=CARD, fg=TEXT, selectcolor=PANEL, command=lambda: self._set_setting("startup", st.get())).pack(anchor="w", padx=16, pady=(4, 12))
        # diagnostics
        D1 = RoundedCard(body)
        D1.pack(fill="x", pady=(0, 12))
        tk.Label(D1, text="Diagnostics", bg=CARD, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        tk.Button(D1, text="Test LS Click", bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=self.engine.trigger_once).pack(anchor="w", padx=16, pady=4)
        tk.Button(D1, text="Save Settings", bg=PANEL, fg=TEXT, relief="flat", padx=12, pady=6, command=lambda: save_config(self.cfg)).pack(anchor="w", padx=16, pady=(4, 12))

    def _set_setting(self, key, value):
        self.cfg[key] = value
        save_config(self.cfg)
        self.engine.set_config(self.cfg)
        if key == "language":
            self.lang = value
            self.status_label.config(text="Language changed")

    def _add_mapping(self):
        mappings = self.cfg.setdefault("mappings", [])
        mappings.append({"id": len(mappings)+1, "enabled": True, "name": "New Mapping", "input": "A", "trigger": {"type": "tap", "tap_count": 2, "interval_ms": 300, "threshold": 0.78, "hold_ms": 130, "delay_enabled": False, "delay_activate_ms": 0, "delay_deactivate_ms": 0}, "action": {"type": "button", "target": "A", "mode": "hold"}})
        save_config(self.cfg)
        self._refresh_mappings()

    def _edit_mapping(self):
        item = self.map_tree.selection()
        if not item:
            return
        idx = int(item[0])
        mapping = self.cfg.get("mappings", [])[idx]
        name = tk.simpledialog.askstring("Edit", "Name", initialvalue=mapping.get("name", ""), parent=self.root)
        if name is not None:
            mapping["name"] = name
            inp = tk.simpledialog.askstring("Edit", "Input (A,B,X,Y,LS,RS,LT,RT,LS_forward,etc)", initialvalue=mapping.get("input", "A"), parent=self.root)
            if inp is not None:
                mapping["input"] = inp
            target = tk.simpledialog.askstring("Edit", "Action target (A,B,X,Y,LS,RS,LB,RB,START,BACK)", initialvalue=mapping.get("action", {}).get("target", "A"), parent=self.root)
            if target is not None:
                mapping.setdefault("action", {})["target"] = target
            mode = tk.simpledialog.askstring("Edit", "Mode (hold/tap/toggle/repeat)", initialvalue=mapping.get("action", {}).get("mode", "hold"), parent=self.root)
            if mode is not None:
                mapping["action"]["mode"] = mode
            save_config(self.cfg)
            self._refresh_mappings()

    def _duplicate_mapping(self):
        item = self.map_tree.selection()
        if not item:
            return
        idx = int(item[0])
        src = self.cfg.get("mappings", [])[idx]
        new = {k: (v if not isinstance(v, (dict, list)) else ([x if not isinstance(x, dict) else dict(x) for x in v] if isinstance(v, list) else dict(v))) for k, v in src.items()}
        new["id"] = len(self.cfg.get("mappings", [])) + 1
        new["name"] = src.get("name", "Mapping") + " Copy"
        self.cfg.setdefault("mappings", []).append(new)
        save_config(self.cfg)
        self._refresh_mappings()

    def _remove_mapping(self):
        item = self.map_tree.selection()
        if not item:
            return
        idx = int(item[0])
        del self.cfg["mappings"][idx]
        save_config(self.cfg)
        self._refresh_mappings()

    def _refresh_mappings(self):
        for i in self.map_tree.get_children():
            self.map_tree.delete(i)
        for idx, m in enumerate(self.cfg.get("mappings", [])):
            self.map_tree.insert("", "end", iid=str(idx), values=(m.get("input", ""), m.get("name", ""), m.get("action", {}).get("mode", ""), "Edit"))

    def _status_callback(self, key, **kw):
        text = T(self.lang, key, **kw) if key in T(self.lang, key) or True else key
        try:
            if isinstance(key, str) and key in ("starting", "waiting_real", "real_disconnected", "reading_error", "virtual_error", "stopped", "active_slot", "running_hold", "running_dash", "error_virtual", "hidhide_not_found", "hidhide_no_device", "hidhide_cloaked", "hidhide_error"):
                text = T(self.lang, key, **kw)
            else:
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
        self.conn_value.config(text="Connected" if state.get("connected") else "Disconnected")
        self.profile_value.config(text=state.get("active_profile", self.profile_name))
        pressed = state.get("pressed", set())
        for button in ("A", "B", "X", "Y"):
            color = GOLD if button in pressed else "#2A3342"
            try:
                self.canvas.itemconfig(button, fill=color)
            except Exception:
                pass

    def _poll_visual(self):
        # placeholder for periodic updates
        self.root.after(2000, self._poll_visual)

    def on_close(self):
        self.engine.stop()
        self.root.destroy()

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