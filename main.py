#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EkranKayıt Pro - Gelişmiş Ekran Kaydedici (Ayrı Araç Paneli + Çizim Düzeltmeli Sürüm)
Kurulum: pip install customtkinter pillow numpy opencv-python mss pyaudio pyautogui pygame
"""
import sys, os, threading, time, shutil, subprocess, wave, math, json, struct
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from ImageToVideoModule import ImageToVideoEditor
from AudioEffectsModule import AudioEffectsTab
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    import numpy as np
    import cv2
    import mss as mss_lib
except ImportError as e:
    print(f"Eksik kütüphane: {e}\npip install customtkinter pillow numpy opencv-python mss pyaudio pyautogui")
    sys.exit(1)

try:
    import pyaudio
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    CURSOR_OK = True
except Exception:
    CURSOR_OK = False
    pyautogui = None

try:
    from pynput import keyboard as _pyn_kb
    HOTKEY_OK = True
except ImportError:
    HOTKEY_OK = False
    _pyn_kb = None

# 🔊 ÖNİZLEME SESİ İÇİN PYGAME
try:
    import pygame
    pygame.mixer.init()
    AUDIO_PLAY_OK = True
except Exception:
    AUDIO_PLAY_OK = False

# ──────────────────────────────────────────────────────────────
#  TEMA & SABİTLER
# ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
BG      = "#0d1117"
CARD    = "#161b22"
CARD2   = "#1c2128"
BORDER  = "#30363d"
ACCENT  = "#238636"
ACCENT2 = "#1f538d"
RED     = "#da3633"
YELLOW  = "#d29922"
PURPLE  = "#8b5cf6"
TXT     = "#e6edf3"
TXT2    = "#8b949e"
FPS_DEF = 30
RATE    = 44100
CHUNK   = 1024

# ──────────────────────────────────────────────────────────────
#  YARDIMCI: Windows'ta ffmpeg konsol penceresi açılmasını engeller
# ──────────────────────────────────────────────────────────────
def _no_window():
    """
    Windows'ta subprocess çağrılarında konsol penceresi açılmasını engeller.
    -noconsole ile derlenmiş .exe dosyalarında da geçerlidir.
    Diğer platformlarda boş dict döner, herhangi bir etkisi olmaz.
    """
    if os.name == 'nt':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {
            'startupinfo': si,
            'creationflags': subprocess.CREATE_NO_WINDOW,
        }
    return {}
TOOLS   = ["mouse", "rectangle", "circle", "arrow", "line", "freehand", "text", "eraser"]
TOOL_ICONS = {"mouse":"🖱️", "rectangle":"▭","circle":"○","arrow":"➜","line":"╱","freehand":"✏","text":"T","eraser":"⌫"}

# ──────────────────────────────────────────────────────────────
#  COLLAPSIBLE SECTIONS FOR RESPONSIVE LAYOUT
# ──────────────────────────────────────────────────────────────
class CollapsibleSection(ctk.CTkFrame):
    """A collapsible section that saves vertical space on small screens."""
    def __init__(self, parent, title, emoji="📂", initial_state=True, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._collapsed = not initial_state
        self._content_frame = None

        # Header with toggle button
        self._header = ctk.CTkFrame(self, fg_color=CARD2, corner_radius=6)
        self._header.pack(fill="x", pady=(2, 0))
        self._header.bind("<Button-1>", lambda e: self._toggle())

        self._toggle_btn = ctk.CTkButton(
            self._header, text=f"{'▶' if not initial_state else '▼'} {emoji} {title}",
            font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT,
            fg_color="transparent", hover_color=CARD,
            command=self._toggle, width=80, height=28
        )
        self._toggle_btn.pack(side="left", padx=8, pady=4)

        # Content container
        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if initial_state:
            self._content_frame.pack(fill="x", pady=2)

    def _toggle(self):
        if self._collapsed:
            self._content_frame.pack(fill="x", pady=2)
            self._toggle_btn.configure(text=f"▼ {self._toggle_btn.cget('text')[2:]}")
            self._collapsed = False
        else:
            self._content_frame.pack_forget()
            self._toggle_btn.configure(text=f"▶ {self._toggle_btn.cget('text')[2:]}")
            self._collapsed = True

    def get_content_frame(self):
        return self._content_frame

# ──────────────────────────────────────────────────────────────
#  YARDIMCI: ffmpeg kontrolü
# ──────────────────────────────────────────────────────────────
def has_ffmpeg():
    try:
        subprocess.run(["ffmpeg","-version"], capture_output=True, timeout=3, **_no_window())
        return True
    except:
        return False
FFMPEG = has_ffmpeg()

def _corner_pos(pos_str: str, obj_w: int, obj_h: int, canvas_W: int, canvas_H: int, margin: int = 16):
    """'top-left/top-right/bottom-left/bottom-right/center' konumunu piksel koordinatına çevirir."""
    if   pos_str == "top-left":     return (margin,                   margin)
    elif pos_str == "top-right":    return (canvas_W - obj_w - margin, margin)
    elif pos_str == "bottom-left":  return (margin,                   canvas_H - obj_h - margin)
    elif pos_str == "center":       return ((canvas_W - obj_w) // 2,  (canvas_H - obj_h) // 2)
    else:                           return (canvas_W - obj_w - margin, canvas_H - obj_h - margin)

# ──────────────────────────────────────────────────────────────
#  WEBCAM THREAD SINIFI
# ──────────────────────────────────────────────────────────────
class WebcamVideoStream:
    """Kamerayı ayrı bir thread'de okuyarak ana kayıt döngüsünü bloklamasını engeller."""
    def __init__(self, src=0, fps=30):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.stream.set(cv2.CAP_PROP_FPS, fps)
        self.stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.stream.set(cv2.CAP_PROP_AUTOFOCUS, 1) # Kameranın otomatik odaklanmasını zorlar
        self.grabbed, self.frame = self.stream.read()
        self.stopped = False
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            grabbed, frame = self.stream.read()
            with self.lock:
                self.grabbed = grabbed
                self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.grabbed, self.frame.copy()
            return False, None

    def stop(self):
        self.stopped = True
        self.stream.release()

# ──────────────────────────────────────────────────────────────
#  WEBCAM ÖNİZLEME PENCERESİ
# ──────────────────────────────────────────────────────────────
class WebcamPreviewWindow(ctk.CTkToplevel):
    """Kayıt sırasında webcam görüntüsünü canlı olarak gösterir."""
    def __init__(self, master, engine: "RecordingEngine"):
        super().__init__(master)
        self.engine = engine
        self.title("📷 Webcam Önizleme")
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._running = True

        # Başlık çubuğu
        hdr = ctk.CTkFrame(self, fg_color=CARD2, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="📷  Canlı Webcam Önizleme",
                     font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT).pack(side="left", padx=10, pady=6)
        ctk.CTkButton(hdr, text="✕", width=28, height=24,
                      fg_color=RED, hover_color="#7f1d1d",
                      font=ctk.CTkFont("Arial", 11, "bold"),
                      command=self._on_close).pack(side="right", padx=6, pady=4)

        # Video alanı
        self.video_label = ctk.CTkLabel(self, text="Kamera başlatılıyor...",
                                        font=ctk.CTkFont("Arial", 12), text_color=TXT2,
                                        fg_color=BG)
        self.video_label.pack(fill="both", expand=True)

        # Boyut göstergesi
        self.lbl_info = ctk.CTkLabel(self, text="", font=ctk.CTkFont("Arial", 10),
                                     text_color=TXT2, fg_color=CARD2)
        self.lbl_info.pack(fill="x")

        # Pencere boyutunu PiP boyutuna göre ayarla
        pw, ph = self.engine.pip_pixel_size
        win_w = max(pw + 20, 280)
        win_h = ph + 70
        self.geometry(f"{win_w}x{win_h}+20+20")

        self._update_frame()

    def _update_frame(self):
        if not self._running:
            return
        cap = self.engine.cap_stream
        if cap is not None:
            ret, frame = cap.read()
            if ret and frame is not None:
                try:
                    # Pencere boyutuna göre ölçekle
                    win_w = self.winfo_width() - 20
                    win_h = self.winfo_height() - 70
                    if win_w > 10 and win_h > 10:
                        fh, fw = frame.shape[:2]
                        scale = min(win_w / fw, win_h / fh)
                        nw, nh = int(fw * scale), int(fh * scale)
                        if nw > 0 and nh > 0:
                            frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                           size=(img.width, img.height))
                    self.video_label.configure(image=ctk_img, text="")
                    self.video_label._image = ctk_img  # GC koruması
                    h, w = frame.shape[:2]
                    self.lbl_info.configure(text=f"  {w}×{h}  |  Canlı  ●")
                except Exception:
                    pass
        elif not self.engine.recording:
            self._on_close()
            return
        self.after(33, self._update_frame)  # ~30 FPS

    def _on_close(self):
        self._running = False
        self.destroy()

