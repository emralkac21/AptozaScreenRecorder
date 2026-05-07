# AudioEffectsModule.py
import os, subprocess, threading, tempfile, shutil
import customtkinter as ctk
from tkinter import filedialog, messagebox
try:
    from PIL import Image
except ImportError:
    pass

try:
    import pygame
    pygame.mixer.init()
    AUDIO_PLAY_OK = True
except ImportError:
    AUDIO_PLAY_OK = False

def _no_window():
    """Windows'ta CMD penceresinin açılmasını engeller."""
    if os.name == 'nt':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
    return {}

def _get_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True, timeout=10, **_no_window())
        return float(r.stdout.strip())
    except: return 0.0

class AudioEffectsEngine:
    @staticmethod
    def build_filters(params, total_dur=None):
        filters = []
        
        # 1. Temel Seviye ve Gürültü
        if params.get("volume", 1.0) != 1.0: filters.append(f"volume={params['volume']}")
        if params.get("noise", False): filters.append("afftdn=nf=-25")
        if params.get("silence", False): filters.append("silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-35dB")
        if params.get("loudnorm", False): filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        if params.get("compressor", False): filters.append("acompressor=threshold=-20dB:ratio=4:attack=5:release=50")
        
        # Panning (Sağ-Sol Denge) -> -1.0 (Sol) ile 1.0 (Sağ) arası
        pan = params.get("panning", 0.0)
        if pan != 0.0:
            left_gain = min(1.0, 1.0 - pan)
            right_gain = min(1.0, 1.0 + pan)
            filters.append(f"pan=stereo|c0={left_gain}*c0|c1={right_gain}*c1")
        elif params.get("stereo", False): 
            filters.append("pan=stereo|c0=c0|c1=c0")
        
        # Karaoke / Vokal Silici (Faz iptali tekniği)
        if params.get("vocal_remove", False):
            filters.append("pan=stereo|c0=0.5*c0-0.5*c1|c1=0.5*c1-0.5*c0")

        # 2. EQ ve Frekans Filtreleri (High-Pass / Low-Pass)
        bass = params.get("bass", 0.0)
        treble = params.get("treble", 0.0)
        if bass != 0.0: filters.append(f"bass=g={bass}")
        if treble != 0.0: filters.append(f"treble=g={treble}")
        
        highpass = params.get("highpass", 0.0)
        if highpass > 0: filters.append(f"highpass=f={highpass}")
        
        lowpass = params.get("lowpass", 20000.0)
        if lowpass < 20000.0: filters.append(f"lowpass=f={lowpass}")

        # 3. Eğlence / Modifikasyon
        pitch = params.get("pitch", 1.0)
        if pitch != 1.0: 
            filters.append(f"asetrate=44100*{pitch},atempo=1/{pitch}")
        
        speed = params.get("speed", 1.0)
        if speed != 1.0: filters.append(f"atempo={speed}")
        
        if params.get("echo", False): filters.append("aecho=0.8:0.9:500:0.4")
        if params.get("reverse", False): filters.append("areverse")
        
        # 4. Audacity Tarzı Modülasyonlar
        if params.get("chorus", False): filters.append("chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3")
        if params.get("flanger", False): filters.append("flanger=delay=0")
        if params.get("tremolo", False): filters.append("tremolo=f=5.0:d=0.5")
        if params.get("vibrato", False): filters.append("vibrato=f=7.0:d=0.5")

        # 5. Fade
        fade_in = params.get("fade_in", 0.0)
        fade_out = params.get("fade_out", 0.0)
        if fade_in > 0: filters.append(f"afade=t=in:ss=0:d={fade_in}")
        if fade_out > 0 and total_dur and total_dur > fade_out:
            filters.append(f"afade=t=out:st={total_dur-fade_out}:d={fade_out}")
            
        return filters

class AudioEffectsTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.TXT2 = "#8b949e"; self.ACCENT = "#238636"; self.ACCENT2 = "#1f538d"; self.RED = "#da3633"; self.YELLOW = "#d29922"; self.BORDER = "#30363d"
        self._temp_preview_file = None
        self.selected_files = [] 
        self._build_ui()

    def _build_ui(self):
        # Sol Taraf: Ayarlar (Scrollable)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        # Sağ Taraf: Önizleme & Dalga Formu
        self.right_panel = ctk.CTkFrame(self, width=320, fg_color="#1c2128", corner_radius=10)
        self.right_panel.pack(side="right", fill="y", padx=(5, 10), pady=10)
        self.right_panel.pack_propagate(False)

        # --- SAĞ PANEL (GÖRSEL VE BİLGİ) ---
        ctk.CTkLabel(self.right_panel, text="🎙️ Dosya & Önizleme", font=ctk.CTkFont("Arial", 14, "bold")).pack(pady=10)
        
        self.btn_select = ctk.CTkButton(self.right_panel, text="📂 Ses Dosyası Seç", fg_color=self.ACCENT2, command=self._pick_files)
        self.btn_select.pack(fill="x", padx=15, pady=5)
        
        self.lbl_file_info = ctk.CTkLabel(self.right_panel, text="Dosya seçilmedi", text_color=self.TXT2, font=ctk.CTkFont("Arial", 11), wraplength=280)
        self.lbl_file_info.pack(pady=5, padx=10)

        # Waveform Ekranı
        self.lbl_waveform = ctk.CTkLabel(self.right_panel, text="Dalga Formu Bekleniyor...", bg_color="#0d1117", width=290, height=100)
        self.lbl_waveform.pack(pady=10, padx=15)

        self.status_lbl = ctk.CTkLabel(self.right_panel, text="", font=ctk.CTkFont("Arial", 11, "bold"), text_color=self.TXT2, wraplength=280)
        self.status_lbl.pack(pady=5)

        # İşlem Butonları
        btn_f = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        btn_f.pack(side="bottom", fill="x", pady=15, padx=15)
        
        ctk.CTkButton(btn_f, text="⏹️", width=36, fg_color=self.RED, command=self._stop_preview).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_f, text="▶️ Önizle", fg_color=self.ACCENT2, command=self._preview_audio).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(self.right_panel, text="✨ Efektleri Uygula & Kaydet", height=40, fg_color="#d29922", hover_color="#b07d17", font=ctk.CTkFont("Arial", 13, "bold"), command=self._apply_and_save).pack(side="bottom", fill="x", padx=15)

        # --- SOL PANEL (AYARLAR) ---
        self.vars = {}
        def _add_section(title):
            f = ctk.CTkFrame(self.scroll, fg_color="#161b22", corner_radius=8)
            f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=5)
            return f

        # 1. Profesyonel İyileştirmeler
        f1 = _add_section("🎛️ Profesyonel İyileştirmeler")
        self._add_switch(f1, "Otomatik Normalizasyon (Loudnorm)", "loudnorm")
        self._add_switch(f1, "Gürültü Temizleme (Denoise)", "noise")
        self._add_switch(f1, "Ses Patlaması Önleyici (Compressor)", "compressor")
        self._add_switch(f1, "Boşlukları/Sessizliği Sil", "silence")
        self._add_switch(f1, "Mono'yu Stereo'ya Çevir", "stereo")
        self._add_slider(f1, "Ana Ses Seviyesi:", "volume", 0.0, 4.0, 1.0, 1)

        # 2. Audacity Filtreleri & EQ
        f2 = _add_section("📻 Ekolayzer & Filtreler")
        self._add_slider(f2, "High-Pass Filtre (Hz) (Uğultu Keser):", "highpass", 0.0, 2000.0, 0.0, 0)
        self._add_slider(f2, "Low-Pass Filtre (Hz) (Cızırtı Keser):", "lowpass", 500.0, 20000.0, 20000.0, 0)
        self._add_slider(f2, "Bas (Bass) dB:", "bass", -15.0, 15.0, 0.0, 1)
        self._add_slider(f2, "Tiz (Treble) dB:", "treble", -15.0, 15.0, 0.0, 1)
        self._add_slider(f2, "Sol/Sağ Denge (Pan):", "panning", -1.0, 1.0, 0.0, 1)

        # 3. Vokal & Karaoke
        f3 = _add_section("🎤 Vokal & Karaoke Modu")
        self._add_switch(f3, "Vokal Silici (Karaoke Altyapısı Oluştur)", "vocal_remove")

        # 4. Modülasyon Efektleri
        f4 = _add_section("🌀 Modülasyon Efektleri")
        self._add_switch(f4, "Chorus (Çoklu Ses Efekti)", "chorus")
        self._add_switch(f4, "Flanger (Metalik Dalgalanma)", "flanger")
        self._add_switch(f4, "Vibrato (Ses Titremesi)", "vibrato")
        self._add_switch(f4, "Tremolo (Hacim Titremesi)", "tremolo")

        # 5. Yaratıcı ve Eğlenceli Efektler
        f5 = _add_section("🎭 Yaratıcı & Eğlenceli (FX)")
        self._add_slider(f5, "Ses Tonu (Pitch - Kalın/İnce):", "pitch", 0.5, 2.0, 1.0, 2)
        self._add_slider(f5, "Hız (Tempo):", "speed", 0.5, 2.0, 1.0, 2)
        self._add_switch(f5, "Yankı ve Derinlik (Echo)", "echo")
        self._add_switch(f5, "Tersine Çevir (Reverse)", "reverse")

        # 6. Zaman ve Geçişler
        f6 = _add_section("⏱️ Geçişler (Fade)")
        self._add_entry(f6, "Artarak Girme - Fade In (sn):", "fade_in", "0.0")
        self._add_entry(f6, "Azalarak Çıkma - Fade Out (sn):", "fade_out", "0.0")

    def _add_switch(self, parent, text, key):
        var = ctk.BooleanVar(value=False); self.vars[key] = var
        ctk.CTkSwitch(parent, text=text, variable=var).pack(anchor="w", padx=15, pady=3)

    def _add_slider(self, parent, text, key, min_val, max_val, default, decimals=1):
        r = ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(r, text=text, width=220, anchor="w", text_color=self.TXT2).pack(side="left")
        var = ctk.DoubleVar(value=default); self.vars[key] = var
        lbl_format = f"{{:.{decimals}f}}"
        lbl = ctk.CTkLabel(r, text=lbl_format.format(default), width=45, text_color=self.ACCENT2, font=ctk.CTkFont("Arial", 11, "bold"))
        ctk.CTkSlider(r, variable=var, from_=min_val, to=max_val, command=lambda v: lbl.configure(text=lbl_format.format(float(v)))).pack(side="left", expand=True, fill="x", padx=5)
        lbl.pack(side="left")

    def _add_entry(self, parent, text, key, default):
        r = ctk.CTkFrame(parent, fg_color="transparent"); r.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(r, text=text, width=220, anchor="w", text_color=self.TXT2).pack(side="left")
        var = ctk.StringVar(value=default); self.vars[key] = var
        ctk.CTkEntry(r, textvariable=var, width=60).pack(side="right")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(title="Ses Seç", filetypes=[("Ses Dosyaları", "*.mp3 *.wav *.ogg *.aac *.flac *.m4a *.wma"), ("Tümü", "*.*")])
        if paths:
            self.selected_files = list(paths)
            if len(self.selected_files) == 1:
                self.lbl_file_info.configure(text=f"Seçili: {os.path.basename(self.selected_files[0])}")
            else:
                self.lbl_file_info.configure(text=f"Toplu İşlem: {len(self.selected_files)} dosya seçildi.")
            self._generate_waveform(self.selected_files[0])

    def _generate_waveform(self, path):
        self.lbl_waveform.configure(text="Dalga Formu Yükleniyor...", image=None)
        def _run():
            tmp_img = tempfile.mktemp(suffix=".png")
            cmd = ["ffmpeg", "-y", "-i", path, "-filter_complex", "showwavespic=s=290x100:colors=0x238636", "-frames:v", "1", tmp_img]
            subprocess.run(cmd, capture_output=True, **_no_window())
            if os.path.exists(tmp_img):
                try:
                    img = Image.open(tmp_img)
                    c_img = ctk.CTkImage(light_image=img, dark_image=img, size=(290, 100))
                    self.after(0, lambda: self.lbl_waveform.configure(image=c_img, text=""))
                except: pass
        threading.Thread(target=_run, daemon=True).start()

    def _get_current_params(self):
        p = {}
        for k, v in self.vars.items():
            try:
                if isinstance(v, ctk.BooleanVar): p[k] = v.get()
                elif isinstance(v, ctk.DoubleVar): p[k] = v.get()
                elif isinstance(v, ctk.StringVar): p[k] = float(v.get() or 0.0)
            except: p[k] = 0.0
        return p

    def _preview_audio(self):
        if not AUDIO_PLAY_OK: return messagebox.showerror("Hata", "Pygame başlatılamadı.")
        if not self.selected_files: return messagebox.showwarning("Uyarı", "Ses dosyası seçin.")
        
        self._stop_preview()
        self.status_lbl.configure(text="⏳ Önizleme hazırlanıyor (Max 45 sn)...", text_color=self.YELLOW)

        def _run():
            try:
                self._temp_preview_file = tempfile.mktemp(suffix=".wav")
                src = self.selected_files[0]
                dur = _get_duration(src)
                filters = AudioEffectsEngine.build_filters(self._get_current_params(), total_dur=min(dur, 45.0))
                
                cmd = ["ffmpeg", "-y", "-i", src, "-t", "45", "-vn"]
                if filters: cmd += ["-af", ",".join(filters)]
                cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", self._temp_preview_file]
                
                subprocess.run(cmd, capture_output=True, timeout=30, **_no_window())
                if os.path.exists(self._temp_preview_file):
                    pygame.mixer.music.load(self._temp_preview_file)
                    pygame.mixer.music.play()
                    self.after(0, lambda: self.status_lbl.configure(text="▶️ Önizleme çalıyor...", text_color=self.ACCENT))
                else:
                    self.after(0, lambda: self.status_lbl.configure(text="✗ Önizleme hatası.", text_color=self.RED))
            except Exception as e:
                self.after(0, lambda: self.status_lbl.configure(text=f"✗ Hata: {str(e)[:50]}", text_color=self.RED))

        threading.Thread(target=_run, daemon=True).start()

    def _stop_preview(self):
        if AUDIO_PLAY_OK:
            try: pygame.mixer.music.stop()
            except: pass
        self.status_lbl.configure(text="⏹️ Durduruldu.", text_color=self.TXT2)

    def _apply_and_save(self):
        if not self.selected_files: return messagebox.showwarning("Uyarı", "Ses dosyası seçin.")
        params = self._get_current_params()
        
        is_batch = len(self.selected_files) > 1
        out_dir = None
        single_out = None

        if is_batch:
            out_dir = filedialog.askdirectory(title="Toplu İşlem: Kaydedilecek Klasörü Seçin")
            if not out_dir: return
        else:
            ext = os.path.splitext(self.selected_files[0])[1]
            single_out = filedialog.asksaveasfilename(title="Dosyayı Kaydet", defaultextension=ext, filetypes=[(ext.upper(), f"*{ext}")])
            if not single_out: return

        self._stop_preview()
        self.status_lbl.configure(text="⏳ İşleniyor... Lütfen bekleyin.", text_color=self.YELLOW)

        def _run():
            success_count = 0
            for src in self.selected_files:
                try:
                    if is_batch:
                        base_name = os.path.basename(src)
                        name, ext = os.path.splitext(base_name)
                        out_path = os.path.join(out_dir, f"{name}_FX{ext}")
                    else:
                        out_path = single_out

                    dur = _get_duration(src)
                    filters = AudioEffectsEngine.build_filters(params, total_dur=dur)
                    
                    cmd = ["ffmpeg", "-y", "-i", src, "-vn"]
                    if filters: cmd += ["-af", ",".join(filters)]
                    
                    out_ext = os.path.splitext(out_path)[1].lower()
                    if out_ext == ".mp3": cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
                    elif out_ext == ".wav": cmd += ["-c:a", "pcm_s16le"]
                    elif out_ext in [".aac", ".m4a"]: cmd += ["-c:a", "aac", "-b:a", "192k"]
                    else: cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]

                    cmd.append(out_path)
                    r = subprocess.run(cmd, capture_output=True, timeout=600, **_no_window())
                    if r.returncode == 0: success_count += 1
                except: pass

            if success_count == len(self.selected_files):
                msg = "✓ Toplu işlem tamamlandı!" if is_batch else "✓ Başarıyla kaydedildi!"
                self.after(0, lambda: self.status_lbl.configure(text=msg, text_color=self.ACCENT))
            else:
                self.after(0, lambda: self.status_lbl.configure(text=f"⚠️ {success_count}/{len(self.selected_files)} dosya işlendi.", text_color=self.YELLOW))

        threading.Thread(target=_run, daemon=True).start()