# ──────────────────────────────────────────────────────────────
#  YÜZER ARAÇ ÇUBUĞU (FLOATING TOOLBAR) - Z-Order Korumalı
# ──────────────────────────────────────────────────────────────
class FloatingToolWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.app = master
        self.title("Araçlar & Zoom")
        # --- GÜVENLİ İKON YÜKLEME ---
        # Dosyanın tam yolunu oluşturuyoruz
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "AQ2.ico")

        if os.path.exists(icon_path):
            try:
                # Bazı Windows sürümlerinde wm_iconbitmap daha kararlı çalışır
                self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception as e:
                print(f"İkon yükleme hatası: {e}")
        else:
            print("Uyarı: AQ2.ico dosyası bulunamadı.")
        # ----------------------------
        self.geometry("260x540")
        self.attributes("-topmost", True)
        self.wm_transient("")
        self.protocol("WM_DELETE_WINDOW", self.close_panel)
        
        ctk.CTkLabel(self, text="🖌️ Çizim Araçları", font=ctk.CTkFont("Arial", 15, "bold")).pack(pady=(15,5))
        self.tool_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tool_frame.pack(pady=5)
        self.tool_btns = {}
        r, c = 0, 0
        for t in TOOLS:
            btn = ctk.CTkButton(self.tool_frame, text=TOOL_ICONS[t], width=45, height=45,
                                font=ctk.CTkFont("Arial", 18), fg_color=CARD2, hover_color=ACCENT2,
                                command=lambda tt=t: self.set_tool(tt))
            btn.grid(row=r, column=c, padx=3, pady=3)
            self.tool_btns[t] = btn
            c += 1
            if c > 3: c, r = 0, r + 1
            
        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(pady=10)
        self.color_prev = ctk.CTkFrame(opts, width=30, height=30, fg_color="#ff4444", corner_radius=4)
        self.color_prev.grid(row=0, column=0, padx=10)
        ctk.CTkButton(opts, text="🎨 Renk Seç", width=100, command=self.pick_color).grid(row=0, column=1)
        
        ctk.CTkLabel(self, text="🖌️ Kalınlık:", font=ctk.CTkFont("Arial", 15, "bold")).pack(pady=(5,0))
        self.thick_var = ctk.IntVar(value=3)
        ctk.CTkSlider(self, variable=self.thick_var, from_=1, to=15, command=self.set_thick).pack(padx=20, pady=5)
        
        ctk.CTkButton(self, text="🗑️ Ekranı Temizle", fg_color=RED, hover_color="#7f1d1d",
                      command=self.app.overlay.clear).pack(pady=10)
        
        ctk.CTkFrame(self, height=2, fg_color=BORDER).pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self, text="🔍 Yakınlaştırma", font=ctk.CTkFont("Arial", 15, "bold")).pack(pady=(5,5))
        self.zoom_lbl = ctk.CTkLabel(self, text="1.0×", font=ctk.CTkFont("Arial", 13, "bold"), text_color=ACCENT2)
        self.zoom_lbl.pack()
        self.zoom_var = ctk.DoubleVar(value=1.0)
        ctk.CTkSlider(self, variable=self.zoom_var, from_=1.0, to=4.0, command=self.set_zoom).pack(padx=20, pady=5)
        ctk.CTkButton(self, text="Sıfırla", command=self.reset_zoom, fg_color=RED).pack(pady=10)
        
        self.set_tool("mouse")

    def set_tool(self, t):
        self.app.overlay.set_tool(t)
        for name, btn in self.tool_btns.items():
            btn.configure(fg_color=ACCENT2 if name == t else CARD2)
            
        ew = getattr(self.app.overlay, 'event_win', None)
        if ew:
            if t == "mouse":
                try: self.wm_transient("")
                except: pass
                ew.geometry("0x0+0+0")
            else:
                ew.geometry(f"{self.app.overlay.W}x{self.app.overlay.H}+0+0")
                try: self.wm_transient(ew)
                except: pass

    def pick_color(self):
        c = colorchooser.askcolor(color=self.app.overlay.color, title="Çizim Rengi")
        if c and c[1]:
            self.app.overlay.set_color(c[1])
            self.color_prev.configure(fg_color=c[1])

    def set_thick(self, val):
        self.app.overlay.set_thickness(int(val))

    def set_zoom(self, val):
        self.app.engine.zoom_factor = float(val)
        self.zoom_lbl.configure(text=f"{float(val):.1f}×")

    def reset_zoom(self):
        self.zoom_var.set(1.0)
        self.set_zoom(1.0)

    def show(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.set_tool(self.app.overlay.tool)

    def hide(self):
        self.withdraw()

    def close_panel(self):
        self.hide()
        self.app.draw_var.set(False)
        self.app._toggle_draw()

# ──────────────────────────────────────────────────────────────
#  KAYIT MOTORU
# ──────────────────────────────────────────────────────────────
class RecordingEngine:
    def __init__(self):
        self.recording  = False
        self.paused     = False
        self.screen_on  = True
        self.webcam_on  = False
        self.audio_on   = True
        self.audio_rate = RATE
        self.audio_muted = False   # ← Kayıt sırasında anlık ses susturma
        self.region     = None
        self.fps        = FPS_DEF
        self.pip_enabled = True
        self.pip_pos    = "bottom-right"
        self.cam_idx    = 0
        self.output_dir = str(Path.home() / "Videos")
        self.cursor_hl  = False
        self.cursor_col = "#ff3333"
        self.cursor_sz  = 22
        self.wm_enabled = False
        self.wm_text    = ""
        self.wm_image   = None
        self.wm_pos     = "bottom-right"
        self.wm_opacity = 0.6
        self.draw_layer = None
        self.draw_lock  = threading.Lock()
        self.zoom_factor = 1.0
        self.zoom_center = None
        self.on_tick    = None
        self.on_done    = None
        self.quality    = 18
        self.enc_preset = "medium"
        self.pip_pixel_size = (240, 135)   # (genişlik, yükseklik) PiP boyutu
        self.cap_stream = None             # Paylaşılan webcam stream
        self._vw        = None
        self._ffmpeg_proc = None
        self._start_t   = None
        self._pause_t   = None
        self._pause_acc = 0.0
        self._audio_f    = []
        self._audio_lock = threading.Lock()   # ← ses tamponu kilidi
        self._t_screen   = None
        self._t_audio    = None
        self.last_path   = None
        self._wm_font    = None               # ← filigran font cache

    @property
    def elapsed(self):
        if not self._start_t: return 0.0
        t = time.time() - self._start_t - self._pause_acc
        return max(0.0, t)

    def elapsed_str(self):
        e = self.elapsed
        h,m,s = int(e//3600), int((e%3600)//60), int(e%60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def start(self):
        if self.recording: return
        os.makedirs(self.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._base = os.path.join(self.output_dir, f"kayit_{ts}")
        self._vid_tmp  = self._base + "_v.mp4"
        self._aud_tmp  = self._base + "_a.wav"
        self.last_path = self._base + ".mp4"
        self._audio_f  = []
        self._pause_acc = 0.0
        self._pause_t   = None
        self.recording  = True
        self.paused     = False
        self._start_t   = time.time()
        # Webcam stream'i burada başlat (önizleme de kullanabilsin)
        if self.webcam_on:
            self.cap_stream = WebcamVideoStream(src=self.cam_idx, fps=self.fps).start()
            time.sleep(0.5)
            if not self.cap_stream.grabbed:
                self.webcam_on = False
                self.cap_stream.stop()
                self.cap_stream = None
        if self.screen_on:
            self._t_screen = threading.Thread(target=self._loop_screen, daemon=True)
            self._t_screen.start()
        if self.audio_on and AUDIO_OK:
            self._t_audio = threading.Thread(target=self._loop_audio, daemon=True)
            self._t_audio.start()

    def pause(self):
        if self.recording and not self.paused:
            self.paused  = True
            self._pause_t = time.time()

    def resume(self):
        if self.recording and self.paused:
            if self._pause_t:
                self._pause_acc += time.time() - self._pause_t
            self.paused   = False
            self._pause_t = None

    def stop(self):
        if not self.recording: return
        self.recording = False
        self.paused    = False
        if self._t_screen: self._t_screen.join(timeout=4)
        if self._t_audio:  self._t_audio.join(timeout=4)
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.stdin.close()
                self._ffmpeg_proc.wait(timeout=60)
            except Exception:
                try: self._ffmpeg_proc.kill()
                except: pass
        self._ffmpeg_proc = None
        if self._vw:
            self._vw.release(); self._vw = None
        if self.cap_stream:
            self.cap_stream.stop(); self.cap_stream = None
        if self._audio_f and self.audio_on and AUDIO_OK:
            self._save_wav()
        self._merge()
        if self.on_done:
            self.on_done(self.last_path)

    def _get_mon(self):
        with mss_lib.mss() as s:
            if self.region:
                x,y,w,h = self.region
                return {"left":x,"top":y,"width":w,"height":h}
            m = s.monitors[1]
            return {"left":m["left"],"top":m["top"],"width":m["width"],"height":m["height"]}

    def _loop_screen(self):
        mon = self._get_mon()
        W, H = mon["width"], mon["height"]
        if W <= 0 or H <= 0: return

        # DİKKAT: -preset ultrafast yapıldı. Gerçek zamanlı kayıtta pipe'ın tıkanmaması için bu ŞARTTIR.
        if FFMPEG:
            ffcmd = [
                "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo", 
                "-s", f"{W}x{H}", "-pix_fmt", "bgr24", "-r", str(self.fps), 
                "-i", "pipe:", 
                "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", 
                "-crf", str(self.quality), "-pix_fmt", "yuv420p", 
                "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709", "-color_range", "tv",
                "-threads", "0", 
                self._vid_tmp
            ]
            self._ffmpeg_proc = subprocess.Popen(
                ffcmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_no_window()
            )
        else:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._vw = cv2.VideoWriter(self._vid_tmp, fourcc, self.fps, (W, H))
            if not self._vw.isOpened(): return

        with self.draw_lock:
            if self.draw_layer is None:
                self.draw_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        
        # Webcam stream engine.start()'ta zaten başlatıldı, paylaşılan referansı kullan
        cap_stream = self.cap_stream
        pip_active = self.pip_enabled and cap_stream is not None
        active_time = 0.0
        frames_written = 0
        last_time = time.perf_counter()
        
        with mss_lib.mss() as sct:
            while self.recording:
                now = time.perf_counter()
                if self.paused:
                    last_time = now
                    time.sleep(0.05)
                    continue
                
                dt = now - last_time
                last_time = now
                active_time += dt
                expected_frames = int(active_time * self.fps)
                frames_to_write = expected_frames - frames_written
                
                if frames_to_write > 0:
                    raw = sct.grab(mon)
                    frame = np.array(raw)
                    if frame.size == 0: continue
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    
                    if self.zoom_factor > 1.0:
                        frame = self._apply_zoom(frame, W, H)
                    
                    # PiP İşlemi (Bloklanma riski sıfırlandı)
                    if pip_active:
                        ret, wf = cap_stream.read()
                        if ret and wf is not None:
                            pw, ph = self.pip_pixel_size
                            wf = cv2.resize(wf, (pw, ph), interpolation=cv2.INTER_AREA)
                            border = 3
                            wf_b = cv2.copyMakeBorder(wf, border, border, border, border, cv2.BORDER_CONSTANT, value=(220, 220, 220))
                            pb_w, pb_h = wf_b.shape[1], wf_b.shape[0]
                            _m = 20
                            _pp = self.pip_pos
                            ox, oy = _corner_pos(_pp, pb_w, pb_h, W, H, margin=_m)
                            ox = max(0, min(ox, W - pb_w))
                            oy = max(0, min(oy, H - pb_h))
                            
                            sh = 6
                            sx1, sy1 = ox + sh, oy + sh
                            sx2, sy2 = min(ox + pb_w + sh, W), min(oy + pb_h + sh, H)
                            shadow_roi = frame[sy1:sy2, sx1:sx2]
                            if shadow_roi.size > 0:
                                frame[sy1:sy2, sx1:sx2] = (shadow_roi * 0.45).astype(np.uint8)
                            
                            ey, ex = min(oy + pb_h, H), min(ox + pb_w, W)
                            frame[oy:ey, ox:ex] = wf_b[:ey-oy, :ex-ox]

                    # Çizim Katmanı
                    with self.draw_lock:
                        if self.draw_layer is not None:
                            dl = np.array(self.draw_layer)
                            fh, fw = frame.shape[:2]
                            dh, dw = dl.shape[:2]
                            if fh != dh or fw != dw:
                                dl = cv2.resize(dl, (fw, fh), interpolation=cv2.INTER_NEAREST)
                            if dl.shape[2] == 4:
                                dl_bgra = dl[:, :, [2, 1, 0, 3]]
                                alpha = dl_bgra[:, :, 3:4] / 255.0
                                bgr_d = dl_bgra[:, :, :3]
                                if np.any(alpha > 0):
                                    frame = (frame.astype(np.float32) * (1 - alpha) + bgr_d.astype(np.float32) * alpha).astype(np.uint8)
                    
                    # İmleç
                    if self.cursor_hl and CURSOR_OK:
                        try:
                            cx, cy = pyautogui.position()
                            if self.region: cx -= self.region[0]; cy -= self.region[1]
                            cc = self._hex_bgr(self.cursor_col)
                            cv2.circle(frame, (int(cx), int(cy)), self.cursor_sz, cc, 2)
                            cv2.circle(frame, (int(cx), int(cy)), 4, cc, -1)
                            cv2.circle(frame, (int(cx), int(cy)), self.cursor_sz + 4, cc, 1)
                        except: pass
                    
                    # Filigran
                    if self.wm_enabled:
                        frame = self._apply_wm(frame, W, H)
                    
                    if self.on_tick:
                        self.on_tick(self.elapsed)
                    
                    # FFmpeg'e veya OpenCV'ye yazma
                    if frame.shape[:2] == (H, W):
                        frame_bytes = frame.tobytes()
                        
                        # KISITLAMA KALDIRILDI!
                        # Zamanın (sürenin) kısalmaması için bilgisayar ne kadar geciktiyse 
                        # o kadar tekrar karesi (frame) yazdırıyoruz.
                        for _ in range(frames_to_write):
                            if self._ffmpeg_proc:
                                try:
                                    if self._ffmpeg_proc.stdin and not self._ffmpeg_proc.stdin.closed:
                                        self._ffmpeg_proc.stdin.write(frame_bytes)
                                    else:
                                        break
                                except (BrokenPipeError, OSError, ValueError):
                                    break
                            elif self._vw:
                                self._vw.write(frame)
                        
                        # Gerçekten kaç kare yazılması gerekiyorsa onu ekliyoruz.
                        frames_written += frames_to_write
                else:
                    # CPU'yu %100 kullanmasını önlemek için ufak bir uyku
                    time.sleep(0.005) 
                    
        # cap_stream engine.stop() tarafından kapatılacak

    def _apply_zoom(self, frame, W, H):
        f  = self.zoom_factor
        cx = self.zoom_center[0] if self.zoom_center else W // 2
        cy = self.zoom_center[1] if self.zoom_center else H // 2
        nw, nh = int(W / f), int(H / f)
        x0 = max(0, min(cx - nw // 2, W - nw))
        y0 = max(0, min(cy - nh // 2, H - nh))
        crop = frame[y0:y0+nh, x0:x0+nw]
        return cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)

    def _apply_wm(self, frame, W, H):
        pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr  = ImageDraw.Draw(ov)
        if self._wm_font is None:
            try: self._wm_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            except: self._wm_font = ImageFont.load_default()
        fnt = self._wm_font
        a = int(255 * self.wm_opacity)
        if self.wm_text:
            bb = dr.textbbox((0, 0), self.wm_text, font=fnt)
            tw, th = bb[2]-bb[0], bb[3]-bb[1]
            pos = self._wm_pos(tw, th, W, H)
            dr.rectangle([pos[0]-4, pos[1]-2, pos[0]+tw+4, pos[1]+th+2], fill=(0,0,0,int(a*0.5)))
            dr.text(pos, self.wm_text, fill=(255,255,255,a), font=fnt)
        if self.wm_image:
            try:
                wm = self.wm_image.convert("RGBA")
                r, g, b, al = wm.split()
                al = al.point(lambda x: int(x * self.wm_opacity))
                wm.putalpha(al)
                iw, ih = wm.size
                pos = self._wm_pos(iw, ih, W, H)
                ov.paste(wm, pos, wm)
            except: pass
        merged = Image.alpha_composite(pil, ov)
        return cv2.cvtColor(np.array(merged.convert("RGB")), cv2.COLOR_RGB2BGR)

    def _wm_pos(self, w, h, W, H):
        return _corner_pos(self.wm_pos, w, h, W, H, margin=16)

    def _hex_bgr(self, h):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (b, g, r)

    def _loop_audio(self):
        if not AUDIO_OK: return
        pa = pyaudio.PyAudio()
        # Susturulduğunda yerine yazılacak sıfır-tampon (1 chunk boyutunda sessizlik)
        _silence = b'\x00' * (CHUNK * 2 * 2)  # 16-bit stereo
        try:
            st = pa.open(format=pyaudio.paInt16, channels=2, rate=self.audio_rate, input=True, frames_per_buffer=CHUNK)
            while self.recording:
                if self.paused: time.sleep(0.05); continue
                try:
                    data = st.read(CHUNK, exception_on_overflow=False)
                    chunk = _silence if self.audio_muted else data
                    with self._audio_lock:
                        self._audio_f.append(chunk)
                except: break
            st.stop_stream(); st.close()
        finally: pa.terminate()

    def _save_wav(self):
        try:
            with self._audio_lock:
                frames = b"".join(self._audio_f)
            wf = wave.open(self._aud_tmp, "wb")
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(self.audio_rate)
            wf.writeframes(frames); wf.close()
        except Exception as e: print(f"Ses hata: {e}")

    def _merge(self):
        has_v = os.path.exists(self._vid_tmp)
        has_a = os.path.exists(self._aud_tmp) if hasattr(self, "_aud_tmp") else False
        if not has_v: return
        if has_a and FFMPEG:
            try:
                cmd = ["ffmpeg", "-y", "-i", self._vid_tmp, "-i", self._aud_tmp, "-c:v", "copy", "-c:a", "aac", "-af", "aresample=async=1", "-shortest", self.last_path]
                r = subprocess.run(cmd, capture_output=True, timeout=120, **_no_window())
                if r.returncode == 0:
                    os.remove(self._vid_tmp); os.remove(self._aud_tmp); return
            except: pass
        shutil.move(self._vid_tmp, self.last_path)
        if has_a:
            try: os.remove(self._aud_tmp)
            except: pass

# ──────────────────────────────────────────────────────────────
#  ÇİZİM KATMANI
# ──────────────────────────────────────────────────────────────
class DrawingOverlay:
    def __init__(self, engine: RecordingEngine):
        self.engine  = engine
        self.win     = None
        self.event_win = None
        self.canvas  = None
        self.tool    = "rectangle"
        self.color   = "#ff4444"
        self.thick   = 3
        self._draw   = False
        self._sx = self._sy = 0
        self._cur    = None
        self._pts    = []
        self.W = self.H = 0

    def show(self):
        if self.win: return
        r = self.engine.region
        self.win = tk.Toplevel()
        self.win.title("DrawOverlay_Visual")
        self.win.wm_attributes("-topmost", True)
        self.win.overrideredirect(True)
        self.win.transient(None)
        self.event_win = tk.Toplevel()
        self.event_win.title("DrawOverlay_Event")
        self.event_win.wm_attributes("-topmost", True)
        self.event_win.overrideredirect(True)
        self.event_win.transient(None)
        if r:
            self.W, self.H = r[2], r[3]
            geom = f"{self.W}x{self.H}+{r[0]}+{r[1]}"
        else:
            self.W = self.win.winfo_screenwidth()
            self.H = self.win.winfo_screenheight()
            geom = f"{self.W}x{self.H}+0+0"
        self.win.geometry(geom)
        self.event_win.geometry(geom)
        if os.name == "nt":
            TRANS_COLOR = "#ab00cd"
            self.win.configure(bg=TRANS_COLOR)
            self.win.attributes("-transparentcolor", TRANS_COLOR)
            self.canvas = tk.Canvas(self.win, bg=TRANS_COLOR, highlightthickness=0, bd=0)
            self.event_win.attributes("-alpha", 0.01)
            self.event_win.configure(bg="black", cursor="crosshair")
        elif sys.platform == "darwin":
            self.win.configure(bg="systemTransparent")
            self.win.wm_attributes("-transparent", True)
            self.canvas = tk.Canvas(self.win, bg="systemTransparent", highlightthickness=0, bd=0)
            self.event_win.attributes("-alpha", 0.01)
            self.event_win.configure(bg="black", cursor="crosshair")
        else:
            self.win.attributes("-alpha", 0.3)
            self.canvas = tk.Canvas(self.win, bg="black", highlightthickness=0, bd=0)
            self.event_win.attributes("-alpha", 0.01)
            self.event_win.configure(bg="black", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.event_win.bind("<ButtonPress-1>",   self._press)
        self.event_win.bind("<B1-Motion>",       self._drag)
        self.event_win.bind("<ButtonRelease-1>", self._release)
        self.event_win.bind("<Double-Button-1>", self._dbl)
        self.event_win.lift()
        with self.engine.draw_lock:
            self.engine.draw_layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def hide(self):
        try:
            root = getattr(tk, '_default_root', None)
            if root is not None:
                tw = getattr(root, 'tool_window', None)
                if tw is not None:
                    tw.wm_transient("")
        except Exception: pass
        if self.win: self.win.destroy(); self.win = None
        if self.event_win: self.event_win.destroy(); self.event_win = None

    def set_tool(self, tool): self.tool = tool
    def set_color(self, color): self.color = color
    def set_thickness(self, t): self.thick = int(t)
    def clear(self):
        if self.canvas: self.canvas.delete("all")
        with self.engine.draw_lock:
            self.engine.draw_layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def _pil_col(self):
        try:
            h = self.color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b, 210)
        except: return (255, 68, 68, 210)

    def _press(self, e):
        self._draw = True; self._sx = e.x; self._sy = e.y
        if self.tool == "freehand": self._pts = [(e.x, e.y)]

    def _drag(self, e):
        if not self._draw: return
        if self._cur: self.canvas.delete(self._cur)
        x0, y0, x1, y1 = self._sx, self._sy, e.x, e.y
        c, t = self.color, self.thick
        if self.tool == "rectangle": self._cur = self.canvas.create_rectangle(x0, y0, x1, y1, outline=c, width=t)
        elif self.tool == "circle": self._cur = self.canvas.create_oval(x0, y0, x1, y1, outline=c, width=t)
        elif self.tool == "arrow": self._cur = self.canvas.create_line(x0, y0, x1, y1, fill=c, width=t, arrow=tk.LAST, arrowshape=(16, 20, 6))
        elif self.tool == "line": self._cur = self.canvas.create_line(x0, y0, x1, y1, fill=c, width=t)
        elif self.tool == "freehand":
            self._pts.append((e.x, e.y))
            if len(self._pts) >= 2:
                fl = [co for p in self._pts for co in p]
                if self._cur: self.canvas.delete(self._cur)
                self._cur = self.canvas.create_line(*fl, fill=c, width=t, smooth=True)
        elif self.tool == "eraser":
            r = self.thick * 2 + 10
            self.canvas.create_oval(x1-r, y1-r, x1+r, y1+r, fill="#ab00cd" if os.name=="nt" else "systemTransparent", outline="")
            with self.engine.draw_lock:
                if self.engine.draw_layer:
                    patch = Image.new("RGBA", (r*2, r*2), (0, 0, 0, 0))
                    px = max(0, x1 - r); py = max(0, y1 - r)
                    self.engine.draw_layer.paste(patch, (px, py))

    def _release(self, e):
        if not self._draw: return
        self._draw = False
        x0, y0, x1, y1 = self._sx, self._sy, e.x, e.y
        pc = self._pil_col(); t = self.thick
        xmin, xmax = min(x0, x1), max(x0, x1)
        ymin, ymax = min(y0, y1), max(y0, y1)
        with self.engine.draw_lock:
            if self.engine.draw_layer is None: return
            d = ImageDraw.Draw(self.engine.draw_layer)
            if self.tool == "rectangle": d.rectangle([xmin, ymin, xmax, ymax], outline=pc, width=t)
            elif self.tool == "circle": d.ellipse([xmin, ymin, xmax, ymax], outline=pc, width=t)
            elif self.tool == "arrow":
                d.line([x0, y0, x1, y1], fill=pc, width=t)
                ang = math.atan2(y1-y0, x1-x0)
                for da in (2.5, -2.5):
                    ax = x1 - 15 * math.cos(ang + da); ay = y1 - 15 * math.sin(ang + da)
                    d.polygon([(x1, y1), (ax, ay)], fill=pc)
            elif self.tool == "line": d.line([x0, y0, x1, y1], fill=pc, width=t)
            elif self.tool == "freehand" and len(self._pts) >= 2:
                for i in range(len(self._pts)-1): d.line([self._pts[i], self._pts[i+1]], fill=pc, width=t)
        self._cur = None

    def _dbl(self, e):
        if self.tool != "text": return
        dlg = tk.Toplevel(self.event_win)
        dlg.title("Metin Ekle"); dlg.geometry("340x200"); dlg.attributes("-topmost", True); dlg.configure(bg="#850068")
        ent = tk.Entry(dlg, font=("Arial", 15), bg="#ffffff", fg="#000000", insertbackground="#850068", relief="flat", highlightthickness=0)
        ent.pack(padx=20, pady=(25, 10), fill="x"); ent.focus()
        svar = tk.IntVar(value=18)
        scale = tk.Scale(dlg, variable=svar, from_=10, to=48, orient="horizontal", bg="#850068", fg="#ffffff", troughcolor="#ffffff", activebackground="#a30080", highlightthickness=0, relief="flat", label="Boyut")
        scale.pack(fill="x", padx=20, pady=(0, 20))
        x, y = e.x, e.y
        def add():
            txt = ent.get()
            if not txt: dlg.destroy(); return
            sz = svar.get()
            self.canvas.create_text(x, y, text=txt, fill=self.color, font=("Arial", sz, "bold"), anchor="nw")
            with self.engine.draw_lock:
                if self.engine.draw_layer:
                    d = ImageDraw.Draw(self.engine.draw_layer)
                    try: fnt = ImageFont.truetype("arial.ttf", sz)
                    except: fnt = ImageFont.load_default()
                    d.text((x, y), txt, fill=self._pil_col(), font=fnt)
            dlg.destroy()
        tk.Button(dlg, text="Ekle ✓", command=add, bg="#1f538d", fg="#e6edf3", relief="flat", padx=10).pack(pady=4)
        ent.bind("<Return>", lambda e2: add())

# ──────────────────────────────────────────────────────────────
#  BÖLGE SEÇİCİ
# ──────────────────────────────────────────────────────────────
class RegionSelector:
    def __init__(self, cb): self.cb = cb
    def select(self):
        w = tk.Toplevel()
        w.attributes("-fullscreen", True); w.attributes("-alpha", 0.35); w.attributes("-topmost", True)
        w.configure(bg="gray20"); w.overrideredirect(True)
        sw = w.winfo_screenwidth(); sh = w.winfo_screenheight()
        cv = tk.Canvas(w, width=sw, height=sh, bg="gray20", cursor="crosshair", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cv.create_text(sw//2, 32, text="📐  Kayıt bölgesini sürükleyerek seçin  |  ESC: İptal", fill="white", font=("Arial", 16, "bold"), tags="hint")
        sx = sy = 0; rect = None
        def press(e):
            nonlocal sx, sy, rect; sx, sy = e.x, e.y
            if rect: cv.delete(rect)
        def drag(e):
            nonlocal rect
            if rect: cv.delete(rect)
            rect = cv.create_rectangle(sx, sy, e.x, e.y, outline="#00ff88", width=2, dash=(5, 3))
            cv.delete("hint"); cv.create_text((sx+e.x)//2, (sy+e.y)//2, text=f"{abs(e.x-sx)}×{abs(e.y-sy)}", fill="white", font=("Arial", 13, "bold"), tags="lbl")
        def release(e):
            x0, y0 = min(sx, e.x), min(sy, e.y); x1, y1 = max(sx, e.x), max(sy, e.y)
            w.destroy()
            if x1-x0 > 20 and y1-y0 > 20: self.cb((x0, y0, x1-x0, y1-y0))
            else: self.cb(None)
        def esc(e): w.destroy(); self.cb(None)
        cv.bind("<ButtonPress-1>", press); cv.bind("<B1-Motion>", drag); cv.bind("<ButtonRelease-1>", release); w.bind("<Escape>", esc)

# ──────────────────────────────────────────────────────────────
#  VİDEO EDİTÖRÜ
# ──────────────────────────────────────────────────────────────
class VideoEditor:
    @staticmethod
    def trim(inp, out, t0, t1, cb=None):
        def _run():
            try:
                r = subprocess.run(["ffmpeg", "-y", "-ss", str(t0), "-i", inp, "-to", str(t1 - t0), "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", out], capture_output=True, timeout=300, **_no_window())
                if cb: cb(r.returncode == 0, out)
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def merge(paths, out, cb=None):
        def _run():
            try:
                lst = out + "_list.txt"
                with open(lst, "w", encoding="utf-8") as f:
                    for p in paths: f.write(f"file '{p.replace(chr(92), '/')}'\n")
                r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", out], capture_output=True, timeout=600, **_no_window())
                try: os.remove(lst)
                except: pass
                if cb: cb(r.returncode == 0, out)
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def convert(inp, out, fmt="mp4", cb=None):
        def _run():
            codecs = {"mp4": ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"], "avi": ["-c:v", "libxvid", "-q:v", "3", "-c:a", "libmp3lame", "-b:a", "192k"], "mkv": ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"], "mov": ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"], "gif": ["-vf", "fps=10,scale=640:-1:flags=lanczos", "-loop", "0"], "webm": ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus", "-b:a", "192k"], "mp3": ["-vn", "-c:a", "libmp3lame", "-b:a", "192k"], "wav": ["-vn", "-c:a", "pcm_s16le"]}
            extra = codecs.get(fmt, ["-c", "copy"])
            try:
                r = subprocess.run(["ffmpeg", "-y", "-i", inp] + extra + [out], capture_output=True, timeout=600, **_no_window())
                if cb: cb(r.returncode == 0, out)
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def get_duration(path):
        try:
            r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, timeout=10, **_no_window())
            return float(r.stdout.strip())
        except: return 0.0

# ──────────────────────────────────────────────────────────────
#  SES EDİTÖRÜ (AUDIO EDITOR)
# ──────────────────────────────────────────────────────────────
class AudioEditor:
    """Ses dosyaları üzerinde kırpma, bölme, dönüştürme ve birleştirme işlemleri."""

    FORMATS = ["mp3", "wav", "ogg", "aac", "flac", "m4a", "opus", "wma"]

    # ── Tüm metodlarda paylaşılan codec tablosu (DRY) ──────────────────────
    _CODEC_MAP = {
        "mp3":  ["-c:a", "libmp3lame", "-b:a", "192k"],
        "wav":  ["-c:a", "pcm_s16le"],
        "ogg":  ["-c:a", "libvorbis", "-q:a", "5"],
        "aac":  ["-c:a", "aac", "-b:a", "192k"],
        "flac": ["-c:a", "flac"],
        "m4a":  ["-c:a", "aac", "-b:a", "192k"],
        "opus": ["-c:a", "libopus", "-b:a", "128k"],
        "wma":  ["-c:a", "wmav2", "-b:a", "192k"],
    }

    @staticmethod
    def get_duration(path):
        """VideoEditor.get_duration ile aynı mantık; tekrarı önlemek için delege edilir."""
        return VideoEditor.get_duration(path)

    @staticmethod
    def trim(inp, out, t0, t1, cb=None):
        """t0→t1 aralığını kırparak yeni dosyaya yazar."""
        def _run():
            try:
                dur = t1 - t0
                ext = os.path.splitext(out)[1].lstrip(".").lower()
                codec_args = AudioEditor._CODEC_MAP.get(ext, ["-c:a", "copy"])
                cmd = ["ffmpeg", "-y", "-ss", str(t0), "-i", inp,
                       "-t", str(dur), "-vn"] + codec_args + [out]
                r = subprocess.run(cmd, capture_output=True, timeout=300, **_no_window())
                if cb: cb(r.returncode == 0, out if r.returncode == 0 else
                          r.stderr.decode("utf-8", errors="replace")[-300:])
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def split(inp, out1, out2, split_time, cb=None):
        """Ses dosyasını split_time saniyesinde ikiye böler."""
        def _run():
            try:
                ext = os.path.splitext(inp)[1].lstrip(".").lower()
                codec_args = AudioEditor._CODEC_MAP.get(ext, ["-c:a", "copy"])
                # İlk parça: 0 → split_time
                r1 = subprocess.run(
                    ["ffmpeg", "-y", "-i", inp, "-t", str(split_time), "-vn"]
                    + codec_args + [out1],
                    capture_output=True, timeout=300, **_no_window()
                )
                # İkinci parça: split_time → son
                r2 = subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(split_time), "-i", inp, "-vn"]
                    + codec_args + [out2],
                    capture_output=True, timeout=300, **_no_window()
                )
                ok = (r1.returncode == 0 and r2.returncode == 0)
                err = ""
                if not ok:
                    err = (r1.stderr + r2.stderr).decode("utf-8", errors="replace")[-300:]
                if cb: cb(ok, (out1, out2) if ok else err)
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def convert(inp, out, fmt="mp3", bitrate="192k", cb=None):
        """Ses dosyasını istenen formata dönüştürür."""
        def _run():
            codec_args = AudioEditor._CODEC_MAP.get(fmt, ["-c:a", "copy"])
            # bitrate override: libmp3lame/aac/libopus/wmav2 için dinamik bitrate
            if bitrate != "192k" and len(codec_args) >= 4 and codec_args[2] == "-b:a":
                codec_args = list(codec_args); codec_args[3] = bitrate
            try:
                r = subprocess.run(
                    ["ffmpeg", "-y", "-i", inp, "-vn"] + codec_args + [out],
                    capture_output=True, timeout=600, **_no_window()
                )
                if cb: cb(r.returncode == 0, out if r.returncode == 0 else
                          r.stderr.decode("utf-8", errors="replace")[-300:])
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def merge(paths, out, cb=None):
        """Birden fazla ses dosyasını sırayla birleştirir."""
        def _run():
            try:
                ext  = os.path.splitext(out)[1].lstrip(".").lower()
                codec_args = AudioEditor._CODEC_MAP.get(ext, ["-c:a", "copy"])
                
                inputs = []
                filter_parts = []
                
                # 1. Aşama: Tüm dosyaları input olarak ekle ve aynı formata (44100Hz, Stereo) dönüştür
                for i, p in enumerate(paths):
                    inputs.extend(["-i", p])
                    filter_parts.append(f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")
                
                # 2. Aşama: Dönüştürülen tüm bu sesleri birbirine ula (concat)
                concat_labels = "".join([f"[a{i}]" for i in range(len(paths))])
                filter_str = ";".join(filter_parts) + f";{concat_labels}concat=n={len(paths)}:v=0:a=1[aout]"
                
                # TXT dosyası kullanmayı bıraktığımız için dosya adı kaynaklı hatalar (boşluk, tırnak vs.) yaşanmaz
                cmd = ["ffmpeg", "-y"] + inputs + [
                    "-filter_complex", filter_str,
                    "-map", "[aout]", "-vn"
                ] + codec_args + [out]
                
                r = subprocess.run(cmd, capture_output=True, timeout=600, **_no_window())
                
                if cb: 
                    cb(r.returncode == 0, out if r.returncode == 0 else
                       r.stderr.decode("utf-8", errors="replace")[-300:])
            except Exception as e:
                if cb: cb(False, str(e))
        threading.Thread(target=_run, daemon=True).start()


# ──────────────────────────────────────────────────────────────
#  TİMELINE VERİ SINIFLARI
# ──────────────────────────────────────────────────────────────
class ClipData:
    """Timeline üzerindeki bir video klibini temsil eder."""
    def __init__(self, path):
        self.path = path; self.name = os.path.basename(path)
        self.duration = VideoEditor.get_duration(path)
        self.trim_start = 0.0; self.trim_end = self.duration
        self.speed = 1.0; self.scale_w = 0; self.scale_h = 0
        self.timeline_start = 0.0; self.thumbnails = []
        self.mute = False
        # Klip başına video efektleri (renk, filtre, dönüşüm, solma)
        self.effects = {
            "brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0,
            "hue": 0.0, "blur": 0.0,
            "bw": False, "sepia": False, "red_filter": False, "blue_filter": False,
            "vignette": False, "sharpen": False, "invert": False,
            "mirror": False, "vflip": False, "rotate": False,
            "fade_in": 0.0, "fade_out": 0.0,
        }
    @property
    def clip_duration(self): return max(0.01, (self.trim_end - self.trim_start) / max(0.01, self.speed))
    @property
    def timeline_end(self): return self.timeline_start + self.clip_duration

class TextOverlay:
    def __init__(self, text="Metin", x=100, y=100, size=32, color="#ffffff", start_time=0.0, end_time=5.0):
        self.text=text; self.x=x; self.y=y; self.size=size; self.color=color
        self.start_time=start_time; self.end_time=end_time; self.uid=id(self)

class AudioTrack:
    """Timeline'a eklenen bağımsız ses parçası."""
    def __init__(self, path, start_time=0.0, volume=1.0):
        self.path       = path
        self.name       = os.path.basename(path)
        self.duration   = VideoEditor.get_duration(path)
        self.trim_start = 0.0
        self.trim_end   = self.duration
        self.start_time = start_time
        self.volume     = volume
        self.uid        = id(self)
    @property
    def clip_duration(self):
        return max(0.01, self.trim_end - self.trim_start)

# ──────────────────────────────────────────────────────────────
#  GEÇİŞ EFEKTLERİ MODÜLü
# ──────────────────────────────────────────────────────────────
TRANSITION_EFFECTS = [
    # (gösterim_adı, ffmpeg_xfade_adı, açıklama, emoji)
    ("Cut",              "cut",         "Doğrudan kesim – geçiş yok",       "✂️"),
    ("Fade",             "fade",        "Yavaş karart / aç",                 "🌅"),
    ("Dissolve",         "dissolve",    "Çözülerek geçiş",                   "💧"),
    ("Wipe",             "wipeleft",    "Soldaki ekrandan sil",              "🌊"),
    ("Zoom",             "zoomin",      "Yakınlaşarak geçiş",                "🔍"),
    ("Jump Cut",         "jumpcut",     "Anlık zıplama (cut özel)",          "⚡"),
    ("Light Leak",       "fadewhite",   "Parlak ışık sızması",               "💡"),
    ("Glitch",           "pixelize",    "Piksel bozulma efekti",             "📺"),
    ("Paper Tear",       "diagtl",      "Köşeden yırtılma",                  "📄"),
    ("Wormhole",         "radial",      "Dairesel girdap",                   "🌀"),
    ("Warp Zoom",        "hlslice",     "Yatay dilim / büküm",               "🌪️"),
    ("Flash",            "fadeblack",   "Siyah flaş",                        "⚫"),
    ("Cross Dissolve",   "smoothleft",  "Yumuşak çapraz geçiş",             "🔄"),
    ("Match Cut",        "circlecrop",  "Daire içi eşleşme",                "🎯"),
    ("Push",             "slideleft",   "Yeni sahneyi itiyor",               "➡️"),
]

# Jump Cut özel işleme: ffmpeg'de xfade=jumpcut yok, direkt hard cut + pts reset
XFADE_NOT_SUPPORTED = {"cut", "jumpcut"}

# O(1) arama için fx → (display_name, emoji) haritası
_TRANS_MAP = {fx: (name, em) for name, fx, desc, em in TRANSITION_EFFECTS}

class TransitionData:
    """İki klip arasındaki geçiş efektini temsil eder."""
    def __init__(self, effect="cut", duration=0.5):
        self.effect   = effect    # TRANSITION_EFFECTS'teki ffmpeg_xfade_adı
        self.duration = duration  # saniye

    @property
    def display_name(self):
        name, em = _TRANS_MAP.get(self.effect, ("Cut", "✂️"))
        return f"{em} {name}"

    @property
    def emoji(self):
        return _TRANS_MAP.get(self.effect, ("Cut", "✂️"))[1]

    @property
    def is_cut(self):
        return self.effect in XFADE_NOT_SUPPORTED

# ──────────────────────────────────────────────────────────────
#  TİMELINE VIDEO EDİTÖR
# ──────────────────────────────────────────────────────────────
class VideoTimelineEditor(ctk.CTkFrame):
    _CLIP_Y  = 26; _CLIP_H  = 54; _AUDIO_Y = 90; _AUDIO_H = 26

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.clips          = []
        self.text_overlays  = []
        self.audio_tracks   = []
        self.transitions    = {}   # key: (id(clip_a), id(clip_b)) → TransitionData
        self.playhead_pos   = 0.0
        self.timeline_dur   = 60.0
        self.px_per_sec     = 60
        self.selected_clip  = None
        self.selected_audio = None
        self.playing        = False
        self._play_after    = None
        self._play_t0_wall  = None
        self._play_t0_pos   = None
        self._drag_clip     = None
        self._drag_audio    = None
        self._drag_mode     = "move"
        self._drag_offset   = 0.0
        self._preview_img          = None
        self._preview_playing_clip = None
        self._prev_audio_tmp       = None
        self._audio_extracting     = False   # eş zamanlı çıkarma engelleyici
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 6))
        ctk.CTkLabel(hdr, text="⏰ Timeline Video Editör", font=ctk.CTkFont("Arial", 16, "bold"), text_color=TXT).pack(side="left")
        body = ctk.CTkFrame(self, fg_color="transparent")

        # Responsive grid layout for body - adapts to screen width
        def _on_body_configure(event):
            try:
                w = event.width
                # On smaller screens (< 900px), stack panels vertically
                if w < 900:
                    body.pack_configure(fill="both", expand=True)
                    left.pack_configure(fill="both", expand=True)
                    right_frame.pack_configure(fill="both", expand=True, padx=(6, 0), pady=(4, 0))
                else:
                    body.pack_configure(fill="both", expand=True)
                    left.pack_configure(side="left", fill="both", expand=True)
                    right_frame.pack_configure(side="right", fill="both", expand=True, padx=(6, 0), pady=(4, 0))
            except:
                pass

        body.bind("<Configure>", _on_body_configure)
        body.pack(fill="both", expand=True, padx=12, pady=4)
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)
        
        prev_card = ctk.CTkFrame(left, fg_color=CARD, corner_radius=10)
        prev_card.pack(fill="x", padx=(0, 6), pady=(0, 4))
        self.preview_canvas = tk.Canvas(prev_card, bg="#000000", highlightthickness=0, width=640, height=340)
        self.preview_canvas.pack(pady=6, padx=8)
        self._draw_placeholder()
        
        ctrl = ctk.CTkFrame(prev_card, fg_color="transparent")
        ctrl.pack(fill="x", padx=8, pady=(0, 4))
        self.btn_play = ctk.CTkButton(ctrl, text="▶  Oynat", width=110, fg_color=ACCENT, hover_color="#1a6e2a", font=ctk.CTkFont("Arial", 12, "bold"), command=self._toggle_play)
        self.btn_play.pack(side="left", padx=4)
        ctk.CTkButton(ctrl, text="⏹", width=36, fg_color=CARD2, hover_color=BORDER, command=self._stop_play).pack(side="left", padx=2)
        ctk.CTkButton(ctrl, text="⏮", width=36, fg_color=CARD2, hover_color=BORDER, command=lambda: self._seek(0.0)).pack(side="left", padx=2)
        self.lbl_time = ctk.CTkLabel(ctrl, text="00:00 / 00:00", font=ctk.CTkFont("Courier", 12), text_color=TXT2)
        self.lbl_time.pack(side="left", padx=10)
        self.preview_audio_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl, text="🔊 Ses", variable=self.preview_audio_var,
                      font=ctk.CTkFont("Arial", 11), width=50).pack(side="left", padx=10)
        
        self.seek_var = ctk.DoubleVar(value=0.0)
        self.seek_slider = ctk.CTkSlider(prev_card, variable=self.seek_var, from_=0, to=100, command=self._on_seek_slide)
        self.seek_slider.pack(fill="x", padx=8, pady=(0, 8))
        
        # ── Responsive Toolbar with ScrollableFrame ──────────────────────────────────
        tb = ctk.CTkScrollableFrame(left, fg_color="#d4d2d2", corner_radius=8, orientation="horizontal", height=40, scrollbar_button_color=CARD2, scrollbar_button_hover_color=BORDER)
        tb.pack(fill="x", padx=(0, 6), pady=(2,2))
        tb._scrollbar.configure(width=12)

        btn_cfg = dict(height=32, font=ctk.CTkFont("Arial", 12, "bold"))
        toolbar_buttons = [
            ("📂 Video Ekle", "add_video", self._import_video, ACCENT2, "#1a4472"),
            ("🎵 Ses Ekle", "add_audio", self._import_audio, "#1a6b66", BORDER),
            ("🖺 Metin Ekle", "add_text", self._add_text_overlay, "#ff9500", "#7c3aed"),
            ("🎬 Geçiş Efekti", "transition", self._open_transition_picker, "#7c3aed", "#5b21b6"),
            ("🔪 Böl", "split", self._split_selected, "#d2ac00", "#7f1d1d"),
            ("🎵 Sesi Ayır", "extract_audio", self._extract_audio, "#ff005d", BORDER),
            ("🔇 Sesi Sil", "mute", self._toggle_mute_selected, "#386293", "#5a1a1a"),
            ("🚮 Sil", "delete", self._delete_selected, RED, "#7f1d1d"),
            ("💾 Dışa Aktar", "export", self._export, YELLOW, "#a07010"),
        ]
        self._toolbar_btns = {}
        for label, key, cmd, color, hover in toolbar_buttons:
            btn = ctk.CTkButton(tb, text=label, width=100, fg_color=color, hover_color=hover, command=cmd, **btn_cfg)
            btn.pack(side="left", padx=3, pady=3)
            self._toolbar_btns[key] = btn
        # Store reference for overflow menu
        self.btn_mute_clip = self._toolbar_btns["mute"]
        self._main_toolbar = tb
        
        tl_card = ctk.CTkFrame(left, fg_color=CARD, corner_radius=8)
        tl_card.pack(fill="both", expand=True, padx=(0, 6), pady=(2,2))
        tl_hdr = ctk.CTkFrame(tl_card, fg_color="transparent")
        tl_hdr.pack(fill="x", padx=8, pady=(2, 2))
        ctk.CTkLabel(tl_hdr, text="⏰ Timeline", font=ctk.CTkFont("Arial", 13, "bold"), text_color=TXT).pack(side="left")
        z_f = ctk.CTkFrame(tl_hdr, fg_color="transparent")
        z_f.pack(side="right")
        ctk.CTkLabel(z_f, text="Zoom:", text_color=TXT2, font=ctk.CTkFont("Arial", 11)).pack(side="left")
        ctk.CTkButton(z_f, text="➕", width=26, height=22, fg_color=CARD2, command=self._tl_zoom_in).pack(side="left", padx=2)
        ctk.CTkButton(z_f, text="➖", width=26, height=22, fg_color=CARD2, command=self._tl_zoom_out).pack(side="left", padx=2)
        tl_wrap = ctk.CTkFrame(tl_card, fg_color="transparent")
        tl_wrap.pack(fill="x", padx=8, pady=(2, 8))
        self.tl_canvas = tk.Canvas(tl_wrap, bg=CARD2, height=140, highlightthickness=2, highlightbackground=BORDER)
        tl_hscroll = tk.Scrollbar(tl_wrap, orient="horizontal", command=self.tl_canvas.xview)
        self.tl_canvas.configure(xscrollcommand=tl_hscroll.set)
        self.tl_canvas.pack(fill="x")
        tl_hscroll.pack(fill="x")
        self.tl_canvas.bind("<Button-1>", self._tl_click)
        self.tl_canvas.bind("<B1-Motion>", self._tl_drag)
        self.tl_canvas.bind("<ButtonRelease-1>", self._tl_release)
        self.tl_canvas.bind("<Double-Button-1>", self._tl_dblclick)
        self._render_timeline()
        self.snap_threshold_px = 12  # Yapışma eşik mesafesi (piksel)
        self._last_overlap_warn = False
        
        # ── Responsive Right Panel with Scrollable Content ───────────────────────────
        right_frame = ctk.CTkScrollableFrame(body, fg_color=CARD, corner_radius=10, width=160)
        right_frame.pack(side="right", fill="both", expand=True, padx=(6, 0))
        right_frame._scrollbar.configure(width=12)

        ctk.CTkLabel(right_frame, text="⚙️  Özellikler",
                     font=ctk.CTkFont("Arial", 13, "bold"), text_color=TXT).pack(pady=(8, 2), padx=8)

        prop_tabs = ctk.CTkTabview(right_frame,
                                   fg_color=CARD2,
                                   segmented_button_fg_color=CARD,
                                   segmented_button_selected_color=ACCENT2,
                                   segmented_button_selected_hover_color="#1a4472",
                                   segmented_button_unselected_color=CARD)
        prop_tabs.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        prop_tabs.add("🎬 Klip")
        prop_tabs.add("📝 Metin")
        prop_tabs.add("🎵 Ses")
        prop_tabs.add("🎬 Geçiş")

        # DÜZELTME: Uygulama açıldığında ilk olarak "Klip" sekmesinin görünmesini sağlıyoruz.
        prop_tabs.set("🎬 Klip")

        # ──────────── TAB 1: Klip Özellikleri (with Collapsible Sections) ────────────
        tab_clip = ctk.CTkScrollableFrame(prop_tabs.tab("🎬 Klip"), fg_color="transparent")
        tab_clip.pack(fill="both", expand=True)

        # Video Kırpma - Collapsible
        trim_section = CollapsibleSection(tab_clip, "Video Kırpma", "✂️")
        trim_section.pack(fill="x", pady=(0, 5))  # DÜZELTME: Section'ın kendisini paketliyoruz
        trim_section.get_content_frame().pack(fill="x")
        
        trim_f = ctk.CTkFrame(trim_section.get_content_frame(), fg_color=CARD, corner_radius=6)
        trim_f.pack(fill="x", padx=6, pady=2)
        for lbl, attr in [("Başlangıç (sn):", "trim_start_var"), ("Bitiş (sn):", "trim_end_var")]:
            row = ctk.CTkFrame(trim_f, fg_color="transparent"); row.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(row, text=lbl, text_color=TXT2, font=ctk.CTkFont("Arial", 11), width=110).pack(side="left")
            var = ctk.StringVar(value="0.0"); setattr(self, attr, var)
            ctk.CTkEntry(row, textvariable=var, width=90).pack(side="left", padx=4)
        ctk.CTkButton(trim_f, text="✓  Kırpmayı Uygula", height=28,
                      fg_color=ACCENT, hover_color="#1a6e2a", command=self._apply_trim).pack(fill="x", padx=8, pady=6)

        # Hız - Collapsible
        speed_section = CollapsibleSection(tab_clip, "Hız (Speed)", "⚡")
        speed_section.pack(fill="x", pady=(0, 5))  # DÜZELTME: Section'ın kendisini paketliyoruz
        speed_section.get_content_frame().pack(fill="x")
        
        speed_f = ctk.CTkFrame(speed_section.get_content_frame(), fg_color=CARD, corner_radius=6)
        speed_f.pack(fill="x", padx=6, pady=2)
        self.speed_var = ctk.DoubleVar(value=1.0)
        self.speed_lbl = ctk.CTkLabel(speed_f, text="1.00×", text_color=ACCENT2, font=ctk.CTkFont("Arial", 15, "bold"))
        self.speed_lbl.pack(pady=(6, 2))
        ctk.CTkSlider(speed_f, variable=self.speed_var, from_=0.25, to=4.0,
                      command=self._on_speed_slide).pack(fill="x", padx=10, pady=(0, 4))
        presets_row = ctk.CTkFrame(speed_f, fg_color="transparent"); presets_row.pack(fill="x", padx=8, pady=(0, 4))
        for s in [0.5, 1.0, 1.5, 2.0]:
            ctk.CTkButton(presets_row, text=f"{s}×", width=50, height=26, fg_color=CARD2,
                          hover_color=ACCENT2, font=ctk.CTkFont("Arial", 11),
                          command=lambda v=s: self._set_speed(v)).pack(side="left", padx=2)
        ctk.CTkButton(speed_f, text="✓  Hızı Uygula", height=28,
                      fg_color=ACCENT, hover_color="#1a6e2a", command=self._apply_speed).pack(fill="x", padx=8, pady=4)

        # Boyut / Ölçek - Collapsible
        scale_section = CollapsibleSection(tab_clip, "Boyut / Ölçek", "📐")
        scale_section.pack(fill="x", pady=(0, 5))  # DÜZELTME: Section'ın kendisini paketliyoruz
        scale_section.get_content_frame().pack(fill="x")
        
        scale_f = ctk.CTkFrame(scale_section.get_content_frame(), fg_color=CARD, corner_radius=6)
        scale_f.pack(fill="x", padx=6, pady=2)
        for lbl, attr in [("Genişlik (px):", "scale_w_var"), ("Yükseklik (px):", "scale_h_var")]:
            row = ctk.CTkFrame(scale_f, fg_color="transparent"); row.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(row, text=lbl, text_color=TXT2, font=ctk.CTkFont("Arial", 11), width=110).pack(side="left")
            var = ctk.StringVar(value="0"); setattr(self, attr, var)
            ctk.CTkEntry(row, textvariable=var, width=90).pack(side="left", padx=4)
        ctk.CTkLabel(scale_f, text="(0 = Orijinal boyutu koru)",
                     text_color=TXT2, font=ctk.CTkFont("Arial", 10)).pack(padx=8)
        preset_sc = ctk.CTkFrame(scale_f, fg_color="transparent"); preset_sc.pack(fill="x", padx=8, pady=4)
        for w, h, lbl in [(1920, 1080, "1080p"), (1280, 720, "720p"), (854, 480, "480p")]:
            ctk.CTkButton(preset_sc, text=lbl, width=60, height=26, fg_color=CARD2,
                          hover_color=ACCENT2, font=ctk.CTkFont("Arial", 11),
                          command=lambda ww=w, hh=h: self._set_scale(ww, hh)).pack(side="left", padx=2)
        ctk.CTkButton(scale_f, text="✓  Ölçeği Uygula", height=28,
                      fg_color=ACCENT, hover_color="#1a6e2a", command=self._apply_scale).pack(fill="x", padx=8, pady=6)

        # Video Efektleri - Collapsible
        fx_section = CollapsibleSection(tab_clip, "Video Efektleri", "🎨")
        fx_section.pack(fill="x", pady=(0, 5))  # DÜZELTME: Section'ın kendisini paketliyoruz
        fx_section.get_content_frame().pack(fill="x")
        
        fx_f = ctk.CTkFrame(fx_section.get_content_frame(), fg_color=CARD, corner_radius=6)
        fx_f.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(fx_f, text="Seçili klibe renk, filtre ve\ndönüşüm efektleri uygulayın.",
                     text_color=TXT2, font=ctk.CTkFont("Arial", 10), justify="left").pack(padx=8, pady=(6, 2))
        ctk.CTkButton(fx_f, text="🎨  Efekt & Filtre Aç", height=30,
                      fg_color="#d29922", hover_color="#b07d17",
                      font=ctk.CTkFont("Arial", 12, "bold"),
                      command=self._open_clip_effects).pack(fill="x", padx=8, pady=(2, 8))

        self.export_status = ctk.CTkLabel(tab_clip, text="", text_color=TXT2,
                                          font=ctk.CTkFont("Arial", 11), wraplength=260, justify="left")
        self.export_status.pack(padx=8, pady=4)

        # ──────────── TAB 2: Metin Katmanları ────────────────────────────
        tab_text = ctk.CTkFrame(prop_tabs.tab("📝 Metin"), fg_color="transparent")
        tab_text.pack(fill="both", expand=True)
        ctk.CTkLabel(tab_text, text="📝  Metin Katmanları",
                     font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(tab_text, text="➕  Yeni Metin Ekle", height=30,
                      fg_color=PURPLE, hover_color="#7c3aed",
                      command=self._add_text_overlay).pack(fill="x", padx=8, pady=(0, 6))
        self.overlay_list_frame = ctk.CTkScrollableFrame(tab_text, fg_color=CARD, corner_radius=6)
        self.overlay_list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # ──────────── TAB 3: Ses Parçaları ───────────────────────────────
        tab_audio = ctk.CTkFrame(prop_tabs.tab("🎵 Ses"), fg_color="transparent")
        tab_audio.pack(fill="both", expand=True)
        ctk.CTkLabel(tab_audio, text="🎵  Ses Parçaları",
                     font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(anchor="w", padx=8, pady=(8, 4))
        ctk.CTkButton(tab_audio, text="➕  Ses Ekle", height=30,
                      fg_color=CARD2, hover_color=BORDER,
                      command=self._import_audio).pack(fill="x", padx=8, pady=(0, 4))
        self.audio_list_frame = ctk.CTkScrollableFrame(tab_audio, fg_color=CARD, corner_radius=6)
        self.audio_list_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkFrame(tab_audio, height=1, fg_color=BORDER).pack(fill="x", padx=8, pady=6)
        self.audio_trim_frame = ctk.CTkFrame(tab_audio, fg_color="transparent")
        ctk.CTkLabel(self.audio_trim_frame, text="✂️  Ses Kırpma",
                     font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(anchor="w", padx=4)
        trim_audio_f = ctk.CTkFrame(self.audio_trim_frame, fg_color=CARD, corner_radius=6)
        trim_audio_f.pack(fill="x", pady=4)
        for lbl, attr in [("Başlangıç (sn):", "audio_trim_start_var"), ("Bitiş (sn):", "audio_trim_end_var")]:
            row = ctk.CTkFrame(trim_audio_f, fg_color="transparent"); row.pack(fill="x", padx=8, pady=3)
            ctk.CTkLabel(row, text=lbl, text_color=TXT2, font=ctk.CTkFont("Arial", 11), width=110).pack(side="left")
            var = ctk.StringVar(value="0.0"); setattr(self, attr, var)
            ctk.CTkEntry(row, textvariable=var, width=90).pack(side="left", padx=4)
        ctk.CTkButton(trim_audio_f, text="✓  Kırpmayı Uygula", height=28,
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      command=self._apply_audio_trim).pack(fill="x", padx=8, pady=4)
        self.audio_trim_frame.pack_forget()

        # ──────────── TAB 4: Geçiş Efektleri ─────────────────────────────
        tab_trans = ctk.CTkFrame(prop_tabs.tab("🎬 Geçiş"), fg_color="transparent")
        tab_trans.pack(fill="both", expand=True)
        ctk.CTkLabel(tab_trans, text="🎬  Geçiş Efektleri",
                     font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(tab_trans,
                     text="Seçili klipten sonraki klibe\nveya iki klip sınırına çift tıklayın",
                     font=ctk.CTkFont("Arial", 10), text_color=TXT2, justify="left").pack(anchor="w", padx=8)
        ctk.CTkButton(tab_trans, text="🎬  Geçiş Efekti Seç", height=32,
                      fg_color="#7c3aed", hover_color="#5b21b6",
                      font=ctk.CTkFont("Arial", 12, "bold"),
                      command=self._open_transition_picker).pack(fill="x", padx=8, pady=8)
        ctk.CTkFrame(tab_trans, height=1, fg_color=BORDER).pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(tab_trans, text="Mevcut Geçişler:",
                     font=ctk.CTkFont("Arial", 11, "bold"), text_color=TXT2).pack(anchor="w", padx=8, pady=(4, 2))
        self.transition_list_frame = ctk.CTkScrollableFrame(tab_trans, fg_color=CARD, corner_radius=6)
        self.transition_list_frame.pack(fill="both", expand=True, padx=8, pady=4)
        ctk.CTkLabel(self.transition_list_frame,
                     text="Henüz geçiş eklenmedi.\nTimeline'a en az 2 video ekleyin.",
                     font=ctk.CTkFont("Arial", 10), text_color=TXT2, justify="center").pack(pady=20)



    def _draw_placeholder(self):
        self.preview_canvas.delete("all")
        self.preview_canvas.configure(width=800, height=400)
        self.preview_canvas.create_rectangle(0, 0, 800, 400, fill="#0d1117", outline="")
        self.preview_canvas.create_text(400, 200, text="📽️  Video Önizleme\nTimeline'a video ekleyip oynat butonuna basın", fill=TXT2, font=("Arial", 14), justify="center")

    def _update_preview_at(self, tpos):
        active = None
        for clip in self.clips:
            if clip.timeline_start <= tpos < clip.timeline_end: active = clip; break
        if active is None: self._draw_placeholder(); return
        offset   = (tpos - active.timeline_start) * max(0.01, active.speed)
        clip_t   = min(active.trim_start + offset, active.trim_end - 0.033)
        def _get():
            try:
                cap = cv2.VideoCapture(active.path)
                if not cap.isOpened(): return None
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(clip_t * fps))
                ret, frame = cap.read(); cap.release()
                return frame if ret and frame is not None else None
            except: return None
        def _show(frame):
            if frame is None: return
            try:
                h, w = frame.shape[:2]; pw, ph = 800, 400
                scale = min(pw / w, ph / h); nw, nh = int(w * scale), int(h * scale)
                frame  = cv2.resize(frame, (nw, nh))
                pil    = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil)
                for ov in self.text_overlays:
                    if ov.start_time <= tpos <= ov.end_time:
                        try: fnt = ImageFont.truetype("arial.ttf", ov.size)
                        except: fnt = ImageFont.load_default()
                        ox, oy = int(ov.x * scale), int(ov.y * scale)
                        draw.text((ox, oy), ov.text, fill=ov.color, font=fnt)
                canvas_img = Image.new("RGB", (pw, ph), (0, 0, 0))
                canvas_img.paste(pil, ((pw - nw) // 2, (ph - nh) // 2))
                itk = ImageTk.PhotoImage(canvas_img)
                self._preview_img = itk
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(0, 0, anchor="nw", image=itk)
                self.preview_canvas.configure(width=pw, height=ph)
            except: pass
        def _thread():
            fr = _get()
            try: self.after(0, lambda: _show(fr))
            except: pass
        threading.Thread(target=_thread, daemon=True).start()

    def _start_preview_audio(self, clip, rel_pos):
        """ffmpeg ile klipten geçici WAV çıkarır ve pygame ile çalar."""
        if self._audio_extracting: return          # zaten çıkarım devam ediyor
        if not FFMPEG or not AUDIO_PLAY_OK: return
        if clip.mute or not self.preview_audio_var.get(): return

        self._audio_extracting     = True
        self._preview_playing_clip = clip.path    # bu path için zaten başlatıldı

        # Önce çalmayı durdur
        try: pygame.mixer.music.stop()
        except: pass

        # Önceki geçici WAV'ı sil
        old_tmp = self._prev_audio_tmp
        if old_tmp:
            try: os.remove(old_tmp)
            except: pass
        self._prev_audio_tmp = None

        import tempfile
        tmp = tempfile.mktemp(suffix="_prv.wav")
        self._prev_audio_tmp = tmp
        clip_path = clip.path   # thread içinde kapanma için

        def _extract():
            try:
                # INPUT-SIDE -ss (seek hızlı, büyük dosyada timeout olmaz)
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{max(0.0, rel_pos):.3f}",   # << -i'den ÖNCE
                    "-i", clip_path,
                    "-t", "60",                           # en fazla 60 sn
                    "-vn",
                    "-ac", "2", "-ar", "44100",
                    "-c:a", "pcm_s16le",
                    tmp
                ]
                r = subprocess.run(cmd, capture_output=True, timeout=12, **_no_window())
                if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 512:
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.play()
                else:
                    # ffmpeg başarısız — path sıfırla ki _play_tick tekrar denesin
                    self._preview_playing_clip = None
            except Exception as e:
                print(f"[Önizleme Ses] {e}")
                self._preview_playing_clip = None
            finally:
                self._audio_extracting = False

        threading.Thread(target=_extract, daemon=True).start()

    def _toggle_play(self):
        if self.playing: self._stop_play()
        else:
            if not self.clips: messagebox.showinfo("Bilgi", "Önce timeline'a video ekleyin."); return
            self.playing = True
            self._play_t0_wall = time.time()
            self._play_t0_pos  = self.playhead_pos
            self._preview_playing_clip = None   # _play_tick ilk tick'te ses başlatsın
            self._audio_extracting     = False
            self.btn_play.configure(text="⏸  Duraklat", fg_color=YELLOW, text_color="#000")
            self._play_tick()

    def _stop_play(self):
        self.playing = False
        if self._play_after:
            try: self.after_cancel(self._play_after)
            except: pass
        self._play_after            = None
        self._preview_playing_clip  = None
        self._audio_extracting      = False
        self.btn_play.configure(text="▶  Oynat", fg_color=ACCENT, text_color=TXT)
        if AUDIO_PLAY_OK:
            try: pygame.mixer.music.stop()
            except: pass

    def _play_tick(self):
        if not self.playing: return
        elapsed  = time.time() - self._play_t0_wall
        new_pos  = self._play_t0_pos + elapsed
        max_end  = max((c.timeline_end for c in self.clips), default=0)
        if new_pos >= max_end: self._seek(0.0); self._stop_play(); return

        active = next((c for c in self.clips if c.timeline_start <= new_pos < c.timeline_end), None)

        # ── Ses yönetimi ─────────────────────────────────────────────
        if active and not active.mute and self.preview_audio_var.get():
            clip_changed  = (active.path != self._preview_playing_clip)
            audio_stopped = (AUDIO_PLAY_OK and not pygame.mixer.music.get_busy()
                             and not self._audio_extracting)
            if clip_changed or audio_stopped:
                rel_pos = (new_pos - active.timeline_start) * active.speed + active.trim_start
                self._start_preview_audio(active, rel_pos)
        else:
            # Sessiz klip ya da ses kapalı
            if AUDIO_PLAY_OK and self._preview_playing_clip:
                try: pygame.mixer.music.stop()
                except: pass
            self._preview_playing_clip = None
        # ─────────────────────────────────────────────────────────────

        self.playhead_pos = new_pos
        self._update_seek_slider()
        self._update_preview_at(new_pos)
        self._render_timeline()
        self._play_after = self.after(33, self._play_tick)

    def _seek(self, pos):
        self.playhead_pos          = max(0.0, float(pos))
        self._preview_playing_clip = None
        self._audio_extracting     = False
        if self.playing:
            self._play_t0_wall = time.time()
            self._play_t0_pos  = self.playhead_pos
            if AUDIO_PLAY_OK:
                try: pygame.mixer.music.stop()
                except: pass
        self._update_seek_slider()
        self._update_preview_at(self.playhead_pos)
        self._render_timeline()

    def _on_seek_slide(self, val):
        max_end = max((c.timeline_end for c in self.clips), default=60)
        pos = float(val) / 100.0 * max_end
        self._seek(pos)

    def _update_seek_slider(self):
        max_end = max((c.timeline_end for c in self.clips), default=60)
        pct = (self.playhead_pos / max_end * 100) if max_end > 0 else 0
        self.seek_var.set(min(100.0, pct))
        mm, ss = divmod(int(self.playhead_pos), 60)
        tm, ts = divmod(int(max_end), 60)
        self.lbl_time.configure(text=f"{mm:02d}:{ss:02d} / {tm:02d}:{ts:02d}")

    def _render_timeline(self):
        c = self.tl_canvas; c.delete("all")
        try: cw = c.winfo_width()
        except: cw = 800
        total_w = max(int(self.timeline_dur * self.px_per_sec) + 120, cw if cw > 1 else 800)
        c.configure(scrollregion=(0, 0, total_w, 126))
        c.create_rectangle(0, 0, total_w, 22, fill="#1c2128", outline="")
        step = max(1, int(5 / max(0.1, self.px_per_sec / 50)))
        for s in range(0, int(self.timeline_dur) + step, step):
            x = s * self.px_per_sec; c.create_line(x, 16, x, 22, fill=BORDER)
            mm, ss = divmod(s, 60); c.create_text(x + 2, 11, text=f"{mm:02d}:{ss:02d}", fill=TXT2, anchor="w", font=("Arial", 9))
        c.create_text(3, 53, text="VIDEO", fill=TXT2, anchor="w", font=("Arial", 9, "bold"))
        c.create_text(3, 103, text="SES", fill=TXT2, anchor="w", font=("Arial", 9, "bold"))
        COLS = [ACCENT2, PURPLE, "#2d6a4f", "#6a2d4f", "#4f6a2d", "#6a4f2d"]
        CY, CH = self._CLIP_Y, self._CLIP_H
        sorted_clips = sorted(self.clips, key=lambda cc: cc.timeline_start)
        for i, clip in enumerate(sorted_clips):
            x0 = clip.timeline_start * self.px_per_sec; x1 = clip.timeline_end * self.px_per_sec
            col = COLS[i % len(COLS)]; is_sel = (clip is self.selected_clip); outline = "#ffffff" if is_sel else BORDER; width = 2 if is_sel else 1
            c.create_rectangle(x0, CY, x1, CY + CH, fill=col, outline=outline, width=width, tags=("clip", f"clip_{i}"))
            name = (clip.name[:18] + "…") if len(clip.name) > 18 else clip.name
            if clip.mute: name = "🔇 " + name
            c.create_text(x0 + 6, CY + 10, text=name, fill="white", anchor="w", font=("Arial", 9, "bold"), tags=(f"clip_{i}",))
            dur_mm, dur_ss = divmod(int(clip.clip_duration), 60); spd_txt = f"  {clip.speed}×" if clip.speed != 1.0 else ""
            c.create_text(x0 + 6, CY + 24, text=f"{dur_mm:02d}:{dur_ss:02d}{spd_txt}", fill="#c8d0da", anchor="w", font=("Arial", 9))
            if clip.scale_w > 0: c.create_text(x0 + 6, CY + 38, text=f"↔ {clip.scale_w}×{clip.scale_h}", fill="#c8d0da", anchor="w", font=("Arial", 8))
            c.create_rectangle(x0, CY, x0 + 7, CY + CH, fill="#fff" if is_sel else "#888", outline="", tags=(f"triml_{i}",))
            c.create_rectangle(x1 - 7, CY, x1, CY + CH, fill="#fff" if is_sel else "#888", outline="", tags=(f"trimr_{i}",))

        # ── Geçiş efekti işaretleri (klip birleşim noktaları) ──────────
        for i in range(len(sorted_clips) - 1):
            ca = sorted_clips[i]; cb = sorted_clips[i + 1]
            key = (id(ca), id(cb))
            trans = self.transitions.get(key, TransitionData("cut", 0.5))
            jx = ca.timeline_end * self.px_per_sec   # bağlantı x noktası
            cy_mid = CY + CH // 2
            r = 10   # elmas yarıçapı
            if trans.is_cut:
                # Kesim: küçük beyaz dikey çizgi
                c.create_line(jx, CY + 4, jx, CY + CH - 4, fill="#ffffff", width=2, dash=(4,3), tags=(f"trans_{i}",))
                c.create_text(jx, CY - 6, text="✂️", fill="#aaa", font=("Arial", 7), tags=(f"trans_{i}",))
            else:
                # Efekt: renkli elmas sembol
                pts = [jx, cy_mid - r, jx + r, cy_mid, jx, cy_mid + r, jx - r, cy_mid]
                c.create_polygon(pts, fill="#f59e0b", outline="#ffffff", width=1, tags=(f"trans_{i}",))
                c.create_text(jx, cy_mid, text=trans.emoji, font=("Arial", 8), fill="#000", tags=(f"trans_{i}",))
                # Süreyi göster
                c.create_text(jx, CY + CH + 4, text=f"{trans.duration:.1f}s", fill="#f59e0b",
                              font=("Arial", 7), tags=(f"trans_{i}",))

        for ov in self.text_overlays:
            x0 = ov.start_time * self.px_per_sec; x1 = ov.end_time * self.px_per_sec
            c.create_rectangle(x0, CY + CH + 2, x1, CY + CH + 10, fill=YELLOW, outline="")
            c.create_text(x0 + 2, CY + CH + 6, text="T", fill="#000", anchor="w", font=("Arial", 7, "bold"))
        AY, AH = self._AUDIO_Y, self._AUDIO_H
        for i, at in enumerate(self.audio_tracks):
            x0  = at.start_time * self.px_per_sec
            x1  = x0 + at.clip_duration * self.px_per_sec
            is_sel = (at is self.selected_audio)
            c.create_rectangle(x0, AY, x1, AY + AH, fill="#2d6a4f", outline="#fff" if is_sel else BORDER, width=2 if is_sel else 1, tags=(f"audio_{i}",))
            c.create_text(x0 + 4, AY + 8, text=f"🎵 {at.name[:18]} ({at.trim_start:.1f}→{at.trim_end:.1f})", fill="white", anchor="w", font=("Arial", 8))
        ph_x = self.playhead_pos * self.px_per_sec
        c.create_line(ph_x, 0, ph_x, 126, fill="#ff4444", width=2, tags="playhead")
        c.create_polygon(ph_x - 6, 0, ph_x + 6, 0, ph_x, 12, fill="#ff4444", tags="playhead")

    def _update_timeline_dur(self):
        if self.clips: self.timeline_dur = max(60.0, max(c.timeline_end for c in self.clips) + 10)
        else: self.timeline_dur = 60.0
        self._render_timeline()

    def _tl_click(self, e):
        cx  = self.tl_canvas.canvasx(e.x)
        pos = cx / max(1, self.px_per_sec)
        CY, CH = self._CLIP_Y, self._CLIP_H
        hit = None
        for i, clip in enumerate(self.clips):
            x0 = clip.timeline_start * self.px_per_sec; x1 = clip.timeline_end * self.px_per_sec
            if x0 <= cx <= x1 and CY <= e.y <= CY + CH:
                hit = clip
                if cx <= x0 + 7: self._drag_mode = "trim_l"
                elif cx >= x1 - 7: self._drag_mode = "trim_r"
                else: self._drag_mode = "move"; self._drag_offset = cx - x0
                break
        if hit:
            self.selected_clip = hit; self.selected_audio = None
            self._drag_clip = hit; self._drag_audio = None
            self._update_props_panel()
            self.audio_trim_frame.pack_forget()
            self._render_timeline(); return
        AY, AH = self._AUDIO_Y, self._AUDIO_H
        for i, at in enumerate(self.audio_tracks):
            x0 = at.start_time * self.px_per_sec; x1 = x0 + at.clip_duration * self.px_per_sec
            if x0 <= cx <= x1 and AY <= e.y <= AY + AH:
                self.selected_audio = at; self.selected_clip = None
                if cx <= x0 + 7: self._drag_mode = "trim_l"
                elif cx >= x1 - 7: self._drag_mode = "trim_r"
                else: self._drag_mode = "move"; self._drag_offset = cx - x0
                self._drag_audio = at; self._drag_clip = None
                self._update_audio_props(); self._render_timeline(); return
        self._drag_clip = None; self._drag_audio = None; self.selected_clip = None; self.selected_audio = None
        self._seek(max(0.0, pos)); self.audio_trim_frame.pack_forget()
        self._render_timeline()

    def _tl_drag(self, e):
        cx  = self.tl_canvas.canvasx(e.x)
        pos = max(0.0, cx / max(1, self.px_per_sec))
        self._last_overlap_warn = False  # Sürükleme sırasında bayrağı sıfırla

        if self._drag_clip:
            clip = self._drag_clip
            if self._drag_mode == "move":
                prop_start = max(0.0, pos - self._drag_offset / max(1, self.px_per_sec))
                new_s, new_e, warn = self._resolve_clip_placement(clip, prop_start, prop_start + clip.clip_duration, self.clips)
                clip.timeline_start = new_s
                self._last_overlap_warn = warn
            elif self._drag_mode == "trim_l":
                new_ts = min(pos, clip.timeline_end - 0.1)
                diff = new_ts - clip.timeline_start
                clip.timeline_start = new_ts
                clip.trim_start = max(0.0, min(clip.trim_start + diff * clip.speed, clip.trim_end - 0.1))
            elif self._drag_mode == "trim_r":
                new_end = max(clip.timeline_start + 0.1, pos)
                diff = new_end - clip.timeline_end
                clip.trim_end = max(clip.trim_start + 0.1, min(clip.trim_end + diff * clip.speed, clip.duration))
        elif self._drag_audio:
            audio = self._drag_audio
            if self._drag_mode == "move":
                prop_start = max(0.0, pos - self._drag_offset / max(1, self.px_per_sec))
                new_s, new_e, warn = self._resolve_clip_placement(audio, prop_start, prop_start + audio.clip_duration, self.audio_tracks)
                audio.start_time = new_s
                self._last_overlap_warn = warn
            elif self._drag_mode == "trim_l":
                new_ts = min(pos, audio.start_time + audio.clip_duration - 0.1)
                diff = new_ts - audio.start_time
                audio.start_time = new_ts
                audio.trim_start = max(0.0, min(audio.trim_start + diff, audio.trim_end - 0.1))
            elif self._drag_mode == "trim_r":
                new_end = max(audio.start_time + 0.1, pos)
                diff = new_end - (audio.start_time + audio.clip_duration)
                audio.trim_end = max(audio.trim_start + 0.1, min(audio.trim_end + diff, audio.duration))

        self._render_timeline()

    def _tl_release(self, e):
        if self._drag_clip:
            self._update_timeline_dur()
            self._update_props_panel()
        if self._drag_audio:
            self._update_audio_list()

        # 🚨 Üst üste binme denemesi uyarısı
        if self._last_overlap_warn:
            messagebox.showwarning("⚠️ Yerleştirme Uyarısı",
                "Klip üst üste binemez! Mevcut boşluk yetersiz olduğu için klip\n"
                "otomatik olarak en yakın geçerli konuma yapıştırıldı.")

        self._drag_clip = None
        self._drag_audio = None
        self._last_overlap_warn = False

    def _tl_zoom_in(self): self.px_per_sec = min(300, int(self.px_per_sec * 1.5)); self._render_timeline()
    def _tl_zoom_out(self): self.px_per_sec = max(8, int(self.px_per_sec / 1.5)); self._render_timeline()

    def _import_video(self):
        paths = filedialog.askopenfilenames(title="Video Seç", filetypes=[("Video Dosyaları", "*.mp4 *.avi *.mkv *.mov *.webm *.flv")])
        for path in paths:
            if not path: continue
            clip = ClipData(path)
            if clip.duration <= 0: messagebox.showerror("Hata", f"Süre okunamadı:\n{path}"); continue
            clip.timeline_start = (self.clips[-1].timeline_end if self.clips else 0.0)
            self.clips.append(clip); self._gen_thumbnail(clip); self._update_timeline_dur()
            if self.clips and self.selected_clip is None: self.selected_clip = self.clips[0]; self._update_props_panel()
        self._update_transition_list()

    def _gen_thumbnail(self, clip):
        def _run():
            try:
                cap = cv2.VideoCapture(clip.path); total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(total * 0.1)))
                ret, frame = cap.read(); cap.release()
                if ret and frame is not None:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); clip.thumbnails = [Image.fromarray(rgb).resize((60, 40), Image.LANCZOS)]
            except: pass
        threading.Thread(target=_run, daemon=True).start()

    def _import_audio(self):
        path = filedialog.askopenfilename(title="Ses Dosyası Seç", filetypes=[("Ses Dosyaları", "*.mp3 *.wav *.aac *.ogg *.flac *.m4a")])
        if not path: return
        last_end = 0.0
        for at in self.audio_tracks:
            end = at.start_time + at.duration
            if end > last_end: last_end = end
        at = AudioTrack(path, start_time=last_end)
        self.audio_tracks.append(at); self._update_audio_list(); self._render_timeline()

    def _update_props_panel(self):
        if not self.selected_clip: return
        c = self.selected_clip; self.trim_start_var.set(f"{c.trim_start:.2f}"); self.trim_end_var.set(f"{c.trim_end:.2f}")
        self.speed_var.set(c.speed); self.speed_lbl.configure(text=f"{c.speed:.2f}×")
        self.scale_w_var.set(str(c.scale_w)); self.scale_h_var.set(str(c.scale_h))
        if c.mute:
            self.btn_mute_clip.configure(text="🔊 Sesi Aç", fg_color=RED)
        else:
            self.btn_mute_clip.configure(text="🔇 Sesi Sil", fg_color=CARD2)

    # ════════════════════════════════════════════════════════════
    #  GEÇİŞ EFEKTİ – Yardımcı Metodlar
    # ════════════════════════════════════════════════════════════

    def _sorted_adjacent_pairs(self):
        """Sıralı klipler arasındaki komşu çift listesini döndürür."""
        sc = sorted(self.clips, key=lambda cc: cc.timeline_start)
        return [(sc[i], sc[i+1]) for i in range(len(sc)-1)]

    def _get_transition(self, clip_a, clip_b):
        """İki klip arasındaki TransitionData'yı döndürür; yoksa 'cut' oluşturur."""
        key = (id(clip_a), id(clip_b))
        if key not in self.transitions:
            self.transitions[key] = TransitionData("cut", 0.5)
        return self.transitions[key]

    def _set_transition(self, clip_a, clip_b, trans: TransitionData):
        key = (id(clip_a), id(clip_b))
        self.transitions[key] = trans
        self._render_timeline()
        self._update_transition_list()

    def _update_transition_list(self):
        """Geçiş sekmesindeki listeyi günceller."""
        if not hasattr(self, "transition_list_frame"):
            return
        for w in self.transition_list_frame.winfo_children():
            w.destroy()
        sc = sorted(self.clips, key=lambda cc: cc.timeline_start)
        pairs = [(sc[i], sc[i+1]) for i in range(len(sc)-1)]
        if not pairs:
            ctk.CTkLabel(self.transition_list_frame,
                         text="Henüz geçiş eklenmedi.\nTimeline'a en az 2 video ekleyin.",
                         font=ctk.CTkFont("Arial", 10), text_color=TXT2, justify="center").pack(pady=20)
            return
        for ca, cb in pairs:
            t   = self.transitions.get((id(ca), id(cb)), TransitionData("cut", 0.5))
            row = ctk.CTkFrame(self.transition_list_frame, fg_color=CARD2, corner_radius=6)
            row.pack(fill="x", pady=2, padx=4)
            # Sol: efekt adı + ok
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=6, pady=4)
            ctk.CTkLabel(info,
                         text=f"{ca.name[:12]}  →  {cb.name[:12]}",
                         font=ctk.CTkFont("Arial", 9), text_color=TXT2).pack(anchor="w")
            col = "#f59e0b" if not t.is_cut else TXT2
            ctk.CTkLabel(info,
                         text=f"{t.display_name}  {t.duration:.1f}s",
                         font=ctk.CTkFont("Arial", 10, "bold"), text_color=col).pack(anchor="w")
            # Sağ: Düzenle butonu
            ctk.CTkButton(row, text="✏️", width=30, height=28,
                          fg_color="#7c3aed", hover_color="#5b21b6",
                          command=lambda a=ca, b=cb: self._open_transition_picker(a, b)
                          ).pack(side="right", padx=4, pady=4)

    def _tl_dblclick(self, e):
        """Timeline üzerinde çift tıklama: geçiş bölgesine çift tıklanırsa picker aç."""
        cx  = self.tl_canvas.canvasx(e.x)
        CY, CH = self._CLIP_Y, self._CLIP_H
        if not (CY <= e.y <= CY + CH):
            return
        pairs = self._sorted_adjacent_pairs()
        HIT_RANGE = max(14, int(self.px_per_sec * 0.3))  # piksel toleransı
        for ca, cb in pairs:
            jx = ca.timeline_end * self.px_per_sec
            if abs(cx - jx) <= HIT_RANGE:
                self._open_transition_picker(ca, cb)
                return

    def _open_transition_picker(self, clip_a=None, clip_b=None):
        """
        Geçiş efekti seçim diyaloğunu açar.
        clip_a/clip_b None ise seçili klip + bir sonraki klip kullanılır.
        """
        sc = sorted(self.clips, key=lambda cc: cc.timeline_start)
        if clip_a is None or clip_b is None:
            if self.selected_clip and self.selected_clip in sc:
                idx = sc.index(self.selected_clip)
                if idx < len(sc) - 1:
                    clip_a, clip_b = sc[idx], sc[idx + 1]
                elif idx > 0:
                    clip_a, clip_b = sc[idx - 1], sc[idx]
                else:
                    messagebox.showwarning("Uyarı",
                        "Geçiş eklemek için timeline'da iki klip olmalı.\n"
                        "Önce bir klip seçin, ardından bu butona basın.")
                    return
            else:
                messagebox.showwarning("Uyarı",
                    "Geçiş eklemek için önce timeline'dan bir klip seçin.")
                return

        current = self._get_transition(clip_a, clip_b)

        dlg = ctk.CTkToplevel(self)
        dlg.title("Geçiş Efekti Seç")
        # --- GÜVENLİ İKON YÜKLEME ---
        # Dosyanın tam yolunu oluşturuyoruz
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "AQ2.ico")

        if os.path.exists(icon_path):
            try:
                # DÜZELTME BURADA: self yerine dlg kullanıyoruz!
                # Ayrıca after metodunu da dlg üzerinden çağırmak daha sağlıklıdır.
                dlg.after(200, lambda: dlg.wm_iconbitmap(icon_path))
        
            except Exception as e:
                print(f"İkon yükleme hatası: {e}")
        else:
            print("Uyarı: AQ2.ico dosyası bulunamadı.")
        # ----------------------------
        dlg.geometry("520x620")
        dlg.resizable(True, True)
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=CARD)
        dlg.grab_set()

        # Başlık
        ctk.CTkLabel(dlg, text="🎬  Geçiş Efekti",
                     font=ctk.CTkFont("Arial", 17, "bold"), text_color=TXT).pack(pady=(16, 2))
        ctk.CTkLabel(dlg,
                     text=f"{clip_a.name[:20]}  →  {clip_b.name[:20]}",
                     font=ctk.CTkFont("Arial", 11), text_color=TXT2).pack(pady=(0, 8))
        ctk.CTkFrame(dlg, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=4)

        # Efekt seçim listesi
        sel_fx = ctk.StringVar(value=current.effect)
        scroll = ctk.CTkScrollableFrame(dlg, fg_color=CARD2, corner_radius=8, height=340)
        scroll.pack(fill="x", padx=16, pady=4)

        # Renk haritası (görsel çeşitlilik)
        FX_COLORS = {
            "cut":        ("#374151", "#9ca3af"),
            "fade":       ("#1e3a5f", "#60a5fa"),
            "dissolve":   ("#1a3a2a", "#4ade80"),
            "wipeleft":   ("#3b2a1a", "#fb923c"),
            "zoomin":     ("#1e1a3a", "#a78bfa"),
            "jumpcut":    ("#3a1a1a", "#f87171"),
            "fadewhite":  ("#3a3a1a", "#fde68a"),
            "pixelize":   ("#2a1a3a", "#c084fc"),
            "diagtl":     ("#1a3a3a", "#67e8f9"),
            "radial":     ("#3a2a1a", "#fdba74"),
            "hlslice":    ("#1a2a3a", "#7dd3fc"),
            "smoothleft": ("#1a3a2f", "#6ee7b7"),
            "circlecrop": ("#3a1a2a", "#f9a8d4"),
            "slideleft":  ("#2a3a1a", "#bef264"),
        }

        for name, fx, desc, em in TRANSITION_EFFECTS:
            bg, fg = FX_COLORS.get(fx, (CARD2, TXT))
            row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2, padx=4)

            rb = ctk.CTkRadioButton(row, text="", variable=sel_fx, value=fx,
                                    fg_color=fg, hover_color=fg, width=24)
            rb.pack(side="left", padx=(8, 0), pady=8)

            ctk.CTkLabel(row, text=f"{em}  {name}",
                         font=ctk.CTkFont("Arial", 12, "bold"),
                         text_color=fg, width=150, anchor="w").pack(side="left", padx=8)
            ctk.CTkLabel(row, text=desc,
                         font=ctk.CTkFont("Arial", 10),
                         text_color=TXT2, anchor="w").pack(side="left", padx=4)
            # Tüm satıra tıklama
            row.bind("<Button-1>", lambda e, v=fx: sel_fx.set(v))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, v=fx: sel_fx.set(v))

        # Süre seçimi
        ctk.CTkFrame(dlg, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=6)
        dur_row = ctk.CTkFrame(dlg, fg_color="transparent")
        dur_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(dur_row, text="⏱  Geçiş Süresi:",
                     font=ctk.CTkFont("Arial", 12, "bold"),
                     text_color=TXT, width=140).pack(side="left")
        dur_var = ctk.DoubleVar(value=current.duration)
        dur_lbl = ctk.CTkLabel(dur_row,
                               text=f"{current.duration:.1f} sn",
                               font=ctk.CTkFont("Arial", 12, "bold"),
                               text_color=ACCENT2, width=60)
        dur_lbl.pack(side="right")
        def _upd_dur(v): dur_lbl.configure(text=f"{float(v):.1f} sn")
        ctk.CTkSlider(dur_row, variable=dur_var, from_=0.1, to=2.0,
                      command=_upd_dur).pack(side="left", fill="x", expand=True, padx=8)

        # Önayar butonları
        preset_row = ctk.CTkFrame(dlg, fg_color="transparent")
        preset_row.pack(fill="x", padx=20, pady=(0, 8))
        for lbl, val in [("Hızlı 0.3s", 0.3), ("Normal 0.5s", 0.5),
                         ("Yavaş 1.0s", 1.0), ("Sinematik 1.5s", 1.5)]:
            ctk.CTkButton(preset_row, text=lbl, width=100, height=26,
                          fg_color=CARD2, hover_color=BORDER,
                          font=ctk.CTkFont("Arial", 10),
                          command=lambda v=val: (dur_var.set(v), _upd_dur(v))
                          ).pack(side="left", padx=3)

        # Butonlar
        ctk.CTkFrame(dlg, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=4)
        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(pady=10)

        def _apply():
            trans = TransitionData(effect=sel_fx.get(), duration=round(dur_var.get(), 1))
            self._set_transition(clip_a, clip_b, trans)
            dlg.destroy()

        def _reset():
            trans = TransitionData("cut", 0.5)
            self._set_transition(clip_a, clip_b, trans)
            dlg.destroy()

        ctk.CTkButton(btn_row, text="✓  Uygula", width=130,
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=_apply).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="✂️  Sıfırla (Cut)", width=130,
                      fg_color=CARD2, hover_color=BORDER,
                      font=ctk.CTkFont("Arial", 12),
                      command=_reset).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="✗  İptal", width=100,
                      fg_color=RED, hover_color="#7f1d1d",
                      font=ctk.CTkFont("Arial", 12),
                      command=dlg.destroy).pack(side="left", padx=8)

    def _apply_trim(self):
        try: t0 = float(self.trim_start_var.get()); t1 = float(self.trim_end_var.get())
        except ValueError: messagebox.showerror("Hata", "Geçerli sayısal değer girin."); return
        if t1 <= t0: messagebox.showerror("Hata", "Bitiş zamanı başlangıçtan büyük olmalı."); return
        c = self.selected_clip; c.trim_start = max(0.0, t0); c.trim_end = min(c.duration, t1)
        self._update_timeline_dur(); messagebox.showinfo("✓", f"Kırpma uygulandı: {c.trim_start:.2f}s → {c.trim_end:.2f}s")

    def _on_speed_slide(self, val): self.speed_lbl.configure(text=f"{float(val):.2f}×")
    def _set_speed(self, v): self.speed_var.set(v); self.speed_lbl.configure(text=f"{v:.2f}×")
    def _apply_speed(self):
        if not self.selected_clip: messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip seçin."); return
        self.selected_clip.speed = round(float(self.speed_var.get()), 2)
        self._update_timeline_dur(); messagebox.showinfo("✓", f"Hız ayarlandı: {self.selected_clip.speed}×")

    def _set_scale(self, w, h): self.scale_w_var.set(str(w)); self.scale_h_var.set(str(h))
    def _apply_scale(self):
        if not self.selected_clip: messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip seçin."); return
        try: self.selected_clip.scale_w = int(self.scale_w_var.get()); self.selected_clip.scale_h = int(self.scale_h_var.get())
        except ValueError: messagebox.showerror("Hata", "Geçerli sayı girin."); return
        self._render_timeline(); messagebox.showinfo("✓", f"Ölçek: {self.selected_clip.scale_w}×{self.selected_clip.scale_h}")

    # ── KLİP BAŞINA VİDEO EFEKTLERİ ──────────────────────────────────────────

    def _build_clip_vf(self, eff, dur=None):
        """ClipData.effects dict'inden ffmpeg -vf filtre dizisi üretir."""
        vf = []
        # Dönüşümler (önce, aspect ratio korunur)
        if eff.get("rotate", False):  vf.append("transpose=1")
        if eff.get("mirror", False):  vf.append("hflip")
        if eff.get("vflip",  False):  vf.append("vflip")
        if eff.get("invert", False):  vf.append("negate")

        # Renk/ışık ayarları
        b = eff.get("brightness", 0.0)
        c = eff.get("contrast",   1.0)
        s = eff.get("saturation", 1.0)
        g = eff.get("gamma",      1.0)
        if any(v != d for v, d in [(b, 0.0), (c, 1.0), (s, 1.0), (g, 1.0)]):
            vf.append(f"eq=brightness={b}:contrast={c}:saturation={s}:gamma={g}")

        h_val = eff.get("hue", 0.0)
        if h_val != 0.0: vf.append(f"hue=h={h_val}")

        blur = eff.get("blur", 0.0)
        if blur > 0: vf.append(f"boxblur={blur}:1")

        # Renk filtreleri (sıra önemli – sadece biri etkin olmalı)
        if eff.get("sepia", False):
            vf.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif eff.get("bw", False):
            vf.append("hue=s=0")
        elif eff.get("red_filter", False):
            vf.append("colorchannelmixer=1:0:0:0:0:0:0:0:0:0:0:0")
        elif eff.get("blue_filter", False):
            vf.append("colorchannelmixer=0:0:0:0:0:0:0:0:0:0:1:0")

        if eff.get("vignette", False): vf.append("vignette")
        if eff.get("sharpen",  False): vf.append("unsharp=5:5:1.0:5:5:0.0")

        # Solma efektleri (sadece gerçek süre bilindiğinde)
        if dur is not None:
            fi = eff.get("fade_in",  0.0)
            fo = eff.get("fade_out", 0.0)
            if fi > 0: vf.append(f"fade=t=in:st=0:d={fi}")
            if fo > 0: vf.append(f"fade=t=out:st={max(0, dur - fo):.3f}:d={fo}")

        return vf

    def _open_clip_effects(self):
        """Seçili klip için efekt & filtre penceresini açar (canlı önizlemeli)."""
        clip = self.selected_clip
        if not clip:
            messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip seçin.")
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Efekt – {clip.name}")
        win.geometry("950x540")
        win.attributes("-topmost", True)
        win.grab_set()

        eff = clip.effects          # doğrudan klip dict'ine referans
        vars_dict = {}

        main_f = ctk.CTkFrame(win, fg_color="transparent")
        main_f.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Sol: ayar sekmeleri ──
        left_f = ctk.CTkFrame(main_f, width=420, fg_color="transparent")
        left_f.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tabs = ctk.CTkTabview(left_f)
        tabs.pack(fill="both", expand=True)
        t_color = tabs.add("Renk & Işık")
        t_fx    = tabs.add("Filtreler")
        t_trans = tabs.add("Dönüşüm")

        # ── Sağ: canlı önizleme ──
        right_f = ctk.CTkFrame(main_f, width=450, fg_color=CARD2, corner_radius=10)
        right_f.pack(side="right", fill="both", expand=True, padx=(6, 0))
        right_f.pack_propagate(False)
        ctk.CTkLabel(right_f, text="📸  Canlı Önizleme",
                     font=ctk.CTkFont("Arial", 14, "bold")).pack(pady=(10, 0))
        preview_lbl = ctk.CTkLabel(right_f, text="⏳  Yükleniyor…", text_color=TXT2)
        preview_lbl.pack(expand=True, fill="both", padx=10, pady=10)

        _timer = [None]

        def _schedule(*_):
            if _timer[0]: win.after_cancel(_timer[0])
            _timer[0] = win.after(400, _gen_preview)

        def _gen_preview():
            cur = {}
            for k, v in vars_dict.items():
                val = v.get()
                if isinstance(v, ctk.StringVar):
                    try: val = float(val)
                    except: val = 0.0
                cur[k] = val
            import threading as _th
            _th.Thread(target=_run_preview, args=(cur,), daemon=True).start()

        def _run_preview(cur_eff):
            import tempfile, subprocess as _sp
            vpath = clip.path
            tmp = os.path.join(tempfile.gettempdir(), f"tl_prev_{id(clip)}.jpg")

            # Bir kare çek (video ise orta kareye atla)
            dur_c = clip.clip_duration
            mid   = clip.trim_start + dur_c / 2

            vf_list = _build_vf_for_preview(cur_eff)
            cmd = ["ffmpeg", "-y", "-ss", f"{mid:.2f}", "-i", vpath, "-vframes", "1"]
            if vf_list: cmd += ["-vf", ",".join(vf_list)]
            cmd.append(tmp)

            try:
                r = _sp.run(cmd, capture_output=True, timeout=15, **_no_window())
                if r.returncode == 0 and os.path.exists(tmp):
                    from PIL import Image as _Img
                    img = _Img.open(tmp)
                    img.thumbnail((400, 320))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                    if win.winfo_exists():
                        win.after(0, lambda: preview_lbl.configure(image=ctk_img, text=""))
                else:
                    if win.winfo_exists():
                        win.after(0, lambda: preview_lbl.configure(text="⚠️  Önizleme oluşturulamadı.", image=""))
            except Exception:
                if win.winfo_exists():
                    win.after(0, lambda: preview_lbl.configure(text="⚠️  FFmpeg hatası.", image=""))

        def _build_vf_for_preview(cur_eff):
            # _build_clip_vf ile aynı mantık; fade'i hariç tut (preview için süre yok)
            return self._build_clip_vf(cur_eff, dur=None)

        # ── Yardımcı widget oluşturucular ──
        def _slider(parent, label, key, lo, hi, default):
            f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=label, width=130, anchor="w").pack(side="left")
            var = ctk.DoubleVar(value=eff.get(key, default)); vars_dict[key] = var
            sl  = ctk.CTkSlider(f, from_=lo, to=hi, variable=var); sl.pack(side="left", fill="x", expand=True, padx=8)
            lbl = ctk.CTkLabel(f, text=f"{var.get():.2f}", width=44); lbl.pack(side="left")
            def _cb(val, _l=lbl): _l.configure(text=f"{float(val):.2f}"); _schedule()
            sl.configure(command=_cb)

        def _switch(parent, label, key):
            var = ctk.BooleanVar(value=eff.get(key, False)); vars_dict[key] = var
            ctk.CTkSwitch(parent, text=label, variable=var, command=_schedule).pack(anchor="w", pady=5, padx=10)

        # Renk & Işık
        _slider(t_color, "Parlaklık",  "brightness", -1.0,  1.0, 0.0)
        _slider(t_color, "Kontrast",   "contrast",   -2.0,  2.0, 1.0)
        _slider(t_color, "Doygunluk",  "saturation",  0.0,  3.0, 1.0)
        _slider(t_color, "Gama",       "gamma",       0.1,  3.0, 1.0)
        _slider(t_color, "Ton (Hue)",  "hue",         0.0, 360.0, 0.0)

        # Filtreler
        _slider(t_fx, "Bulanıklık (Blur)", "blur", 0.0, 20.0, 0.0)
        _switch(t_fx, "Siyah Beyaz",        "bw")
        _switch(t_fx, "Sepya",              "sepia")
        _switch(t_fx, "Kırmızı Filtre",     "red_filter")
        _switch(t_fx, "Mavi Filtre",        "blue_filter")
        _switch(t_fx, "Vignette (Karartma)","vignette")
        _switch(t_fx, "Keskinleştir",       "sharpen")
        _switch(t_fx, "Renkleri Ters Çevir","invert")

        # Dönüşüm
        _switch(t_trans, "Ayna (Yatay Çevir)", "mirror")
        _switch(t_trans, "Dikey Çevir",         "vflip")
        _switch(t_trans, "Döndür (90° Sağa)",   "rotate")
        ctk.CTkLabel(t_trans, text="Solarak Girme (Fade In) sn:", anchor="w").pack(fill="x", padx=10, pady=(14, 0))
        fi_var = ctk.StringVar(value=str(eff.get("fade_in", 0.0))); vars_dict["fade_in"] = fi_var
        ctk.CTkEntry(t_trans, textvariable=fi_var).pack(fill="x", padx=10, pady=2)
        fi_var.trace_add("write", _schedule)
        ctk.CTkLabel(t_trans, text="Solarak Çıkma (Fade Out) sn:", anchor="w").pack(fill="x", padx=10, pady=(8, 0))
        fo_var = ctk.StringVar(value=str(eff.get("fade_out", 0.0))); vars_dict["fade_out"] = fo_var
        ctk.CTkEntry(t_trans, textvariable=fo_var).pack(fill="x", padx=10, pady=2)
        fo_var.trace_add("write", _schedule)

        def _save_and_close():
            for k, v in vars_dict.items():
                val = v.get()
                if isinstance(v, ctk.StringVar):
                    try: val = float(val)
                    except ValueError: val = 0.0
                eff[k] = val          # doğrudan clip.effects'e yazar
            win.destroy()

        ctk.CTkButton(left_f, text="💾  Efektleri Kaydet & Kapat",
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      command=_save_and_close).pack(pady=12, side="bottom")

        _schedule()   # pencere ilk açılışında önizlemeyi yükle

    def _update_audio_props(self):
        if not self.selected_audio: return
        at = self.selected_audio
        self.audio_trim_start_var.set(f"{at.trim_start:.2f}")
        self.audio_trim_end_var.set(f"{at.trim_end:.2f}")
        self.audio_trim_frame.pack(fill="x", padx=12, pady=(10, 4))

    def _apply_audio_trim(self):
        if not self.selected_audio: return
        try: t0 = float(self.audio_trim_start_var.get()); t1 = float(self.audio_trim_end_var.get())
        except ValueError: messagebox.showerror("Hata", "Geçerli sayı girin."); return
        if t1 <= t0: messagebox.showerror("Hata", "Bitiş, başlangıçtan büyük olmalı."); return
        at = self.selected_audio; at.trim_start = max(0.0, t0); at.trim_end = min(at.duration, t1)
        self._render_timeline(); messagebox.showinfo("✓", f"Ses kırpma uygulandı: {at.trim_start:.2f}s → {at.trim_end:.2f}s")

    def _add_text_overlay(self):
        dlg = ctk.CTkToplevel(self); dlg.title("Metin Katmanı Ekle"); dlg.geometry("400x430"); dlg.attributes("-topmost", True); dlg.configure(fg_color=CARD); dlg.grab_set()
        ctk.CTkLabel(dlg, text="📝  Metin Katmanı Ekle", font=ctk.CTkFont("Arial", 16, "bold"), text_color=TXT).pack(pady=(14, 8))
        frm = ctk.CTkFrame(dlg, fg_color="transparent"); frm.pack(fill="x", padx=20)
        def _field(parent, label, default):
            r = ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", pady=3)
            ctk.CTkLabel(r, text=label, width=130, anchor="w", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
            var = ctk.StringVar(value=str(default)); ctk.CTkEntry(r, textvariable=var, width=200).pack(side="left", padx=4); return var
        text_var = _field(frm, "Metin:", "Başlık"); x_var = _field(frm, "X konumu (px):", "50"); y_var = _field(frm, "Y konumu (px):", "50")
        t0_var = _field(frm, "Başlangıç (sn):", f"{self.playhead_pos:.1f}"); t1_var = _field(frm, "Bitiş (sn):", f"{self.playhead_pos + 5:.1f}")
        sz_r = ctk.CTkFrame(frm, fg_color="transparent"); sz_r.pack(fill="x", pady=3)
        ctk.CTkLabel(sz_r, text="Yazı boyutu:", width=130, anchor="w", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        sz_var = ctk.IntVar(value=32); sz_lbl = ctk.CTkLabel(sz_r, text="32", text_color=ACCENT2, font=ctk.CTkFont("Arial", 12, "bold"), width=30); sz_lbl.pack(side="right")
        ctk.CTkSlider(sz_r, variable=sz_var, from_=12, to=80, width=150, command=lambda v: sz_lbl.configure(text=str(int(float(v))))).pack(side="left", padx=4)
        color_h = {"val": "#ffffff"}
        def _pick():
            c = colorchooser.askcolor(color=color_h["val"], title="Metin Rengi")
            if c and c[1]: color_h["val"] = c[1]; col_btn.configure(fg_color=c[1], text_color="#000" if c[1].lower() in ("#ffffff","#ffff00") else "#fff")
        col_btn = ctk.CTkButton(frm, text="🎨  Renk Seç", fg_color="#ffffff", text_color="#000000", command=_pick); col_btn.pack(fill="x", pady=6)
        def _apply():
            try:
                ov = TextOverlay(text=text_var.get(), x=int(x_var.get()), y=int(y_var.get()), size=sz_var.get(), color=color_h["val"], start_time=float(t0_var.get()), end_time=float(t1_var.get()))
                self.text_overlays.append(ov); self._update_overlay_list(); self._render_timeline(); dlg.destroy()
            except ValueError as ex: messagebox.showerror("Hata", f"Geçersiz değer: {ex}")
        ctk.CTkButton(dlg, text="✓  Ekle", fg_color=ACCENT, command=_apply).pack(fill="x", padx=20, pady=8)

    def _update_overlay_list(self):
        for w in self.overlay_list_frame.winfo_children(): w.destroy()
        for ov in self.text_overlays:
            r = ctk.CTkFrame(self.overlay_list_frame, fg_color=CARD, corner_radius=6); r.pack(fill="x", pady=2, padx=4)
            ctk.CTkLabel(r, text=f"📝 {ov.text[:16]}  ({ov.start_time:.1f}s→{ov.end_time:.1f}s)  [{ov.x},{ov.y}]",
                         font=ctk.CTkFont("Arial", 10), text_color=TXT).pack(side="left", padx=6, pady=4)
            ctk.CTkButton(r, text="🗑", width=28, height=24, fg_color=RED,
                          command=lambda o=ov: self._remove_overlay(o)).pack(side="right", padx=4, pady=4)
            ctk.CTkButton(r, text="✏️", width=28, height=24, fg_color=PURPLE, hover_color="#5b21b6",
                          command=lambda o=ov: self._edit_text_overlay(o)).pack(side="right", padx=2, pady=4)

    def _edit_text_overlay(self, ov):
        """Mevcut bir metin katmanını düzenlemek için diyalog açar."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Metin Katmanını Düzenle")
        dlg.geometry("400x460")
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=CARD)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="✏️  Metin Katmanını Düzenle",
                     font=ctk.CTkFont("Arial", 16, "bold"), text_color=TXT).pack(pady=(14, 8))

        frm = ctk.CTkFrame(dlg, fg_color="transparent")
        frm.pack(fill="x", padx=20)

        def _field(parent, label, default):
            row = ctk.CTkFrame(parent, fg_color="transparent"); row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=130, anchor="w", text_color=TXT2,
                         font=ctk.CTkFont("Arial", 12)).pack(side="left")
            var = ctk.StringVar(value=str(default))
            ctk.CTkEntry(row, textvariable=var, width=200).pack(side="left", padx=4)
            return var

        text_var = _field(frm, "Metin:", ov.text)
        x_var    = _field(frm, "X konumu (px):", str(ov.x))
        y_var    = _field(frm, "Y konumu (px):", str(ov.y))
        t0_var   = _field(frm, "Başlangıç (sn):", f"{ov.start_time:.1f}")
        t1_var   = _field(frm, "Bitiş (sn):",     f"{ov.end_time:.1f}")

        sz_r = ctk.CTkFrame(frm, fg_color="transparent"); sz_r.pack(fill="x", pady=3)
        ctk.CTkLabel(sz_r, text="Yazı boyutu:", width=130, anchor="w",
                     text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        sz_var = ctk.IntVar(value=ov.size)
        sz_lbl = ctk.CTkLabel(sz_r, text=str(ov.size), text_color=ACCENT2,
                              font=ctk.CTkFont("Arial", 12, "bold"), width=30)
        sz_lbl.pack(side="right")
        ctk.CTkSlider(sz_r, variable=sz_var, from_=12, to=80, width=150,
                      command=lambda v: sz_lbl.configure(text=str(int(float(v))))).pack(side="left", padx=4)

        color_h = {"val": ov.color}

        def _pick():
            c = colorchooser.askcolor(color=color_h["val"], title="Metin Rengi")
            if c and c[1]:
                color_h["val"] = c[1]
                col_btn.configure(fg_color=c[1],
                                  text_color="#000" if c[1].lower() in ("#ffffff", "#ffff00") else "#fff")

        col_btn = ctk.CTkButton(frm, text="🎨  Renk Seç", fg_color=ov.color,
                                text_color="#000000" if ov.color.lower() in ("#ffffff", "#ffff00") else "#ffffff",
                                command=_pick)
        col_btn.pack(fill="x", pady=6)

        def _apply():
            try:
                ov.text       = text_var.get()
                ov.x          = int(x_var.get())
                ov.y          = int(y_var.get())
                ov.size       = sz_var.get()
                ov.color      = color_h["val"]
                ov.start_time = float(t0_var.get())
                ov.end_time   = float(t1_var.get())
                self._update_overlay_list()
                self._render_timeline()
                dlg.destroy()
            except ValueError as ex:
                messagebox.showerror("Hata", f"Geçersiz değer: {ex}")

        ctk.CTkButton(dlg, text="💾  Değişiklikleri Kaydet",
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      command=_apply).pack(fill="x", padx=20, pady=8)

    def _remove_overlay(self, ov):
        if ov in self.text_overlays: self.text_overlays.remove(ov); self._update_overlay_list(); self._render_timeline()

    def _toggle_mute_selected(self):
        if not self.selected_clip:
            messagebox.showwarning("Uyarı", "Önce timeline'dan bir video klip seçin.")
            return
        self.selected_clip.mute = not self.selected_clip.mute
        if self.selected_clip.mute:
            self.btn_mute_clip.configure(text="🔊 Sesi Aç", fg_color=RED)
            messagebox.showinfo("🔇 Ses Silindi", f"'{self.selected_clip.name}' klibinin sesi dışa aktarmada sessiz olacak.")
        else:
            self.btn_mute_clip.configure(text="🔇 Sesi Sil", fg_color=CARD2)
            messagebox.showinfo("🔊 Ses Açıldı", f"'{self.selected_clip.name}' klibinin sesi yeniden aktif.")
        self._render_timeline()

    def _extract_audio(self):
        if not FFMPEG: messagebox.showerror("Hata", "Bu özellik ffmpeg gerektiriyor!"); return
        if not self.selected_clip: messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip seçin."); return
        out = filedialog.asksaveasfilename(title="Sesi Kaydet", defaultextension=".mp3", filetypes=[("MP3", "*.mp3"), ("WAV", "*.wav"), ("AAC", "*.aac")])
        if not out: return
        self.export_status.configure(text="⏳ Ses ayırılıyor…", text_color=YELLOW)
        def _run():
            try:
                acodec = "libmp3lame" if out.endswith(".mp3") else "pcm_s16le"
                cmd = ["ffmpeg", "-y", "-i", self.selected_clip.path, "-vn", "-c:a", acodec, out]
                r = subprocess.run(cmd, capture_output=True, timeout=180, **_no_window())
                if r.returncode == 0: self.after(0, lambda: self.export_status.configure(text=f"✓ Ses ayırıldı:\n{os.path.basename(out)}", text_color=ACCENT))
                else: self.after(0, lambda: self.export_status.configure(text="✗ Ses ayırma başarısız", text_color=RED))
            except Exception as ex: self.after(0, lambda: self.export_status.configure(text=f"✗ Hata: {ex}", text_color=RED))
        threading.Thread(target=_run, daemon=True).start()

    def _update_audio_list(self):
        for w in self.audio_list_frame.winfo_children(): w.destroy()
        for at in self.audio_tracks:
            r = ctk.CTkFrame(self.audio_list_frame, fg_color=CARD, corner_radius=6); r.pack(fill="x", pady=2, padx=4)
            ctk.CTkLabel(r, text=f"🎵 {at.name[:18]}  @{at.start_time:.1f}s",
                         font=ctk.CTkFont("Arial", 10), text_color=TXT).pack(side="left", padx=6, pady=4)
            ctk.CTkButton(r, text="🗑", width=28, height=24, fg_color=RED,
                          command=lambda a=at: self._remove_audio(a)).pack(side="right", padx=4, pady=4)
            ctk.CTkButton(r, text="📍", width=28, height=24, fg_color="#1f538d", hover_color="#2a6ca8",
                          command=lambda a=at: self._position_audio(a)).pack(side="right", padx=2, pady=4)

    def _position_audio(self, at):
        """Ses parçasının timeline'daki başlangıç konumunu ayarlamak için diyalog açar."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Ses Konumunu Ayarla")
        dlg.geometry("380x260")
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=CARD)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="📍  Ses Konumunu Ayarla",
                     font=ctk.CTkFont("Arial", 15, "bold"), text_color=TXT).pack(pady=(16, 4))
        ctk.CTkLabel(dlg, text=f"🎵  {at.name}",
                     font=ctk.CTkFont("Arial", 11), text_color=TXT2).pack(pady=(0, 12))

        frm = ctk.CTkFrame(dlg, fg_color=CARD2, corner_radius=8)
        frm.pack(fill="x", padx=20, pady=4)

        # Başlangıç zamanı
        row1 = ctk.CTkFrame(frm, fg_color="transparent"); row1.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(row1, text="Başlangıç (sn):", width=130, anchor="w",
                     text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        start_var = ctk.StringVar(value=f"{at.start_time:.2f}")
        ctk.CTkEntry(row1, textvariable=start_var, width=120).pack(side="left", padx=4)

        # Oynatma kafası konumuna yapıştır butonu
        def _snap_to_playhead():
            start_var.set(f"{self.playhead_pos:.2f}")

        ctk.CTkButton(frm, text="▶  Oynatma Kafasına Yapıştır",
                      fg_color=ACCENT2, hover_color="#174d7c", height=28,
                      command=_snap_to_playhead).pack(fill="x", padx=12, pady=(0, 8))

        # Süre bilgisi
        dur_mm, dur_ss = divmod(int(at.clip_duration), 60)
        ctk.CTkLabel(dlg, text=f"Ses süresi: {dur_mm:02d}:{dur_ss:02d}  ({at.clip_duration:.1f} sn)",
                     font=ctk.CTkFont("Arial", 10), text_color=TXT2).pack(pady=4)

        def _apply():
            try:
                new_start = float(start_var.get())
                if new_start < 0:
                    messagebox.showerror("Hata", "Başlangıç zamanı 0'dan küçük olamaz."); return
                at.start_time = new_start
                self._update_audio_list()
                self._render_timeline()
                dlg.destroy()
            except ValueError:
                messagebox.showerror("Hata", "Geçerli bir sayı girin.")

        ctk.CTkButton(dlg, text="💾  Konumu Kaydet",
                      fg_color=ACCENT, hover_color="#1a6e2a", height=36,
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=_apply).pack(fill="x", padx=20, pady=10)
    
    def _resolve_clip_placement(self, clip, new_start, new_end, track_list):
        px_s = self.px_per_sec
        snap = self.snap_threshold_px
        duration = new_end - new_start

        def _get_end(t): return t.timeline_end if hasattr(t, "timeline_end") else t.start_time + t.clip_duration

        # 1️⃣ SİHİRLİ YAPIŞMA (MAGNETIC SNAP)
        candidates = []
        for other in track_list:
            if other is clip: continue
            o_s = other.timeline_start * px_s
            o_e = _get_end(other) * px_s
            if abs(new_start * px_s - o_e) <= snap: candidates.append(o_e / px_s)
            if abs(new_end * px_s - o_s) <= snap: candidates.append((o_s / px_s) - duration)

        if candidates:
            candidates.sort(key=lambda c: abs(c - new_start))
            for cand in candidates:
                cand_end = cand + duration
                # Sadece çakışma olmayan ilk yapışma noktasını kabul et
                if not any(cand < _get_end(o) and cand_end > o.timeline_start for o in track_list if o is not clip):
                    new_start = cand
                    new_end = new_start + duration
                    break

        # 2️⃣ ÇAKIŞMA ENGELLEME (OVERLAP PREVENTION)
        warn = False
        for other in track_list:
            if other is clip: continue
            o_end = _get_end(other)
            if new_start < o_end and new_end > other.timeline_start:
                # Çakışma tespit edildi, en yakın güvenli kenara it
                if abs(new_start - o_end) <= abs(other.timeline_start - new_end):
                    new_start = o_end
                else:
                    new_start = other.timeline_start - duration
                new_start = max(0.0, new_start)
                new_end = new_start + duration
                # Eğer boşluk yetersizse hala çakışıyor demektir -> Uyarı bayrağı
                if new_start < o_end and new_end > other.timeline_start:
                    warn = True
                break
        return new_start, new_end, warn

    def _remove_audio(self, at):
        if at in self.audio_tracks: self.audio_tracks.remove(at); self._update_audio_list(); self._render_timeline()

    def _delete_selected(self):
        if self.selected_clip:
            if messagebox.askyesno("Onay", f"'{self.selected_clip.name}' silinsin mi?"):
                # Geçişleri temizle
                clip_id = id(self.selected_clip)
                keys_to_del = [k for k in self.transitions if clip_id in k]
                for k in keys_to_del: del self.transitions[k]
                self.clips.remove(self.selected_clip); self.selected_clip = None; self._update_timeline_dur()
        elif self.selected_audio:
            if messagebox.askyesno("Onay", f"'{self.selected_audio.name}' silinsin mi?"):
                self.audio_tracks.remove(self.selected_audio); self.selected_audio = None; self._update_audio_list(); self._render_timeline()
        else:
            messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip veya ses seçin.")

    def _delete_selected_clip(self):
        if not self.selected_clip: messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip seçin."); return
        if messagebox.askyesno("Onay", f"'{self.selected_clip.name}' silinsin mi?"):
            self.clips.remove(self.selected_clip); self.selected_clip = None; self._update_timeline_dur()

    def _split_selected(self):
        if self.selected_clip:
            self._split_video_clip()
        elif self.selected_audio:
            self._split_audio_track()
        else:
            messagebox.showwarning("Uyarı", "Önce timeline'dan bir klip veya ses seçin.")

    def _split_video_clip(self):
        if not self.selected_clip: return
        clip = self.selected_clip
        split_pos = self.playhead_pos
        
        if not (clip.timeline_start < split_pos < clip.timeline_end):
            messagebox.showwarning("Uyarı", "Bölme noktası klibin içinde olmalı!")
            return

        new_clip1 = ClipData(clip.path)
        new_clip1.timeline_start = clip.timeline_start
        new_clip1.trim_start = clip.trim_start
        split_in_clip = (split_pos - clip.timeline_start) * clip.speed
        new_clip1.trim_end = clip.trim_start + split_in_clip
        new_clip1.speed = clip.speed
        new_clip1.scale_w = clip.scale_w
        new_clip1.scale_h = clip.scale_h
        
        new_clip2 = ClipData(clip.path)
        new_clip2.timeline_start = split_pos
        new_clip2.trim_start = new_clip1.trim_end
        new_clip2.trim_end = clip.trim_end
        new_clip2.speed = clip.speed
        new_clip2.scale_w = clip.scale_w
        new_clip2.scale_h = clip.scale_h
        
        idx = self.clips.index(clip)
        self.clips.pop(idx)
        self.clips.insert(idx, new_clip2)
        self.clips.insert(idx, new_clip1)
        
        self.selected_clip = None
        self._render_timeline()
        self._update_timeline_dur()

    def _split_audio_track(self):
        if not self.selected_audio: return
        audio = self.selected_audio
        split_pos = self.playhead_pos
        
        if not (audio.start_time < split_pos < audio.start_time + audio.clip_duration):
            messagebox.showwarning("Uyarı", "Bölme noktası ses parçasının içinde olmalı!")
            return

        new_audio1 = AudioTrack(audio.path, start_time=audio.start_time, volume=audio.volume)
        new_audio1.trim_start = audio.trim_start
        split_in_audio = (split_pos - audio.start_time)
        new_audio1.trim_end = audio.trim_start + split_in_audio
        
        new_audio2 = AudioTrack(audio.path, start_time=split_pos, volume=audio.volume)
        new_audio2.trim_start = new_audio1.trim_end
        new_audio2.trim_end = audio.trim_end
        
        idx = self.audio_tracks.index(audio)
        self.audio_tracks.pop(idx)
        self.audio_tracks.insert(idx, new_audio2)
        self.audio_tracks.insert(idx, new_audio1)
        
        self.selected_audio = None
        self._render_timeline()

    def _export(self):
        if not self.clips: messagebox.showwarning("Uyarı", "Timeline'a en az bir video ekleyin."); return
        if not FFMPEG: messagebox.showerror("Hata", "Export için ffmpeg gereklidir!"); return

        # ── Çözünürlük seçim diyaloğu ──────────────────────────────
        res_result = {"value": None, "cancelled": False}
        dlg = ctk.CTkToplevel()
        dlg.title("📐 Dışa Aktarma Ayarları")
        dlg.geometry("380x310")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color=CARD)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="📐  Çözünürlük Seç", font=ctk.CTkFont("Arial", 15, "bold"), text_color=TXT).pack(pady=(16, 6))
        ctk.CTkFrame(dlg, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=4)

        res_var = ctk.StringVar(value="Orijinal")
        resolutions = [
            ("Orijinal (kaynak boyutu)",  "Orijinal"),
            ("3840 × 2160  (4K UHD)",     "3840x2160"),
            ("1920 × 1080  (Full HD)",    "1920x1080"),
            ("1280 × 720   (HD)",         "1280x720"),
            ("854 × 480    (SD)",         "854x480"),
            ("640 × 360    (360p)",       "640x360"),
        ]
        for label, val in resolutions:
            ctk.CTkRadioButton(dlg, text=label, variable=res_var, value=val,
                               font=ctk.CTkFont("Arial", 12), text_color=TXT,
                               fg_color=ACCENT2).pack(anchor="w", padx=24, pady=2)

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(pady=14)
        def _ok():
            res_result["value"] = res_var.get()
            dlg.destroy()
        def _cancel():
            res_result["cancelled"] = True
            dlg.destroy()
        ctk.CTkButton(btn_row, text="✓  Devam Et", width=130, fg_color=ACCENT, hover_color="#1a6e2a", command=_ok).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="✗  İptal",    width=100, fg_color=RED,    hover_color="#7f1d1d", command=_cancel).pack(side="left", padx=8)
        dlg.wait_window()

        if res_result["cancelled"] or res_result["value"] is None: return
        chosen_res = res_result["value"]   # örn. "1920x1080" veya "Orijinal"
        # ────────────────────────────────────────────────────────────

        out = filedialog.asksaveasfilename(title="Videoyu Kaydet", defaultextension=".mp4", filetypes=[("MP4", "*.mp4"), ("MKV", "*.mkv")])
        if not out: return
        self.export_status.configure(text="⏳ Dışa aktarılıyor…", text_color=YELLOW)
        def _run():
            try:
                tmp_dir = os.path.join(os.path.dirname(out), "_tleditor_tmp_")
                os.makedirs(tmp_dir, exist_ok=True)
                processed = []
                sorted_clips = sorted(self.clips, key=lambda cc: cc.timeline_start)

                for i, clip in enumerate(sorted_clips):
                    tmp_out = os.path.join(tmp_dir, f"seg_{i:04d}.mp4")
                    v_filters, a_filters = [], []

                    # ── Hız ────────────────────────────────────────
                    if clip.speed != 1.0:
                        v_filters.append(f"setpts={1/clip.speed:.4f}*PTS")
                        spd = clip.speed
                        if 0.5 <= spd <= 2.0:   a_filters.append(f"atempo={spd:.4f}")
                        elif spd > 2.0:          a_filters.extend([f"atempo=2.0", f"atempo={spd/2:.4f}"])
                        else:                    a_filters.extend([f"atempo=0.5", f"atempo={spd*2:.4f}"])

                    # ── Mute → volume=0 (akış tipi aynı kalsın, concat bozulmasın) ──
                    if clip.mute:
                        a_filters.append("volume=0")

                    # ── Çözünürlük / ölçek ──────────────────────────
                    if chosen_res != "Orijinal":
                        rw, rh = chosen_res.split("x")
                        v_filters.append(
                            f"scale={rw}:{rh}:force_original_aspect_ratio=decrease,"
                            f"pad={rw}:{rh}:(ow-iw)/2:(oh-ih)/2:color=black"
                        )
                    elif clip.scale_w > 0 and clip.scale_h > 0:
                        v_filters.append(f"scale={clip.scale_w}:{clip.scale_h}")

                    # ── Video Efektleri (renk, filtre, dönüşüm, solma) ──────────
                    clip_eff = getattr(clip, "effects", {})
                    if clip_eff:
                        eff_vf = self._build_clip_vf(clip_eff, dur=clip.clip_duration)
                        v_filters.extend(eff_vf)

                    # ── Metin katmanları ────────────────────────────
                    clip_dur = clip.clip_duration
                    out_ss = clip.trim_start / clip.speed  # Orijinal zamanın filtredeki (PTS) karşılığı
                    
                    # --- FONT YOLUNU DİNAMİK VE GÜVENLİ BELİRLEME ---
                    import sys
                    if os.name == 'nt':
                        # Windows: C:\Windows\Fonts\arial.ttf -> FFmpeg için C\:/Windows/Fonts/arial.ttf
                        win_dir = os.environ.get("windir", "C:\\Windows").replace("\\", "/")
                        ff_font = win_dir.replace(":", "\\:") + "/Fonts/arial.ttf"
                    elif sys.platform == 'darwin':
                        ff_font = "/Library/Fonts/Arial.ttf"
                    else:
                        ff_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    # ------------------------------------------------

                    for ov in self.text_overlays:
                        rel_s = ov.start_time - clip.timeline_start
                        rel_e = ov.end_time   - clip.timeline_start
                        if rel_e > 0 and rel_s < clip_dur:
                            rs   = max(0.0, rel_s); re = min(clip_dur, rel_e)
                            
                            rs_adj = out_ss + rs
                            re_adj = out_ss + re
                            
                            safe = ov.text.replace("\\","\\\\").replace("'","\\'").replace(":","\\:").replace(",", "\\,")
                            hx   = ov.color.lstrip("#")
                            
                            # DÜZELTME: drawtext içine fontfile='{ff_font}' parametresi eklendi
                            v_filters.append(
                                f"drawtext=fontfile='{ff_font}':text='{safe}':fontsize={ov.size}:"
                                f"fontcolor=0x{hx}:x={ov.x}:y={ov.y}:"
                                f"enable='between(t,{rs_adj:.3f},{re_adj:.3f})'"
                            )

                    # ── ffmpeg komutu (output-side seeking — daha güvenilir) ────
                    seg_dur = clip.trim_end - clip.trim_start
                    out_t = seg_dur / clip.speed  # DÜZELTME 3: Çıktı süresi de klibin hızına göre ayarlanmalı
                    
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", clip.path,
                        "-ss", f"{out_ss:.3f}",
                        "-t",  f"{out_t:.3f}",
                    ]
                    if v_filters: cmd += ["-vf", ",".join(v_filters)]
                    if a_filters: cmd += ["-af", ",".join(a_filters)]
                    cmd += [
                        "-c:v", "libx264", "-preset", "fast",
                        "-c:a", "aac", "-b:a", "192k",
                        "-avoid_negative_ts", "make_zero",
                        "-movflags", "+faststart",
                        tmp_out
                    ]
                    r = subprocess.run(cmd, capture_output=True, timeout=600, **_no_window())
                    if r.returncode == 0:
                        processed.append(tmp_out)
                    else:
                        err = r.stderr.decode("utf-8", errors="replace")[-600:]
                        self.after(0, lambda e=err: self.export_status.configure(
                            text=f"✗ Segment hatası:\n{e[:160]}", text_color=RED))
                        return

                # ── Segmentleri birleştir (Geçiş efektleri dahil) ──────────────
                if len(processed) == 1:
                    final_vid = processed[0]
                else:
                    # Geçiş efektleri var mı kontrol et
                    has_fx = False
                    pairs = [(sorted_clips[i], sorted_clips[i+1]) for i in range(len(sorted_clips)-1)]
                    for ca, cb in pairs:
                        t = self.transitions.get((id(ca), id(cb)), TransitionData("cut", 0.5))
                        if not t.is_cut:
                            has_fx = True; break

                    if not has_fx:
                        # Geçiş yok → hızlı concat kopyalama
                        lst = os.path.join(tmp_dir, "list.txt")
                        with open(lst, "w", encoding="utf-8") as f:
                            for p in processed:
                                f.write(f"file '{p.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
                        final_vid = os.path.join(tmp_dir, "merged.mp4")
                        r2 = subprocess.run(
                            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                             "-i", lst, "-c", "copy", final_vid],
                            capture_output=True, timeout=600, **_no_window()
                        )
                        if r2.returncode != 0:
                            err2 = r2.stderr.decode("utf-8", errors="replace")[-400:]
                            self.after(0, lambda e=err2: self.export_status.configure(
                                text=f"✗ Birleştirme hatası:\n{e[:120]}", text_color=RED))
                            return
                    else:
                        # ── xfade filter_complex ile geçiş efektleri ─────────────
                        self.after(0, lambda: self.export_status.configure(
                            text="⚙️ Geçiş efektleri uygulanıyor…", text_color=YELLOW))

                        # ── Her segmentin gerçek süresini ölç ──────────────────
                        seg_durs = []
                        for p in processed:
                            seg_durs.append(max(0.1, VideoEditor.get_duration(p)))

                        # ── Segment çözünürlüklerini normalize et ─────────────
                        # xfade tüm girişlerin aynı boyutta olmasını gerektirir.
                        # İlk segmentin boyutunu referans al, diğerlerini ölçekle.
                        def _get_res(path):
                            try:
                                r = subprocess.run(
                                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                                     "-show_entries", "stream=width,height",
                                     "-of", "csv=p=0", path],
                                    capture_output=True, timeout=15, **_no_window())
                                w, h = r.stdout.decode().strip().split(",")
                                return int(w), int(h)
                            except:
                                return None, None

                        ref_w, ref_h = _get_res(processed[0])
                        norm_processed = list(processed)

                        if ref_w and ref_h:
                            for pi, p in enumerate(processed[1:], 1):
                                pw, ph = _get_res(p)
                                if pw != ref_w or ph != ref_h:
                                    norm_out = os.path.join(tmp_dir, f"norm_{pi:04d}.mp4")
                                    nr = subprocess.run(
                                        ["ffmpeg", "-y", "-i", p,
                                         "-vf", f"scale={ref_w}:{ref_h}:force_original_aspect_ratio=decrease,"
                                                f"pad={ref_w}:{ref_h}:(ow-iw)/2:(oh-ih)/2:color=black",
                                         "-c:v", "libx264", "-preset", "fast",
                                         "-c:a", "aac", "-b:a", "192k", norm_out],
                                        capture_output=True, timeout=300, **_no_window())
                                    if nr.returncode == 0:
                                        norm_processed[pi] = norm_out

                        # ── Sessiz segmentlere boş ses ekle ───────────────────
                        # acrossfade/xfade için tüm segmentlerin ses akışı olmalı
                        audio_ready = list(norm_processed)
                        for pi, p in enumerate(norm_processed):
                            probe = subprocess.run(
                                ["ffprobe", "-v", "error", "-select_streams", "a:0",
                                 "-show_entries", "stream=codec_name",
                                 "-of", "default=noprint_wrappers=1:nokey=1", p],
                                capture_output=True, timeout=10, **_no_window())
                            if not probe.stdout.strip():
                                # Ses akışı yok → sessiz ses ekle
                                sil_out = os.path.join(tmp_dir, f"sil_{pi:04d}.mp4")
                                sr = subprocess.run(
                                    ["ffmpeg", "-y", "-i", p,
                                     "-f", "lavfi", "-i", f"aevalsrc=0:c=stereo:s=44100:d={seg_durs[pi]:.3f}",
                                     "-map", "0:v", "-map", "1:a",
                                     "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                                     "-shortest", sil_out],
                                    capture_output=True, timeout=120, **_no_window())
                                if sr.returncode == 0:
                                    audio_ready[pi] = sil_out

                        # ── filter_complex zincirini doğru kur ────────────────
                        # Her adımda prev_lbl VE a_prev güncellenmeli (eski kodda güncellenmiyordu — asıl hata)
                        input_args = []
                        for p in audio_ready:
                            input_args += ["-i", p]

                        fc_parts    = []
                        audio_parts = []
                        prev_lbl    = "[0:v]"   # video zinciri önceki çıkışı
                        a_prev      = "[0:a]"   # ses zinciri önceki çıkışı
                        cumulative_dur = seg_durs[0]  # çıkış akışının toplam süresi

                        for i, (ca, cb) in enumerate(pairs):
                            t      = self.transitions.get((id(ca), id(cb)), TransitionData("cut", 0.5))
                            tdur   = t.duration if not t.is_cut else 0.02
                            tdur   = min(tdur, seg_durs[i] * 0.9, seg_durs[i+1] * 0.9)
                            tdur   = max(0.02, tdur)

                            # xfade offset = şimdiye kadar birikmiş çıkış süresi − geçiş süresi
                            offset = max(0.02, cumulative_dur - tdur)

                            is_last  = (i == len(pairs) - 1)
                            v_out    = "[vout]" if is_last else f"[xv{i}]"
                            a_out    = "[aout]" if is_last else f"[xa{i}]"
                            next_v   = f"[{i+1}:v]"
                            next_a   = f"[{i+1}:a]"

                            # Video xfade
                            fx_name = t.effect if not t.is_cut else "fade"
                            fc_parts.append(
                                f"{prev_lbl}{next_v}xfade=transition={fx_name}"
                                f":duration={tdur:.3f}:offset={offset:.3f}{v_out}"
                            )

                            # Ses acrossfade
                            audio_parts.append(
                                f"{a_prev}{next_a}acrossfade=d={tdur:.3f}:c1=tri:c2=tri{a_out}"
                            )

                            # ✅ Zinciri ilerlet (eski kodda bu iki satır eksikti)
                            prev_lbl       = v_out
                            a_prev         = a_out
                            cumulative_dur = offset + seg_durs[i+1]

                        filter_complex = ";".join(fc_parts + audio_parts)
                        final_vid = os.path.join(tmp_dir, "merged.mp4")
                        xfade_cmd = (
                            ["ffmpeg", "-y"] + input_args +
                            ["-filter_complex", filter_complex,
                             "-map", "[vout]", "-map", "[aout]",
                             "-c:v", "libx264", "-preset", "fast",
                             "-c:a", "aac", "-b:a", "192k",
                             "-movflags", "+faststart", final_vid]
                        )
                        rx = subprocess.run(xfade_cmd, capture_output=True, timeout=1200, **_no_window())
                        if rx.returncode != 0:
                            # Hata mesajını kaydet, concat fallback dene
                            xfade_err = rx.stderr.decode("utf-8", errors="replace")[-600:]
                            self.after(0, lambda: self.export_status.configure(
                                text="⚠️ xfade başarısız, concat ile deneniyor…", text_color=YELLOW))
                            lst = os.path.join(tmp_dir, "list.txt")
                            with open(lst, "w", encoding="utf-8") as ff:
                                for p in processed:
                                    ff.write(f"file '{p.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
                            rf = subprocess.run(
                                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                                 "-i", lst, "-c", "copy", final_vid],
                                capture_output=True, timeout=600, **_no_window()
                            )
                            if rf.returncode != 0:
                                err3 = rf.stderr.decode("utf-8", errors="replace")[-400:]
                                self.after(0, lambda e=err3: self.export_status.configure(
                                    text=f"✗ Birleştirme hatası:\n{e[:120]}", text_color=RED))
                                return

                # ── Bağımsız ses parçalarını karıştır ──────────────
                if self.audio_tracks and os.path.exists(final_vid):
                    audio_inputs = []
                    for at in self.audio_tracks:
                        audio_inputs += ["-i", at.path]
                    n = len(self.audio_tracks) + 1
                    delay_filters = []
                    for j, at in enumerate(self.audio_tracks):
                        delay_ms = int(at.start_time * 1000)
                        trim_part = ""
                        if at.trim_start > 0 or at.trim_end < at.duration:
                            trim_part = f"atrim={at.trim_start:.3f}:{at.trim_end:.3f},asetpts=PTS-STARTPTS,"
                        delay_filters.append(
                            f"[{j+1}:a]{trim_part}adelay={delay_ms}|{delay_ms}[a{j}]"
                        )
                    mix_inputs = "".join(f"[a{j}]" for j in range(len(self.audio_tracks)))
                    fc = ";".join(delay_filters) + f";[0:a]{mix_inputs}amix=inputs={n}:duration=first[aout]"
                    mix_out = out
                    mix_cmd = (
                        ["ffmpeg", "-y", "-i", final_vid] + audio_inputs +
                        ["-filter_complex", fc,
                         "-map", "0:v", "-map", "[aout]",
                         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                         "-movflags", "+faststart", mix_out]
                    )
                    r3 = subprocess.run(mix_cmd, capture_output=True, timeout=600, **_no_window())
                    if r3.returncode != 0:
                        # Fallback: ses katmanlarsız kaydet
                        shutil.copy(final_vid, out)
                elif os.path.exists(final_vid):
                    shutil.copy(final_vid, out)

                try: shutil.rmtree(tmp_dir)
                except: pass

                if os.path.exists(out):
                    self.after(0, lambda: self.export_status.configure(
                        text=f"✓ Tamamlandı: {os.path.basename(out)}", text_color=ACCENT))
                    self.after(0, lambda: messagebox.showinfo(
                        "✓  Dışa Aktarma Tamamlandı", f"Video başarıyla kaydedildi:\n{out}"))
                else:
                    self.after(0, lambda: self.export_status.configure(
                        text="✗ Çıktı dosyası oluşturulamadı", text_color=RED))
            except Exception as ex:
                self.after(0, lambda: self.export_status.configure(
                    text=f"✗ Export hatası:\n{ex}", text_color=RED))
        threading.Thread(target=_run, daemon=True).start()

# ──────────────────────────────────────────────────────────────
#  ANA UYGULAMA
# ──────────────────────────────────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AptozaQ2"); self.geometry("1280x740"); self.minsize(1050, 640); self.configure(fg_color=BG)
        # --- GÜVENLİ İKON YÜKLEME ---
        # Dosyanın tam yolunu oluşturuyoruz
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "AQ2.ico")

        if os.path.exists(icon_path):
            try:
                # Bazı Windows sürümlerinde wm_iconbitmap daha kararlı çalışır
                self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception as e:
                print(f"İkon yükleme hatası: {e}")
        else:
            print("Uyarı: AQ2.ico dosyası bulunamadı.")
        # ----------------------------
        self.engine = RecordingEngine(); self.overlay = DrawingOverlay(self.engine)
        self.engine.on_tick = self._tick; self.engine.on_done = self._on_done
        self._sched_t = None; self._pyn_listener = None; self._sched_active = False
        self._shortcut_defaults = {"start": "F9", "pause": "F10", "stop": "F11", "screenshot": "F8", "draw": "F7"}
        self._shortcuts = dict(self._shortcut_defaults)
        self._hotkey_labels = {}; self._tk_bound_keys = []
        self._webcam_preview = None  # Canlı webcam önizleme penceresi
        self.tool_window = FloatingToolWindow(self); self.tool_window.withdraw()
        self._build_ui(); self._refresh_timer(); self._register_hotkeys()

    def _build_ui(self):
        # ── Scrollable Sidebar with Vertical Scrollbar ──────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=CARD, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Canvas + Scrollbar for sidebar content
        self.sidebar_canvas = tk.Canvas(self.sidebar, bg=CARD, highlightthickness=0, bd=0)
        self.sidebar_scroll = tk.Scrollbar(self.sidebar, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scroll.set)

        # Configure canvas scrolling region
        def _configure_sidebar_scroll(event):
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        self.sidebar_canvas.bind("<Configure>", _configure_sidebar_scroll)

        # Place canvas and scrollbar
        self.sidebar_canvas.pack(side="left", fill="y", expand=True)
        self.sidebar_scroll.pack(side="right", fill="y")

        # Inner frame for sidebar content
        self.sidebar_inner = ctk.CTkFrame(self.sidebar_canvas, fg_color="transparent")
        self.sidebar_canvas.create_window((0, 0), window=self.sidebar_inner, anchor="nw")

        logo = ctk.CTkLabel(self.sidebar_inner, text="AptozaQ2", font=ctk.CTkFont("Arial", 24, "bold"), text_color=TXT); logo.pack(pady=(10, 4), padx=16)
        ctk.CTkLabel(self.sidebar_inner, text="V1.1.0", font=ctk.CTkFont("Arial", 11), text_color=TXT2).pack()
        ctk.CTkFrame(self.sidebar_inner, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=5)
        self._nav_btns = {}
        nav_items = [("🎬", "Kayıt", self._show_record), ("✏", "Düzenleme", self._show_edit), ("🎬", "Timeline", self._show_timeline), ("🎵", "Ses Editörü", self._show_audio), ("⚙️", "Ayarlar", self._show_settings), ("❓", "Yardım", self._show_help)]
        for icon, label, cmd in nav_items:
            btn = ctk.CTkButton(self.sidebar_inner, text=f"  {icon}  {label}", anchor="w", height=36, font=ctk.CTkFont("Arial", 14), fg_color="#1f538d", hover_color=CARD2, text_color=TXT2, command=cmd)
            btn.pack(fill="x", padx=8, pady=2); self._nav_btns[label] = btn
        ctk.CTkFrame(self.sidebar_inner, height=1, fg_color=BORDER).pack(fill="x", padx=5, pady=6)
        self.btn_show_tools = ctk.CTkButton(self.sidebar_inner, text="🛠️ Araç ve Zoom Paneli", height=30, fg_color=CARD2, hover_color="#FF0000", command=self.tool_window.show)
        self.btn_show_tools.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkFrame(self.sidebar_inner, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(self.sidebar_inner, text="📸 Ekran Görüntüsü", font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(pady=(4, 4))
        self.ss_fmt_var = ctk.StringVar(value="png")
        ctk.CTkOptionMenu(self.sidebar_inner, variable=self.ss_fmt_var, values=["png", "jpg", "bmp", "webp", "tiff"], width=100).pack(padx=5, pady=(0, 4))
        ctk.CTkButton(self.sidebar_inner, text="📷  Ekran Görüntüsü Al", height=34, fg_color=ACCENT2, hover_color=BORDER, font=ctk.CTkFont("Arial", 12, "bold"), command=self._take_screenshot).pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_status_side = ctk.CTkLabel(self.sidebar_inner, text="● Hazır", font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2); self.lbl_status_side.pack(pady=4)
        self.lbl_timer_side  = ctk.CTkLabel(self.sidebar_inner, text="00:00:00", font=ctk.CTkFont("Courier", 26, "bold"), text_color=TXT); self.lbl_timer_side.pack(pady=4)
        self.btn_start = ctk.CTkButton(self.sidebar_inner, text="⏺  Kayıt Başlat", height=36, fg_color="#1f538d", hover_color="#FF0000", font=ctk.CTkFont("Arial", 13, "bold"), command=self._start_recording)
        self.btn_start.pack(fill="x", padx=10, pady=(8, 3))
        self.btn_pause = ctk.CTkButton(self.sidebar_inner, text="⏸  Duraklat", height=36, fg_color="#1f538d", hover_color="#FF6F00", text_color="#000", font=ctk.CTkFont("Arial", 13, "bold"), state="disabled", command=self._pause_resume)
        self.btn_pause.pack(fill="x", padx=10, pady=3)
        self.btn_stop = ctk.CTkButton(self.sidebar_inner, text="⏹  Durdur", height=36, fg_color="#1f538d", hover_color="#CF35AE", font=ctk.CTkFont("Arial", 13, "bold"), state="disabled", command=self._stop_recording)
        self.btn_stop.pack(fill="x", padx=10, pady=3)
        # ── Kayıt sırasında canlı mikrofon mute butonu ──
        self.btn_mic_mute = ctk.CTkButton(
            self.sidebar_inner, text="🎙️  Mikrofon Açık", height=34,
            fg_color=CARD2, hover_color="#7f1d1d",
            font=ctk.CTkFont("Arial", 12, "bold"),
            state="disabled", command=self._toggle_mic_mute
        )
        self.btn_mic_mute.pack(fill="x", padx=10, pady=(0, 3))
        ctk.CTkFrame(self.sidebar_inner, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=5)
        self.draw_var = ctk.BooleanVar(value=False)
        self.btn_draw_toggle = ctk.CTkSwitch(self.sidebar_inner, text="Ekranda Çizim Modu", variable=self.draw_var, command=self._toggle_draw, font=ctk.CTkFont("Arial", 13, "bold"), text_color="#ffffff")
        self.btn_draw_toggle.pack(padx=16, pady=4)
        ctk.CTkFrame(self.sidebar_inner, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=(5, 4))
        ctk.CTkLabel(self.sidebar_inner, text="🎨 Tema", font=ctk.CTkFont("Arial", 12, "bold"), text_color=TXT2).pack(pady=(0, 2))
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.sidebar_inner, values=["Koyu", "Açık", "Sistem"], command=self._change_appearance_mode, width=150)
        self.appearance_mode_menu.pack(padx=16, pady=(0, 10))

        # Bind mousewheel for sidebar scrolling
        def _on_sidebar_mousewheel(event):
            self.sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel)
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0); self.content.pack(side="left", fill="both", expand=True)
        self._frames = {}
        self._frames["Kayıt"] = self._build_record_frame(); self._frames["Düzenleme"] = self._build_edit_frame()
        self._frames["Timeline"] = self._build_timeline_frame(); self._frames["Ses Editörü"] = self._build_audio_frame()
        self._frames["Ayarlar"] = self._build_settings_frame()
        self._frames["Yardım"] = self._build_help_frame(); self._show_record()

    def _nav_select(self, name):
        for n, b in self._nav_btns.items(): b.configure(fg_color=ACCENT2 if n == name else "transparent", text_color=TXT if n == name else TXT2)
        for n, f in self._frames.items():
            if n == name: f.pack(fill="both", expand=True)
            else: f.pack_forget()
    def _show_record(self): self._nav_select("Kayıt")
    def _show_edit(self): self._nav_select("Düzenleme")
    def _show_timeline(self): self._nav_select("Timeline")
    def _show_settings(self): self._nav_select("Ayarlar")
    def _show_help(self): self._nav_select("Yardım")
    def _show_audio(self): self._nav_select("Ses Editörü")
    def _build_timeline_frame(self): return VideoTimelineEditor(self.content)

    # ── Ses Editörü ana frame ──────────────────────────────────
    def _build_audio_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        hdr = ctk.CTkFrame(f, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(hdr, text="🎵  Ses Editörü",
                     font=ctk.CTkFont("Arial", 20, "bold"), text_color=TXT).pack(side="left")
        if not FFMPEG:
            ctk.CTkLabel(f, text="⚠️  Bu modül ffmpeg gerektirir. Lütfen ffmpeg'i yükleyin.",
                         text_color=YELLOW, font=ctk.CTkFont("Arial", 13)).pack(pady=20)
            return f

        tabs = ctk.CTkTabview(f, fg_color=CARD,
                              segmented_button_fg_color=CARD2,
                              segmented_button_selected_color=ACCENT2)
        tabs.pack(fill="both", expand=True, padx=20, pady=4)
        tabs.add("✂️  Kırp")
        tabs.add("🔀  Böl")
        tabs.add("🔄  Dönüştür")
        tabs.add("🔗  Birleştir")
        tabs.add("✨  Efektler")
        self._build_audio_trim_tab(tabs.tab("✂️  Kırp"))
        self._build_audio_split_tab(tabs.tab("🔀  Böl"))
        self._build_audio_convert_tab(tabs.tab("🔄  Dönüştür"))
        self._build_audio_merge_tab(tabs.tab("🔗  Birleştir"))
        
        # YENİ SES EFEKTLERİ MODÜLÜN BAĞLANDIĞI YER:
        self.audio_effects_tab = AudioEffectsTab(tabs.tab("✨  Efektler"))
        self.audio_effects_tab.pack(fill="both", expand=True)
        return f

    # ── Yardımcı: ses dosyası seçici ──────────────────────────
    def _pick_audio_file(self, entry):
        p = filedialog.askopenfilename(
            title="Ses Dosyası Seç",
            filetypes=[("Ses Dosyaları", "*.mp3 *.wav *.ogg *.aac *.flac *.m4a *.opus *.wma"),
                       ("Tümü", "*.*")])
        if p:
            entry.delete(0, "end")
            entry.insert(0, p)

    def _audio_read_dur(self, entry, lbl):
        p = entry.get()
        if not p or not os.path.exists(p):
            lbl.configure(text="⚠️ Dosya bulunamadı", text_color=YELLOW); return
        d = AudioEditor.get_duration(p)
        mm, ss = int(d // 60), int(d % 60)
        lbl.configure(text=f"⏱  Süre: {d:.2f} sn  ({mm:02d}:{ss:02d})",
                      text_color=TXT2)

    def _audio_done(self, ok, result, lbl):
        if ok:
            if isinstance(result, tuple):
                names = " + ".join(os.path.basename(r) for r in result)
                lbl.configure(text=f"✓  Tamamlandı: {names}", text_color=ACCENT)
            else:
                lbl.configure(text=f"✓  Tamamlandı: {os.path.basename(result)}",
                              text_color=ACCENT)
        else:
            lbl.configure(text=f"✗  Hata: {str(result)[:120]}", text_color=RED)

    # ── Kırp sekmesi ──────────────────────────────────────────
    def _build_audio_trim_tab(self, p):
        pad = dict(padx=16, pady=4)

        ctk.CTkLabel(p, text="Kaynak Ses Dosyası:",
                     font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", **pad)
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", **pad)
        self.atrim_src = ctk.CTkEntry(row, placeholder_text="Ses dosyası seçin...", width=500)
        self.atrim_src.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="📂", width=40,
                      command=lambda: self._pick_audio_file(self.atrim_src)).pack(side="left")

        self.atrim_dur_lbl = ctk.CTkLabel(p, text="", text_color=TXT2,
                                          font=ctk.CTkFont("Arial", 11))
        self.atrim_dur_lbl.pack(anchor="w", padx=16)
        ctk.CTkButton(p, text="⏱  Süreyi Oku", width=140, fg_color=CARD2,
                      command=lambda: self._audio_read_dur(self.atrim_src, self.atrim_dur_lbl)
                      ).pack(anchor="w", **pad)

        ctk.CTkFrame(p, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=6)

        tr = ctk.CTkFrame(p, fg_color="transparent"); tr.pack(fill="x", **pad)
        ctk.CTkLabel(tr, text="Başlangıç (sn):", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=130).pack(side="left")
        self.atrim_t0 = ctk.CTkEntry(tr, placeholder_text="0", width=100)
        self.atrim_t0.pack(side="left", padx=6)

        tr2 = ctk.CTkFrame(p, fg_color="transparent"); tr2.pack(fill="x", **pad)
        ctk.CTkLabel(tr2, text="Bitiş (sn):", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=130).pack(side="left")
        self.atrim_t1 = ctk.CTkEntry(tr2, placeholder_text="60", width=100)
        self.atrim_t1.pack(side="left", padx=6)

        self.atrim_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont("Arial", 12),
                                         text_color=TXT2)
        self.atrim_status.pack(anchor="w", padx=16, pady=4)

        ctk.CTkButton(p, text="✂️  Kırp ve Kaydet", height=40,
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._do_audio_trim).pack(anchor="w", **pad)

    def _do_audio_trim(self):
        if not FFMPEG:
            messagebox.showerror("Hata", "ffmpeg bulunamadı!"); return
        src = self.atrim_src.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir ses dosyası seçin."); return
        try:
            t0 = float(self.atrim_t0.get() or 0)
            t1 = float(self.atrim_t1.get() or 0)
        except ValueError:
            messagebox.showerror("Hata", "Başlangıç/bitiş değerleri sayısal olmalıdır."); return
        if t1 <= t0:
            messagebox.showerror("Hata", "Bitiş zamanı başlangıçtan büyük olmalıdır."); return
        ext = os.path.splitext(src)[1]
        out = filedialog.asksaveasfilename(
            title="Kırpılmış Dosyayı Kaydet",
            defaultextension=ext,
            filetypes=[(ext.upper().lstrip("."), f"*{ext}"),
                       ("Tüm Dosyalar", "*.*")])
        if not out: return
        self.atrim_status.configure(text="⏳ Kırpılıyor...", text_color=YELLOW)
        AudioEditor.trim(src, out, t0, t1,
                         lambda ok, r: self.after(0, lambda: self._audio_done(ok, r, self.atrim_status)))

    # ── Böl sekmesi ───────────────────────────────────────────
    def _build_audio_split_tab(self, p):
        pad = dict(padx=16, pady=4)

        ctk.CTkLabel(p, text="Kaynak Ses Dosyası:",
                     font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", **pad)
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", **pad)
        self.asplit_src = ctk.CTkEntry(row, placeholder_text="Ses dosyası seçin...", width=500)
        self.asplit_src.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="📂", width=40,
                      command=lambda: self._pick_audio_file(self.asplit_src)).pack(side="left")

        self.asplit_dur_lbl = ctk.CTkLabel(p, text="", text_color=TXT2,
                                           font=ctk.CTkFont("Arial", 11))
        self.asplit_dur_lbl.pack(anchor="w", padx=16)
        ctk.CTkButton(p, text="⏱  Süreyi Oku", width=140, fg_color=CARD2,
                      command=lambda: self._audio_read_dur(self.asplit_src, self.asplit_dur_lbl)
                      ).pack(anchor="w", **pad)

        ctk.CTkFrame(p, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=6)

        sp = ctk.CTkFrame(p, fg_color="transparent"); sp.pack(fill="x", **pad)
        ctk.CTkLabel(sp, text="Bölme Noktası (sn):", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=160).pack(side="left")
        self.asplit_time = ctk.CTkEntry(sp, placeholder_text="örn: 30", width=100)
        self.asplit_time.pack(side="left", padx=6)

        ctk.CTkLabel(p,
                     text="ℹ️  Dosya belirttiğiniz saniyede ikiye bölünür.\n"
                          "   Parça 1: 0 → N sn  |  Parça 2: N sn → son",
                     font=ctk.CTkFont("Arial", 11), text_color=TXT2, justify="left"
                     ).pack(anchor="w", padx=16, pady=2)

        self.asplit_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont("Arial", 12),
                                          text_color=TXT2)
        self.asplit_status.pack(anchor="w", padx=16, pady=4)

        ctk.CTkButton(p, text="🔀  Böl ve Kaydet", height=40,
                      fg_color=PURPLE, hover_color="#7c3aed",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._do_audio_split).pack(anchor="w", **pad)

    def _do_audio_split(self):
        if not FFMPEG:
            messagebox.showerror("Hata", "ffmpeg bulunamadı!"); return
        src = self.asplit_src.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir ses dosyası seçin."); return
        try:
            sp = float(self.asplit_time.get())
        except ValueError:
            messagebox.showerror("Hata", "Bölme noktası sayısal olmalıdır."); return
        if sp <= 0:
            messagebox.showerror("Hata", "Bölme noktası 0'dan büyük olmalıdır."); return
        ext  = os.path.splitext(src)[1]
        base = filedialog.asksaveasfilename(
            title="1. Parçanın Adını ve Yerini Seçin",
            defaultextension=ext,
            filetypes=[(ext.upper().lstrip("."), f"*{ext}"), ("Tüm Dosyalar", "*.*")])
        if not base: return
        stem, e = os.path.splitext(base)
        out1, out2 = base, stem + "_2" + e
        self.asplit_status.configure(text="⏳ Bölünüyor...", text_color=YELLOW)
        AudioEditor.split(src, out1, out2, sp,
                          lambda ok, r: self.after(0, lambda: self._audio_done(ok, r, self.asplit_status)))

    # ── Dönüştür sekmesi ──────────────────────────────────────
    def _build_audio_convert_tab(self, p):
        pad = dict(padx=16, pady=4)

        ctk.CTkLabel(p, text="Kaynak Ses Dosyası:",
                     font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", **pad)
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", **pad)
        self.aconv_src = ctk.CTkEntry(row, placeholder_text="Ses dosyası seçin...", width=500)
        self.aconv_src.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="📂", width=40,
                      command=lambda: self._pick_audio_file(self.aconv_src)).pack(side="left")

        ctk.CTkFrame(p, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=6)

        opt_row = ctk.CTkFrame(p, fg_color="transparent"); opt_row.pack(fill="x", **pad)
        ctk.CTkLabel(opt_row, text="Çıktı Formatı:", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=120).pack(side="left")
        self.aconv_fmt = ctk.StringVar(value="mp3")
        ctk.CTkOptionMenu(opt_row, variable=self.aconv_fmt,
                          values=AudioEditor.FORMATS, width=110).pack(side="left", padx=6)

        bit_row = ctk.CTkFrame(p, fg_color="transparent"); bit_row.pack(fill="x", **pad)
        ctk.CTkLabel(bit_row, text="Bit Hızı:", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=120).pack(side="left")
        self.aconv_br = ctk.StringVar(value="192k")
        ctk.CTkOptionMenu(bit_row, variable=self.aconv_br,
                          values=["64k", "96k", "128k", "160k", "192k", "256k", "320k"],
                          width=110).pack(side="left", padx=6)
        ctk.CTkLabel(bit_row,
                     text="(WAV / FLAC için geçersiz)", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 10)).pack(side="left", padx=6)

        self.aconv_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont("Arial", 12),
                                         text_color=TXT2)
        self.aconv_status.pack(anchor="w", padx=16, pady=4)

        ctk.CTkButton(p, text="🔄  Dönüştür ve Kaydet", height=40,
                      fg_color=ACCENT2, hover_color="#1a4472",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._do_audio_convert).pack(anchor="w", **pad)

    def _do_audio_convert(self):
        if not FFMPEG:
            messagebox.showerror("Hata", "ffmpeg bulunamadı!"); return
        src = self.aconv_src.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir ses dosyası seçin."); return
        fmt = self.aconv_fmt.get()
        br  = self.aconv_br.get()
        out = filedialog.asksaveasfilename(
            title="Dönüştürülmüş Dosyayı Kaydet",
            defaultextension=f".{fmt}",
            filetypes=[(fmt.upper(), f"*.{fmt}"), ("Tüm Dosyalar", "*.*")])
        if not out: return
        self.aconv_status.configure(text="⏳ Dönüştürülüyor...", text_color=YELLOW)
        AudioEditor.convert(src, out, fmt, br,
                            lambda ok, r: self.after(0, lambda: self._audio_done(ok, r, self.aconv_status)))

    # ── Birleştir sekmesi ─────────────────────────────────────
    def _build_audio_merge_tab(self, p):
        pad = dict(padx=16, pady=4)

        ctk.CTkLabel(p, text="Birleştirilecek Ses Dosyaları (sırayla ekleyin):",
                     font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", **pad)

        self.amerge_list = tk.Listbox(
            p, bg=CARD2, fg=TXT, selectbackground=ACCENT2,
            font=("Arial", 12), relief="flat", height=7,
            borderwidth=0, highlightthickness=1, highlightbackground=BORDER)
        self.amerge_list.pack(fill="x", padx=16, pady=4)

        btn_row = ctk.CTkFrame(p, fg_color="transparent"); btn_row.pack(fill="x", **pad)
        ctk.CTkButton(btn_row, text="➕  Dosya Ekle", width=130,
                      fg_color=ACCENT2, hover_color="#1a4472",
                      command=self._amerge_add).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="➖  Kaldır", width=100,
                      fg_color=RED, hover_color="#7f1d1d",
                      command=self._amerge_remove).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="⬆  Yukarı", width=90,
                      fg_color=CARD2, hover_color=BORDER,
                      command=self._amerge_up).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="⬇  Aşağı", width=90,
                      fg_color=CARD2, hover_color=BORDER,
                      command=self._amerge_down).pack(side="left")

        fmt_row = ctk.CTkFrame(p, fg_color="transparent"); fmt_row.pack(fill="x", **pad)
        ctk.CTkLabel(fmt_row, text="Çıktı Formatı:", text_color=TXT2,
                     font=ctk.CTkFont("Arial", 12), width=120).pack(side="left")
        self.amerge_fmt = ctk.StringVar(value="mp3")
        ctk.CTkOptionMenu(fmt_row, variable=self.amerge_fmt,
                          values=AudioEditor.FORMATS, width=110).pack(side="left", padx=6)

        self.amerge_status = ctk.CTkLabel(p, text="", font=ctk.CTkFont("Arial", 12),
                                          text_color=TXT2)
        self.amerge_status.pack(anchor="w", padx=16, pady=4)

        ctk.CTkButton(p, text="🔗  Birleştir ve Kaydet", height=40,
                      fg_color=ACCENT, hover_color="#1a6e2a",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._do_audio_merge).pack(anchor="w", **pad)

    def _amerge_add(self):
        p = filedialog.askopenfilename(
            title="Ses Dosyası Ekle",
            filetypes=[("Ses Dosyaları", "*.mp3 *.wav *.ogg *.aac *.flac *.m4a *.opus *.wma"),
                       ("Tümü", "*.*")])
        if p: self.amerge_list.insert("end", p)

    def _amerge_remove(self):
        sel = self.amerge_list.curselection()
        if sel: self.amerge_list.delete(sel[0])

    def _amerge_up(self):
        sel = self.amerge_list.curselection()
        if not sel or sel[0] == 0: return
        i = sel[0]; val = self.amerge_list.get(i)
        self.amerge_list.delete(i); self.amerge_list.insert(i - 1, val)
        self.amerge_list.selection_set(i - 1)

    def _amerge_down(self):
        sel = self.amerge_list.curselection()
        if not sel or sel[0] >= self.amerge_list.size() - 1: return
        i = sel[0]; val = self.amerge_list.get(i)
        self.amerge_list.delete(i); self.amerge_list.insert(i + 1, val)
        self.amerge_list.selection_set(i + 1)

    def _do_audio_merge(self):
        if not FFMPEG:
            messagebox.showerror("Hata", "ffmpeg bulunamadı!"); return
        paths = list(self.amerge_list.get(0, "end"))
        if len(paths) < 2:
            messagebox.showwarning("Uyarı", "En az 2 ses dosyası eklemeniz gerekiyor."); return
        fmt = self.amerge_fmt.get()
        out = filedialog.asksaveasfilename(
            title="Birleştirilmiş Dosyayı Kaydet",
            defaultextension=f".{fmt}",
            filetypes=[(fmt.upper(), f"*.{fmt}"), ("Tüm Dosyalar", "*.*")])
        if not out: return
        self.amerge_status.configure(text="⏳ Birleştiriliyor...", text_color=YELLOW)
        AudioEditor.merge(paths, out,
                          lambda ok, r: self.after(0, lambda: self._audio_done(ok, r, self.amerge_status)))
    def _change_appearance_mode(self, new_mode: str):
        if new_mode == "Koyu": ctk.set_appearance_mode("Dark")
        elif new_mode == "Açık": ctk.set_appearance_mode("Light")
        else: ctk.set_appearance_mode("System")

    def _build_record_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); hdr = ctk.CTkFrame(f, fg_color="transparent"); hdr.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(hdr, text="Kayıt Kaynakları", font=ctk.CTkFont("Arial", 20, "bold"), text_color=TXT).pack(side="left")
        row = ctk.CTkFrame(f, fg_color="transparent"); row.pack(fill="x", padx=20, pady=4)
        sc = self._card(row, "🖥️  Ekran Kaydı"); sc.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.sw_screen = ctk.CTkSwitch(sc, text="Etkin", font=ctk.CTkFont("Arial", 13)); self.sw_screen.select(); self.sw_screen.pack(anchor="w", padx=16, pady=6)
        ctk.CTkButton(sc, text="📐  Bölge Seç", height=32, fg_color=CARD2, hover_color=BORDER, command=self._select_region).pack(padx=16, pady=4, fill="x")
        self.lbl_region = ctk.CTkLabel(sc, text="Tam Ekran", font=ctk.CTkFont("Arial", 11), text_color=TXT2); self.lbl_region.pack(padx=16)
        ctk.CTkLabel(sc, text="FPS", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, pady=(10, 0), anchor="w")
        self.fps_var = ctk.StringVar(value="30"); fps_menu = ctk.CTkOptionMenu(sc, variable=self.fps_var, values=["10", "15", "24", "30", "60"], width=100); fps_menu.pack(padx=16, pady=4, anchor="w")
        ctk.CTkLabel(sc, text="Video Kalitesi", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, pady=(8, 0), anchor="w")
        self.quality_var = ctk.StringVar(value="Yüksek (CRF 18)")
        ctk.CTkOptionMenu(sc, variable=self.quality_var, values=["Çok Yüksek (CRF 16)", "Yüksek (CRF 18)", "Orta (CRF 23)", "Düşük (CRF 28)"], width=180).pack(padx=16, pady=4, anchor="w")
        wc = self._card(row, "📷  Webcam"); wc.pack(side="left", fill="both", expand=True, padx=6)
        self.sw_webcam = ctk.CTkSwitch(wc, text="Etkin", font=ctk.CTkFont("Arial", 13)); self.sw_webcam.pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(wc, text="PiP (Küçük ekran)", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.sw_pip = ctk.CTkSwitch(wc, text="Aktif", font=ctk.CTkFont("Arial", 12)); self.sw_pip.select(); self.sw_pip.pack(anchor="w", padx=16, pady=4)
        ctk.CTkLabel(wc, text="Kamera indeksi", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.cam_idx_var = ctk.StringVar(value="0"); ctk.CTkOptionMenu(wc, variable=self.cam_idx_var, values=["0", "1", "2"]).pack(padx=16, pady=4, anchor="w")
        ctk.CTkLabel(wc, text="PiP Boyutu", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.pip_size_var = ctk.StringVar(value="Orta (240×135)")
        ctk.CTkOptionMenu(wc, variable=self.pip_size_var,
                          values=["Küçük (160×90)", "Orta (240×135)", "Büyük (320×180)", "Tam (480×270)"],
                          width=180).pack(padx=16, pady=4, anchor="w")
        ctk.CTkLabel(wc, text="PiP Konumu", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.pip_pos_var = ctk.StringVar(value="bottom-right"); ctk.CTkOptionMenu(wc, variable=self.pip_pos_var, values=["bottom-right", "bottom-left", "top-right", "top-left"], width=160).pack(padx=16, pady=(2, 4), anchor="w")
        ctk.CTkLabel(wc, text="Kayıt sırasında önizleme", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.sw_cam_preview = ctk.CTkSwitch(wc, text="Göster", font=ctk.CTkFont("Arial", 12)); self.sw_cam_preview.select(); self.sw_cam_preview.pack(anchor="w", padx=16, pady=(4, 8))
        ac = self._card(row, "🎙️  Ses"); ac.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.sw_audio = ctk.CTkSwitch(ac, text="Etkin", font=ctk.CTkFont("Arial", 13))
        if AUDIO_OK: self.sw_audio.select()
        else: ctk.CTkLabel(ac, text="⚠ pyaudio yok", text_color=YELLOW, font=ctk.CTkFont("Arial", 11)).pack(padx=16)
        self.sw_audio.pack(anchor="w", padx=16, pady=6)
        ctk.CTkLabel(ac, text="Örnekleme hızı", font=ctk.CTkFont("Arial", 12), text_color=TXT2).pack(padx=16, anchor="w")
        self.rate_var = ctk.StringVar(value="44100"); ctk.CTkOptionMenu(ac, variable=self.rate_var, values=["22050", "44100", "48000"]).pack(padx=16, pady=4, anchor="w")
        outf = self._card(f, "📁  Çıktı Klasörü"); outf.pack(fill="x", padx=20, pady=8)
        row2 = ctk.CTkFrame(outf, fg_color="transparent"); row2.pack(fill="x", padx=16, pady=8)
        self.lbl_outdir = ctk.CTkLabel(row2, text=self.engine.output_dir, font=ctk.CTkFont("Arial", 12), text_color=TXT2, wraplength=600, anchor="w"); self.lbl_outdir.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row2, text="Değiştir", width=100, command=self._pick_outdir).pack(side="right")
        return f

    def _build_edit_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(f, text="Video Düzenleme", font=ctk.CTkFont("Arial", 20, "bold"), text_color=TXT).pack(anchor="w", padx=24, pady=(20, 12))
        tabs = ctk.CTkTabview(f, fg_color=CARD, segmented_button_fg_color=CARD2, segmented_button_selected_color=ACCENT2)
        tabs.pack(fill="both", expand=True, padx=20, pady=4)
        
        tabs.add("✏  Kırp"); self._build_trim_tab(tabs.tab("✏  Kırp"))
        tabs.add("🔗  Birleştir"); self._build_merge_tab(tabs.tab("🔗  Birleştir"))
        tabs.add("🔄  Dönüştür"); self._build_convert_tab(tabs.tab("🔄  Dönüştür"))
        
        # 👇 YENİ EKLENEN KISIM
        tabs.add("🖼️ Görsel→Video")
        img2vid_tab = tabs.tab("🖼️ Görsel→Video")
        self.img2vid_editor = ImageToVideoEditor(img2vid_tab)
        self.img2vid_editor.pack(fill="both", expand=True)
        # 👆 YENİ EKLENEN KISIM SONU
        
        return f

    def _build_trim_tab(self, p):
        ctk.CTkLabel(p, text="Kaynak Video:", font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", padx=8, pady=(12, 2))
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        self.trim_src = ctk.CTkEntry(row, placeholder_text="Video dosyası seçin...", width=500); self.trim_src.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="📂", width=40, command=lambda: self._pick_video(self.trim_src)).pack(side="left")
        tr = ctk.CTkFrame(p, fg_color="transparent"); tr.pack(fill="x", padx=8, pady=10)
        ctk.CTkLabel(tr, text="Başlangıç (sn):", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.trim_t0 = ctk.CTkEntry(tr, placeholder_text="0", width=90); self.trim_t0.pack(side="left", padx=6)
        ctk.CTkLabel(tr, text="Bitiş (sn):", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.trim_t1 = ctk.CTkEntry(tr, placeholder_text="60", width=90); self.trim_t1.pack(side="left", padx=6)
        self.lbl_trim_dur = ctk.CTkLabel(p, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 11)); self.lbl_trim_dur.pack(anchor="w", padx=8)
        ctk.CTkButton(p, text="⏱  Süreyi Oku", width=140, fg_color=CARD2, command=self._read_duration).pack(anchor="w", padx=8, pady=4)
        self.trim_status = ctk.CTkLabel(p, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 12)); self.trim_status.pack(anchor="w", padx=8)
        ctk.CTkButton(p, text="✏  Kırp", height=40, fg_color=ACCENT, hover_color=ACCENT2, command=self._do_trim).pack(anchor="w", padx=8, pady=10)

    def _build_merge_tab(self, p):
        ctk.CTkLabel(p, text="Birleştirilecek Videolar (sırayla ekleyin):", font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", padx=8, pady=(12, 4))
        self.merge_list = tk.Listbox(p, bg=CARD2, fg=TXT, selectbackground=ACCENT2, font=("Arial", 12), relief="flat", height=7, borderwidth=0, highlightthickness=0); self.merge_list.pack(fill="x", padx=8, pady=4)
        r = ctk.CTkFrame(p, fg_color="transparent"); r.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(r, text="➕ Ekle", width=100, fg_color=ACCENT2, command=self._merge_add).pack(side="left", padx=(0, 6))
        ctk.CTkButton(r, text="➖ Kaldır", width=100, fg_color=RED, command=self._merge_remove).pack(side="left")
        self.merge_status = ctk.CTkLabel(p, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 12)); self.merge_status.pack(anchor="w", padx=8, pady=4)
        ctk.CTkButton(p, text="🔗  Birleştir", height=40, fg_color=ACCENT, hover_color=ACCENT2, command=self._do_merge).pack(anchor="w", padx=8, pady=6)

    def _build_convert_tab(self, p):
        ctk.CTkLabel(p, text="Kaynak Video:", font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", padx=8, pady=(12, 2))
        row = ctk.CTkFrame(p, fg_color="transparent"); row.pack(fill="x", padx=8, pady=2)
        self.conv_src = ctk.CTkEntry(row, placeholder_text="Video dosyası...", width=500); self.conv_src.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="📂", width=40, command=lambda: self._pick_video(self.conv_src)).pack(side="left")
        ctk.CTkLabel(p, text="Hedef Format:", font=ctk.CTkFont("Arial", 13), text_color=TXT2).pack(anchor="w", padx=8, pady=(10, 2))
        self.conv_fmt = ctk.StringVar(value="mp4"); frow = ctk.CTkFrame(p, fg_color="transparent"); frow.pack(fill="x", padx=8, pady=4)
        for fmt in ["mp4", "avi", "mkv", "mov", "gif", "webm", "mp3", "wav"]: ctk.CTkRadioButton(frow, text=fmt.upper(), variable=self.conv_fmt, value=fmt, font=ctk.CTkFont("Arial", 13)).pack(side="left", padx=8)
        self.conv_status = ctk.CTkLabel(p, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 12)); self.conv_status.pack(anchor="w", padx=8, pady=6)
        ctk.CTkButton(p, text="🔄  Dönüştür", height=40, fg_color=ACCENT, hover_color=ACCENT2, command=self._do_convert).pack(anchor="w", padx=8, pady=6)

    def _build_settings_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); ctk.CTkLabel(f, text="Ayarlar", font=ctk.CTkFont("Arial", 20, "bold"), text_color=TXT).pack(anchor="w", padx=24, pady=(20, 12))
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20)
        cc = self._card(scroll, "🖱️  İmleç Vurgusu"); cc.pack(fill="x", pady=6)
        self.sw_cursor = ctk.CTkSwitch(cc, text="İmleci vurgula", font=ctk.CTkFont("Arial", 13)); self.sw_cursor.pack(anchor="w", padx=16, pady=8)
        r = ctk.CTkFrame(cc, fg_color="transparent"); r.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(r, text="Renk:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.cursor_col_prev = ctk.CTkFrame(r, width=28, height=28, fg_color="#ff3333", corner_radius=4); self.cursor_col_prev.pack(side="left", padx=6)
        ctk.CTkButton(r, text="Seç", width=60, fg_color=CARD2, hover_color=BORDER, command=self._pick_cursor_color).pack(side="left")
        ctk.CTkLabel(r, text="  Boyut:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left", padx=(10, 0))
        self.cursor_sz_var = ctk.IntVar(value=22); ctk.CTkSlider(r, variable=self.cursor_sz_var, from_=10, to=50, width=120).pack(side="left", padx=6)
        wc = self._card(scroll, "💧  Filigran (Watermark)"); wc.pack(fill="x", pady=6)
        self.sw_wm = ctk.CTkSwitch(wc, text="Filigran etkin", font=ctk.CTkFont("Arial", 13)); self.sw_wm.pack(anchor="w", padx=16, pady=8)
        r2 = ctk.CTkFrame(wc, fg_color="transparent"); r2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(r2, text="Metin:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.wm_text_entry = ctk.CTkEntry(r2, placeholder_text="EkranKayıt Pro", width=260); self.wm_text_entry.pack(side="left", padx=6)
        r3 = ctk.CTkFrame(wc, fg_color="transparent"); r3.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(r3, text="Görsel:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.lbl_wm_img = ctk.CTkLabel(r3, text="Seçilmedi", text_color=TXT2, font=ctk.CTkFont("Arial", 11)); self.lbl_wm_img.pack(side="left", padx=6)
        ctk.CTkButton(r3, text="📂 Görsel Seç", width=120, fg_color=CARD2, command=self._pick_wm_image).pack(side="left", padx=4)
        ctk.CTkButton(r3, text="✗ Temizle", width=90, fg_color=RED, command=self._clear_wm_image).pack(side="left", padx=4)
        r4 = ctk.CTkFrame(wc, fg_color="transparent"); r4.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(r4, text="Konum:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.wm_pos_var = ctk.StringVar(value="bottom-right"); ctk.CTkOptionMenu(r4, variable=self.wm_pos_var, values=["top-left", "top-right", "bottom-left", "bottom-right", "center"], width=150).pack(side="left", padx=6)
        ctk.CTkLabel(r4, text="Saydamlık:", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left", padx=(12, 0))
        self.wm_opacity_var = ctk.DoubleVar(value=0.6); ctk.CTkSlider(r4, variable=self.wm_opacity_var, from_=0.1, to=1.0, width=120).pack(side="left", padx=6)
        sc2 = self._card(scroll, "⏰  Zamanlı Kayıt"); sc2.pack(fill="x", pady=6)
        self.sw_sched = ctk.CTkSwitch(sc2, text="Zamanlayıcı etkin", font=ctk.CTkFont("Arial", 13)); self.sw_sched.pack(anchor="w", padx=16, pady=8)
        r5 = ctk.CTkFrame(sc2, fg_color="transparent"); r5.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(r5, text="Başlangıç (SS:DD):", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left")
        self.sched_start = ctk.CTkEntry(r5, placeholder_text="14:30", width=80); self.sched_start.pack(side="left", padx=6)
        ctk.CTkLabel(r5, text="Bitiş (SS:DD):", text_color=TXT2, font=ctk.CTkFont("Arial", 12)).pack(side="left", padx=(12, 0))
        self.sched_end = ctk.CTkEntry(r5, placeholder_text="15:00", width=80); self.sched_end.pack(side="left", padx=6)
        self.lbl_sched_status = ctk.CTkLabel(sc2, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 12)); self.lbl_sched_status.pack(anchor="w", padx=16, pady=4)
        ctk.CTkButton(sc2, text="⏰  Zamanlayıcıyı Ayarla", height=38, fg_color=PURPLE, hover_color="#7c3aed", command=self._set_scheduler).pack(anchor="w", padx=16, pady=8)
        kc = self._card(scroll, "⌨️  Kısayol Tuşları"); kc.pack(fill="x", pady=6)
        if not HOTKEY_OK: ctk.CTkLabel(kc, text="⚠  Global kısayollar için:  pip install keyboard", text_color=YELLOW, font=ctk.CTkFont("Arial", 11)).pack(anchor="w", padx=16, pady=(6, 2)); ctk.CTkLabel(kc, text="(Şu an yalnızca uygulama odakta iken çalışır)", text_color=TXT2, font=ctk.CTkFont("Arial", 11)).pack(anchor="w", padx=16, pady=(0, 6))
        _action_names = {"start": ("⏺", "Kayıt Başlat"), "pause": ("⏸", "Duraklat / Devam"), "stop": ("⏹", "Durdur"), "screenshot": ("📸", "Ekran Görüntüsü"), "draw": ("✏", "Çizim Modu Aç/Kapat")}
        for action, (icon, name) in _action_names.items():
            row_k = ctk.CTkFrame(kc, fg_color=CARD2, corner_radius=8); row_k.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row_k, text=f"{icon}  {name}", width=200, anchor="w", font=ctk.CTkFont("Arial", 13), text_color=TXT).pack(side="left", padx=12, pady=8)
            key_lbl = ctk.CTkLabel(row_k, text=self._shortcuts.get(action, "—"), width=90, anchor="center", font=ctk.CTkFont("Courier", 13, "bold"), fg_color=CARD, corner_radius=6, text_color=ACCENT2); key_lbl.pack(side="left", padx=6, pady=6)
            self._hotkey_labels[action] = key_lbl
            ctk.CTkButton(row_k, text="Değiştir", width=80, fg_color=ACCENT2, hover_color=BORDER, font=ctk.CTkFont("Arial", 12), command=lambda a=action, l=key_lbl: self._show_key_capture(a, l)).pack(side="left", padx=4)
            ctk.CTkButton(row_k, text="Sıfırla", width=70, fg_color=CARD, hover_color=BORDER, font=ctk.CTkFont("Arial", 12), command=lambda a=action, l=key_lbl: self._reset_hotkey(a, l)).pack(side="left", padx=(0, 8))
        gc = self._card(scroll, "⚙️  Genel"); gc.pack(fill="x", pady=6)
        ctk.CTkButton(gc, text="💾  Ayarları Kaydet", height=36, fg_color=ACCENT, command=self._save_settings).pack(anchor="w", padx=16, pady=10)
        return f

    def _build_help_frame(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); ctk.CTkLabel(f, text="Yardım ve Hakkında", font=ctk.CTkFont("Arial", 20, "bold"), text_color=TXT).pack(anchor="w", padx=24, pady=(20, 12))
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20)
        hc = self._card(scroll, "📌  Temel İşlevler Kılavuzu"); hc.pack(fill="x", pady=6)
        info_text = ("🎥 Ekran Kaydı: Ekranınızı, belirli bir pencereyi/bölgeyi, web kamerasını ve bilgisayar/mikrofon sesini eşzamanlı olarak kaydedebilirsiniz.\n"
                     "🖌️ Canlı Çizim: 'Araç ve Zoom Paneli' veya kısayol tuşu ile kayıt sırasında ekran üzerinde serbest çizim yapabilir, renkli şekiller ve özel metinler ekleyerek önemli yerleri vurgulayabilirsiniz.\n"
                     "🔍 Yakınlaştırma (Zoom): Kayıt esnasında belirlediğiniz bir oranda imleç odaklı canlı yakınlaştırma yapabilirsiniz.\n"
                     "✂️ Video Düzenleme: Hazır videoları kırpabilir, birden fazla videoyu sırayla birleştirebilir veya GIF, MP3 gibi farklı dosya formatlarına dönüştürebilirsiniz.\n"
                     "⏰ Zamanlayıcı: Ayarlar sekmesinden belirlenen başlangıç ve bitiş saatlerine göre uygulamanın otomatik kayıt yapmasını sağlayabilirsiniz.")
        ctk.CTkLabel(hc, text=info_text, font=ctk.CTkFont("Arial", 14), text_color=TXT, justify="left", wraplength=700).pack(anchor="w", padx=16, pady=10)
        ac = self._card(scroll, "👤  Geliştirici ve Bağlantılar"); ac.pack(fill="x", pady=6)
        ctk.CTkLabel(ac, text="Geliştirici: Emrullah ALKAÇ", font=ctk.CTkFont("Arial", 15, "bold"), text_color=ACCENT).pack(anchor="w", padx=16, pady=(10,2))
        ctk.CTkLabel(ac, text="YouTube: https://www.youtube.com/@yaz%C4%B1l%C4%B1mhocas%C4%B1-p9c", font=ctk.CTkFont("Arial", 14), text_color=TXT2).pack(anchor="w", padx=16, pady=(2,10))
        return f

    def _card(self, parent, title=""):
        c = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        if title: ctk.CTkLabel(c, text=title, font=ctk.CTkFont("Arial", 14, "bold"), text_color=TXT).pack(anchor="w", padx=16, pady=(12, 4))
        return c

    def _apply_engine_settings(self):
        self.engine.screen_on = self.sw_screen.get(); self.engine.webcam_on = self.sw_webcam.get(); self.engine.audio_on = self.sw_audio.get() and AUDIO_OK
        self.engine.audio_rate = int(self.rate_var.get()); self.engine.fps = int(self.fps_var.get()); self.engine.pip_enabled = self.sw_pip.get()
        self.engine.cam_idx = int(self.cam_idx_var.get()); self.engine.pip_pos = self.pip_pos_var.get(); self.engine.cursor_hl = self.sw_cursor.get()
        self.engine.cursor_sz = self.cursor_sz_var.get(); self.engine.wm_enabled = self.sw_wm.get(); self.engine.wm_text = self.wm_text_entry.get()
        self.engine.wm_pos = self.wm_pos_var.get(); self.engine.wm_opacity = self.wm_opacity_var.get()
        _crf_map = {"Çok Yüksek (CRF 16)": 16, "Yüksek (CRF 18)": 18, "Orta (CRF 23)": 23, "Düşük (CRF 28)": 28}
        self.engine.quality = _crf_map.get(self.quality_var.get(), 18)
        _pip_size_map = {
            "Küçük (160×90)":   (160,  90),
            "Orta (240×135)":   (240, 135),
            "Büyük (320×180)":  (320, 180),
            "Tam (480×270)":    (480, 270),
        }
        self.engine.pip_pixel_size = _pip_size_map.get(self.pip_size_var.get(), (240, 135))

    def _start_recording(self):
        self._apply_engine_settings()
        self.engine.audio_muted = False   # her yeni kayıtta sıfırla
        self.engine.start()
        self.btn_start.configure(state="disabled"); self.btn_pause.configure(state="normal"); self.btn_stop.configure(state="normal")
        # Mikrofon butonu: ses aktifse etkinleştir
        if self.engine.audio_on and AUDIO_OK:
            self.btn_mic_mute.configure(state="normal", text="🎙️  Mikrofon Açık", fg_color=CARD2)
        self.lbl_status_side.configure(text="● Kayıt Yapılıyor", text_color=RED)
        if self.draw_var.get(): self.overlay.show(); self.tool_window.show()
        # Webcam önizleme penceresini aç
        if self.engine.webcam_on and self.sw_cam_preview.get():
            if self._webcam_preview is None or not self._webcam_preview.winfo_exists():
                self._webcam_preview = WebcamPreviewWindow(self, self.engine)
        self._keep_windows_on_top()

    def _keep_windows_on_top(self):
        if self.engine.recording and self.draw_var.get():
            try:
                self.overlay.win.lift()
                self.overlay.event_win.lift()
                self.tool_window.lift()
                self.overlay.win.attributes("-topmost", True)
                self.overlay.event_win.attributes("-topmost", True)
                self.tool_window.attributes("-topmost", True)
            except Exception: pass
        if self.engine.recording:
            self.after(500, self._keep_windows_on_top)

    def _pause_resume(self):
        if self.engine.paused:
            self.engine.resume(); self.btn_pause.configure(text="⏸  Duraklat"); self.lbl_status_side.configure(text="● Kayıt Yapılıyor", text_color=RED)
        else:
            self.engine.pause(); self.btn_pause.configure(text="▶  Devam Et"); self.lbl_status_side.configure(text="⏸ Duraklatıldı", text_color=YELLOW)

    def _stop_recording(self):
        self.overlay.hide(); self.draw_var.set(False); self.lbl_status_side.configure(text="⏳ Kaydediliyor...", text_color=YELLOW)
        # Webcam önizleme penceresini kapat
        if self._webcam_preview is not None:
            try:
                if self._webcam_preview.winfo_exists():
                    self._webcam_preview._on_close()
            except Exception: pass
            self._webcam_preview = None
        threading.Thread(target=self.engine.stop, daemon=True).start()
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸  Duraklat")
        self.btn_stop.configure(state="disabled")
        self.btn_mic_mute.configure(state="disabled", text="🎙️  Mikrofon Açık", fg_color=CARD2)
        self.engine.audio_muted = False

    def _toggle_mic_mute(self):
        """Kayıt sırasında mikrofonu anlık olarak susturur / açar."""
        self.engine.audio_muted = not self.engine.audio_muted
        if self.engine.audio_muted:
            self.btn_mic_mute.configure(
                text="🔇  Mikrofon Kapalı",
                fg_color=RED,
                hover_color="#7f1d1d"
            )
        else:
            self.btn_mic_mute.configure(
                text="🎙️  Mikrofon Açık",
                fg_color=ACCENT,
                hover_color="#1a6e2a"
            )

    def _on_done(self, path):
        self.after(0, lambda: self.lbl_status_side.configure(text="✓ Tamamlandı", text_color=ACCENT))
        self.after(0, lambda: messagebox.showinfo("Kayıt Tamamlandı", f"Video kaydedildi:\n{path}"))

    def _toggle_draw(self):
        if self.draw_var.get():
            self.tool_window.show()
            if self.engine.recording: self.overlay.show()
            self.after(200, lambda: self.tool_window.lift()); self.after(200, lambda: self.tool_window.attributes("-topmost", True))
        else: self.overlay.hide(); self.tool_window.hide()

    def _take_screenshot(self):
        fmt = self.ss_fmt_var.get().lower(); ts = datetime.now().strftime("%Y%m%d_%H%M%S"); default_name = f"screenshot_{ts}.{fmt}"
        filetypes = [("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("BMP", "*.bmp"), ("WebP", "*.webp"), ("TIFF", "*.tiff")]
        path = filedialog.asksaveasfilename(initialdir=self.engine.output_dir, initialfile=default_name, defaultextension=f".{fmt}", filetypes=filetypes)
        if not path: return
        try:
            with mss_lib.mss() as sct:
                mon = self.engine._get_mon(); raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                save_kw = {}
                if fmt in ("jpg", "jpeg"): save_kw["quality"] = 95
                elif fmt == "webp": save_kw["quality"] = 90
                img.save(path, **save_kw)
                messagebox.showinfo("Ekran Görüntüsü", f"Kaydedildi:\n{path}")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def _register_hotkeys(self):
        if getattr(self, '_pyn_listener', None):
            try: self._pyn_listener.stop()
            except: pass
        self._pyn_listener = None
        if HOTKEY_OK:
            try:
                _actions = {"start": self._start_recording, "pause": self._pause_resume, "stop": self._stop_recording, "screenshot": self._take_screenshot, "draw": self._hotkey_draw_toggle}
                hk_map = {}
                for action, key in self._shortcuts.items():
                    if key and key != "—":
                        fmt = key.lower().replace('+', '>+<')
                        if not fmt.startswith('<'): fmt = '<' + fmt
                        if not fmt.endswith('>'): fmt = fmt + '>'
                        cb = _actions[action]; hk_map[fmt] = (lambda c=cb: self.after(0, c))
                self._pyn_listener = _pyn_kb.GlobalHotKeys(hk_map); self._pyn_listener.start(); return
            except Exception as e: print(f"[Kısayol] pynput kayıt hatası: {e}"); globals()['HOTKEY_OK'] = False
        for k in self._tk_bound_keys:
            try: self.unbind_all(f"<{k}>")
            except: pass
        self._tk_bound_keys = []
        _actions = {"start": self._start_recording, "pause": self._pause_resume, "stop": self._stop_recording, "screenshot": self._take_screenshot, "draw": self._hotkey_draw_toggle}
        for action, key in self._shortcuts.items():
            if key and key != "—":
                cb = _actions[action]
                try: self.bind_all(f"<{key}>", lambda e, c=cb: c()); self._tk_bound_keys.append(key)
                except Exception as ex: print(f"[Kısayol] tkinter bind hatası ({key}): {ex}")

    def _hotkey_draw_toggle(self): self.draw_var.set(not self.draw_var.get()); self._toggle_draw()
    def _reset_hotkey(self, action, lbl): default = self._shortcut_defaults.get(action, "—"); self._shortcuts[action] = default; lbl.configure(text=default); self._register_hotkeys()

    def _show_key_capture(self, action, lbl):
        _action_names = {"start": "Kayıt Başlat", "pause": "Duraklat / Devam", "stop": "Durdur", "screenshot": "Ekran Görüntüsü", "draw": "Çizim Modu"}
        dlg = ctk.CTkToplevel(self); dlg.title("Kısayol Ata"); dlg.geometry("340x185"); dlg.resizable(False, False); dlg.attributes("-topmost", True); dlg.grab_set()
        ctk.CTkLabel(dlg, text=f"« {_action_names[action]} »\niçin bir tuşa basın:", font=ctk.CTkFont("Arial", 14), text_color=TXT, justify="center").pack(pady=(20, 8))
        captured_lbl = ctk.CTkLabel(dlg, text="...", font=ctk.CTkFont("Courier", 18, "bold"), text_color=ACCENT2, fg_color=CARD2, corner_radius=8, width=200, height=36); captured_lbl.pack(pady=4)
        pressed = {"key": None}
        def on_key(e):
            parts = []
            if e.state & 0x4: parts.append("ctrl")
            if e.state & 0x1: parts.append("shift")
            if e.state & 0x8: parts.append("alt")
            sym = e.keysym
            if sym in ("Control_L","Control_R","Shift_L","Shift_R","Alt_L","Alt_R","Super_L","Super_R","Caps_Lock"): return
            parts.append(sym if len(sym) > 1 else sym.lower()); key_str = "+".join(parts); pressed["key"] = key_str; captured_lbl.configure(text=key_str)
        dlg.bind("<Key>", on_key); dlg.focus_set()
        def apply():
            if pressed["key"]: self._shortcuts[action] = pressed["key"]; lbl.configure(text=pressed["key"]); self._register_hotkeys()
            dlg.destroy()
        def clear_key(): self._shortcuts[action] = "—"; lbl.configure(text="—"); self._register_hotkeys(); dlg.destroy()
        btn_row = ctk.CTkFrame(dlg, fg_color="transparent"); btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="✓  Uygula", width=110, fg_color=ACCENT, hover_color="#1a6e2a", command=apply).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="✗  Temizle", width=110, fg_color=RED, hover_color="#7f1d1d", command=clear_key).pack(side="left", padx=6)

    def _tick(self, _): pass
    def _refresh_timer(self):
        if self.engine.recording:
            s = self.engine.elapsed_str(); self.lbl_timer_side.configure(text=s)
            if self.engine.zoom_factor > 1.0 and CURSOR_OK:
                try:
                    x, y = pyautogui.position(); r = self.engine.region
                    if r: x -= r[0]; y -= r[1]
                    self.engine.zoom_center = (x, y)
                except: pass
        self.after(250, self._refresh_timer)

    def _select_region(self): self.withdraw(); self.after(200, lambda: RegionSelector(self._on_region).select())
    def _on_region(self, r):
        self.deiconify(); self.engine.region = r
        if r: self.lbl_region.configure(text=f"{r[0]},{r[1]}  {r[2]}×{r[3]} px")
        else: self.lbl_region.configure(text="Tam Ekran")

    def _pick_outdir(self):
        d = filedialog.askdirectory(initialdir=self.engine.output_dir)
        if d: self.engine.output_dir = d; self.lbl_outdir.configure(text=d)
    def _pick_cursor_color(self):
        c = colorchooser.askcolor(color=self.engine.cursor_col, title="İmleç Rengi")
        if c and c[1]: self.engine.cursor_col = c[1]; self.cursor_col_prev.configure(fg_color=c[1])
    def _pick_wm_image(self):
        p = filedialog.askopenfilename(filetypes=[("Görseller", "*.png *.jpg *.jpeg *.bmp")])
        if p:
            try: img = Image.open(p).resize((150, 60), Image.LANCZOS); self.engine.wm_image = img; self.lbl_wm_img.configure(text=os.path.basename(p))
            except Exception as e: messagebox.showerror("Hata", str(e))
    def _clear_wm_image(self): self.engine.wm_image = None; self.lbl_wm_img.configure(text="Seçilmedi")
    def _pick_video(self, entry):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mkv *.mov *.webm")])
        if p: entry.delete(0, "end"); entry.insert(0, p)
    def _read_duration(self):
        p = self.trim_src.get()
        if not p: return
        d = VideoEditor.get_duration(p); self.lbl_trim_dur.configure(text=f"Süre: {d:.1f} saniye ({int(d//60):02d}:{int(d%60):02d})")
    def _do_trim(self):
        if not FFMPEG: messagebox.showerror("Hata", "ffmpeg gerekli!"); return
        src = self.trim_src.get()
        if not src or not os.path.exists(src): return
        try: t0, t1 = float(self.trim_t0.get() or 0), float(self.trim_t1.get() or 0)
        except: return
        ext = os.path.splitext(src)[1]; out = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(ext.upper(), f"*{ext}")])
        if not out: return
        self.trim_status.configure(text="⏳ Kırpılıyor...")
        VideoEditor.trim(src, out, t0, t1, lambda ok, p: self.after(0, lambda: self._edit_done(ok, p, self.trim_status)))
    def _merge_add(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mkv *.mov")])
        if p: self.merge_list.insert("end", p)
    def _merge_remove(self):
        sel = self.merge_list.curselection()
        if sel: self.merge_list.delete(sel[0])
    def _do_merge(self):
        if not FFMPEG: return
        paths = list(self.merge_list.get(0, "end"))
        if len(paths) < 2: return
        out = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not out: return
        self.merge_status.configure(text="⏳ Birleştiriliyor...")
        VideoEditor.merge(paths, out, lambda ok, p: self.after(0, lambda: self._edit_done(ok, p, self.merge_status)))
    def _do_convert(self):
        if not FFMPEG: return
        src = self.conv_src.get()
        if not src or not os.path.exists(src): return
        fmt = self.conv_fmt.get(); out = filedialog.asksaveasfilename(defaultextension=f".{fmt}", filetypes=[(fmt.upper(), f"*.{fmt}")])
        if not out: return
        self.conv_status.configure(text="⏳ Dönüştürülüyor...")
        VideoEditor.convert(src, out, fmt, lambda ok, p: self.after(0, lambda: self._edit_done(ok, p, self.conv_status)))
    def _edit_done(self, ok, path, lbl):
        if ok: lbl.configure(text=f"✓ Tamamlandı: {os.path.basename(path)}", text_color=ACCENT)
        else: lbl.configure(text=f"✗ Hata: {path}", text_color=RED)
    def _set_scheduler(self):
        if not self.sw_sched.get(): return
        try: sh, sm = map(int, self.sched_start.get().split(":")); eh, em = map(int, self.sched_end.get().split(":"))
        except: return
        from datetime import timedelta as _td
        now = datetime.now(); start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0); end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
        if start_dt < now: start_dt += _td(days=1)
        if end_dt < start_dt: end_dt += _td(days=1)
        self._sched_active = True; self.lbl_sched_status.configure(text=f"⏰ Bekleniyor... Başlangıç: {start_dt.strftime('%H:%M')}  |  Bitiş: {end_dt.strftime('%H:%M')}", text_color=YELLOW)
        def _watch():
            while self._sched_active:
                n = datetime.now()
                if n >= start_dt and not self.engine.recording: self.after(0, self._start_recording)
                if n >= end_dt and self.engine.recording: self.after(0, self._stop_recording); self._sched_active = False; break
                time.sleep(5)
        self._sched_t = threading.Thread(target=_watch, daemon=True); self._sched_t.start()
    def _save_settings(self):
        cfg_path = Path.home() / ".ekran_kayit_pro.json"
        cfg = {"output_dir": self.engine.output_dir, "fps": self.fps_var.get(), "quality": self.quality_var.get(), "cursor_hl": self.sw_cursor.get(), "cursor_sz": self.cursor_sz_var.get(), "wm_text": self.wm_text_entry.get(), "wm_pos": self.wm_pos_var.get(), "wm_opacity": self.wm_opacity_var.get(), "shortcuts": self._shortcuts}
        with open(cfg_path, "w") as f: json.dump(cfg, f, indent=2)
    def _load_settings(self):
        cfg_path = Path.home() / ".ekran_kayit_pro.json"
        if not cfg_path.exists(): return
        try:
            with open(cfg_path) as f: cfg = json.load(f)
            if "output_dir" in cfg: self.engine.output_dir = cfg["output_dir"]; self.lbl_outdir.configure(text=cfg["output_dir"])
            if "fps" in cfg: self.fps_var.set(cfg["fps"])
            if "quality" in cfg: self.quality_var.set(cfg["quality"])
            if "shortcuts" in cfg: self._shortcuts.update(cfg["shortcuts"])
            for action, lbl in self._hotkey_labels.items(): lbl.configure(text=self._shortcuts.get(action, "—"))
            self._register_hotkeys()
        except: pass

if __name__ == "__main__":
    app = App()
    app._load_settings()
    app.mainloop()