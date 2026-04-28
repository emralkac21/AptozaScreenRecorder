#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageToVideoModule.py - EkranKayıt Pro için Görselden Video Dönüştürücü Modülü
(Efekt ve Filtre Destekli, Çökme Korumalı, ÖN İZLEMELİ Sürüm)
"""
import os
import shutil
import subprocess
import threading
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image  # Ön izleme görselini yüklemek için gerekli

# ── Paylaşılan yardımcıları AQ2'den al; çift tanım yapmıyoruz ────────────────
try:
    from AQ2 import _no_window, BG, CARD, CARD2, BORDER, ACCENT, RED, YELLOW, TXT, TXT2
except ImportError:
    # AQ2 bulunamadıysa (bağımsız test) fallback tanımlar
    def _no_window():
        if os.name == 'nt':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            return {'startupinfo': si, 'creationflags': subprocess.CREATE_NO_WINDOW}
        return {}
    BG = "#0d1117"; CARD = "#161b22"; CARD2 = "#1c2128"; BORDER = "#30363d"
    ACCENT = "#238636"; RED = "#da3633"; YELLOW = "#d29922"
    TXT = "#e6edf3"; TXT2 = "#8b949e"

class ImageToVideoEditor(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.images = []  # [{'path': str, 'duration': float, 'effects': dict}, ...]
        self._has_ffmpeg = shutil.which("ffmpeg") is not None
        self._build_ui()

    def _build_ui(self):
        # ── Üst Başlık & Butonlar ──
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(hdr, text="🖼️ Görselden Video Oluştur", font=ctk.CTkFont("Arial", 18, "bold"), text_color=TXT).pack(side="left")
        
        btn_style = dict(width=110, height=32, font=ctk.CTkFont("Arial", 12))
        ctk.CTkButton(hdr, text="➕ Görsel Ekle", fg_color="#1f538d", hover_color="#2a6ca8", **btn_style, command=self._add_images).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="🗑️ Listeyi Temizle", fg_color=RED, hover_color="#7f1d1d", **btn_style, command=self._clear_list).pack(side="right", padx=4)

        if not self._has_ffmpeg:
            ctk.CTkLabel(self, text="⚠️ ffmpeg bulunamadı. Bu özellik çalışmayacaktır.", text_color=YELLOW, font=ctk.CTkFont("Arial", 13)).pack(pady=20)
            return

        # ── Ana İçerik (Sol: Liste, Sağ: Ayarlar) ──
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        # Sol: Görsel Listesi
        left = ctk.CTkFrame(body, fg_color=CARD, corner_radius=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(left, text="📁 Görsel Sırası & Süreler", font=ctk.CTkFont("Arial", 13, "bold"), text_color=TXT).pack(anchor="w", padx=12, pady=(10, 6))
        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # Sağ: Ayarlar Paneli
        right = ctk.CTkFrame(body, fg_color=CARD, corner_radius=8, width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="⚙️ Çıktı Ayarları", font=ctk.CTkFont("Arial", 14, "bold"), text_color=TXT).pack(anchor="w", padx=12, pady=(12, 6))

        # Çözünürlük
        ctk.CTkLabel(right, text="Video Çözünürlüğü:", text_color=TXT2).pack(anchor="w", padx=12, pady=(6, 2))
        self.res_var = ctk.StringVar(value="1920x1080")
        self.res_menu = ctk.CTkOptionMenu(right, variable=self.res_var, values=["1920x1080", "1280x720", "854x480", "Özel"], width=200, command=lambda c: self._toggle_custom_res())
        self.res_menu.pack(fill="x", padx=12, pady=2)

        self.custom_res_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.cust_w = ctk.CTkEntry(self.custom_res_frame, placeholder_text="Genişlik", width=90)
        self.cust_w.pack(side="left", padx=(0, 6))
        self.cust_h = ctk.CTkEntry(self.custom_res_frame, placeholder_text="Yükseklik", width=90)
        self.cust_h.pack(side="left")
        self.custom_res_frame.pack(fill="x", padx=12, pady=(0, 4))
        self.custom_res_frame.pack_forget()

        # Varsayılan Süre
        ctk.CTkLabel(right, text="Varsayılan Süre (sn):", text_color=TXT2).pack(anchor="w", padx=12, pady=(10, 2))
        self.def_dur_var = ctk.StringVar(value="5.0")
        ctk.CTkEntry(right, textvariable=self.def_dur_var).pack(fill="x", padx=12, pady=2)

        # Çıktı Yolu
        ctk.CTkLabel(right, text="Kayıt Yeri & İsim:", text_color=TXT2).pack(anchor="w", padx=12, pady=(10, 2))
        out_row = ctk.CTkFrame(right, fg_color="transparent")
        out_row.pack(fill="x", padx=12, pady=2)
        self.out_path_var = ctk.StringVar()
        ctk.CTkEntry(out_row, textvariable=self.out_path_var, placeholder_text="gorsel_video.mp4").pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(out_row, text="📂", width=36, command=self._pick_output).pack(side="right")

        # Durum & Başlat Butonu
        self.status_lbl = ctk.CTkLabel(right, text="", text_color=TXT2, font=ctk.CTkFont("Arial", 11))
        self.status_lbl.pack(pady=(12, 6))

        self.gen_btn = ctk.CTkButton(right, text="🎬 Video Oluştur", height=40, fg_color=ACCENT, hover_color="#1a6e2a",
                                     font=ctk.CTkFont("Arial", 14, "bold"), command=self._generate)
        self.gen_btn.pack(fill="x", padx=12, pady=(4, 12))

    def _toggle_custom_res(self, *args):
        if self.res_var.get() == "Özel":
            self.custom_res_frame.pack(fill="x", padx=12, pady=(0, 4))
        else:
            self.custom_res_frame.pack_forget()

    def _add_images(self):
        paths = filedialog.askopenfilenames(title="Görsel Seç", filetypes=[("Görseller", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if not paths: return
        try:
            default_dur = float(self.def_dur_var.get())
        except:
            default_dur = 5.0
        for p in paths:
            self.images.append({"path": p, "duration": default_dur, "effects": {}})
        self._render_list()

    def _clear_list(self):
        self.images.clear()
        self._render_list()

    def _render_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        for i, img in enumerate(self.images):
            row = ctk.CTkFrame(self.list_frame, fg_color=CARD2, corner_radius=6)
            row.pack(fill="x", pady=3, padx=4)
            
            name = os.path.basename(img["path"])
            if len(name) > 28: name = name[:25] + "..."
            ctk.CTkLabel(row, text=f"🖼️ {name}", width=180, anchor="w", text_color=TXT).pack(side="left", padx=8, pady=4)
            
            dur_lbl = ctk.CTkLabel(row, text="Süre:", text_color=TXT2, font=ctk.CTkFont("Arial", 11))
            dur_lbl.pack(side="left", padx=(4, 2))
            dur_entry = ctk.CTkEntry(row, width=55)
            dur_entry.insert(0, str(img["duration"]))
            dur_entry.pack(side="left", padx=(0, 4))
            
            def _save(idx=i, ent=dur_entry):
                try: self.images[idx]["duration"] = max(0.1, float(ent.get()))
                except: ent.delete(0, "end"); ent.insert(0, str(self.images[idx]["duration"]))
            dur_entry.bind("<FocusOut>", lambda e, s=_save: s())
            dur_entry.bind("<Return>", lambda e, s=_save: s())
            
            ctk.CTkButton(row, text="✕", width=26, fg_color=RED, hover_color="#7f1d1d", font=ctk.CTkFont("Arial", 10),
                          command=lambda idx=i: self._remove_image(idx)).pack(side="right", padx=4, pady=4)
            ctk.CTkButton(row, text="🎨", width=26, fg_color="#d29922", hover_color="#b07d17", font=ctk.CTkFont("Arial", 10),
                          command=lambda idx=i: self._open_effects_window(idx)).pack(side="right", padx=4, pady=4)

    def _remove_image(self, idx):
        self.images.pop(idx)
        self._render_list()

    # ── FİLTRE VE EFEKT ZİNCİRİNİ OLUŞTURAN YARDIMCI FONKSİYON ──
    def _build_vf_list(self, eff, w, h, dur=None, is_preview=False):
        """Efekt ayarlarından FFMPEG -vf (video filter) dizilimini oluşturur."""
        vf_list = []

        # 1. Transform: Oranlar bozulmadan önce döndürme ve çevirme
        if eff.get("rotate", False): vf_list.append("transpose=1")
        if eff.get("mirror", False): vf_list.append("hflip")
        if eff.get("vflip", False): vf_list.append("vflip")
        if eff.get("invert", False): vf_list.append("negate")

        # 2. Ölçeklendirme ve Merkeze Oturtma
        # Önizlemede küçük boyut yeterli (daha hızlı), final videoda hedef çözünürlük kullanılır
        if is_preview:
            pw, ph = 400, 400
            vf_list.append(f"scale={pw}:{ph}:force_original_aspect_ratio=decrease")
            vf_list.append(f"pad={pw}:{ph}:(ow-iw)/2:(oh-ih)/2:color=black")
        else:
            vf_list.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease")
            vf_list.append(f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black")

        # 3. Renk, Işık ve Filtreler
        b = eff.get("brightness", 0.0)
        c = eff.get("contrast", 1.0)
        s = eff.get("saturation", 1.0)
        g = eff.get("gamma", 1.0)
        if any(val != default for val, default in [(b, 0.0), (c, 1.0), (s, 1.0), (g, 1.0)]):
            vf_list.append(f"eq=brightness={b}:contrast={c}:saturation={s}:gamma={g}")

        h_val = eff.get("hue", 0.0)
        if h_val != 0.0: vf_list.append(f"hue=h={h_val}")

        blur = eff.get("blur", 0.0)
        if blur > 0: vf_list.append(f"boxblur={blur}:1")

        if eff.get("sepia", False):
            vf_list.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        elif eff.get("bw", False):
            vf_list.append("hue=s=0")
        elif eff.get("red_filter", False):
            vf_list.append("colorchannelmixer=1:0:0:0:0:0:0:0:0:0:0:0")
        elif eff.get("blue_filter", False):
            vf_list.append("colorchannelmixer=0:0:0:0:0:0:0:0:0:0:1:0")

        if eff.get("vignette", False): vf_list.append("vignette")
        if eff.get("sharpen", False): vf_list.append("unsharp=5:5:1.0:5:5:0.0")

        # 4. Solma Efektleri (Fade) - Sadece final videoda uygulanır, ön izlemede statik resim olduğu için atlanır
        if not is_preview and dur is not None:
            fi = eff.get("fade_in", 0.0)
            fo = eff.get("fade_out", 0.0)
            if fi > 0: vf_list.append(f"fade=t=in:st=0:d={fi}")
            if fo > 0:
                st = max(0, dur - fo)
                vf_list.append(f"fade=t=out:st={st}:d={fo}")

        return vf_list

    def _open_effects_window(self, idx):
        """Her görsel için özel efekt ayarları ve ÖN İZLEME penceresini açar"""
        win = ctk.CTkToplevel(self)
        win.title("Efekt ve Filtre Ayarları")
        win.geometry("950x550") # Pencereyi ön izleme için genişlettik
        win.attributes("-topmost", True)
        win.grab_set()

        eff = self.images[idx].setdefault("effects", {})
        vars_dict = {}

        # Ana Taşıyıcı Çerçeve (Sol Sekmeler, Sağ Ön İzleme)
        main_frame = ctk.CTkFrame(win, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── SOL TARAF: AYARLAR (Sekmeler) ──
        left_frame = ctk.CTkFrame(main_frame, width=400, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        tabs = ctk.CTkTabview(left_frame)
        tabs.pack(fill="both", expand=True)

        tab_color = tabs.add("Renk & Işık")
        tab_fx = tabs.add("Filtreler")
        tab_trans = tabs.add("Dönüşüm")

        # ── SAĞ TARAF: ÖN İZLEME ──
        right_frame = ctk.CTkFrame(main_frame, width=450, fg_color=CARD2, corner_radius=10)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        right_frame.pack_propagate(False)

        ctk.CTkLabel(right_frame, text="📸 Canlı Ön İzleme", font=ctk.CTkFont("Arial", 14, "bold")).pack(pady=(10, 0))
        
        self.preview_lbl = ctk.CTkLabel(right_frame, text="⏳ Ön İzleme Yükleniyor...", text_color=TXT2)
        self.preview_lbl.pack(expand=True, fill="both", padx=10, pady=10)

        # ── ÖN İZLEME MOTORU (Debounce) ──
        # NOT: Her pencere kendi yerel timer ve label referansını tutar.
        # self üzerinde saklanırsa eş zamanlı iki pencerede race condition oluşur.
        _preview_timer = [None]          # list-cell → closure'dan mutate edilebilir
        _preview_lbl_ref = [self.preview_lbl]

        def schedule_preview(*args):
            """Herhangi bir ayar değiştiğinde, kısa süre sonra ön izlemeyi yeniler."""
            if _preview_timer[0] is not None:
                win.after_cancel(_preview_timer[0])
            _preview_timer[0] = win.after(400, generate_preview)  # 400ms bekler, kasmayı önler

        def generate_preview():
            # Güncel ayarları geçici olarak topla
            current_eff = {}
            for k, v in vars_dict.items():
                val = v.get()
                if isinstance(v, ctk.StringVar):
                    try: val = float(val)
                    except: val = 0.0
                current_eff[k] = val

            # FFMPEG'i UI'ı dondurmamak için arkaplan iş parçacığında çalıştır
            threading.Thread(target=_run_ffmpeg_preview, args=(current_eff,), daemon=True).start()

        def _run_ffmpeg_preview(current_eff):
            img_path = self.images[idx]["path"]
            w, h = self._get_target_res()
            tmp_img = os.path.join(tempfile.gettempdir(), f"preview_tmp_{idx}.jpg")

            # Pencere hâlâ açıksa label'ı güvenle günceller
            def _safe_update(text="", image=""):
                try:
                    if win.winfo_exists():
                        win.after(0, lambda t=text, i=image:
                                  _preview_lbl_ref[0].configure(text=t, image=i))
                except Exception:
                    pass

            vf_list   = self._build_vf_list(current_eff, w, h, is_preview=True)
            vf_string = ",".join(vf_list)

            cmd = ["ffmpeg", "-y", "-i", img_path, "-vframes", "1"]
            if vf_string:
                cmd.extend(["-vf", vf_string])
            cmd.append(tmp_img)

            try:
                r = subprocess.run(cmd, capture_output=True, timeout=10, **_no_window())
                if r.returncode == 0 and os.path.exists(tmp_img):
                    try:
                        pil_image = Image.open(tmp_img)
                        pil_image.thumbnail((400, 400))
                        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image,
                                               size=pil_image.size)
                        _safe_update(image=ctk_img)
                    except Exception:
                        _safe_update(text="Resim Yüklenemedi.")
                else:
                    _safe_update(text="Hata oluştu.")
            except Exception:
                _safe_update(text="FFmpeg zaman aşımı.")


        # ── Sekme İçerikleri ──
        def create_slider(parent, text, key, from_, to, default):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=5)
            ctk.CTkLabel(frame, text=text, width=120, anchor="w").pack(side="left")
            var = ctk.DoubleVar(value=eff.get(key, default))
            vars_dict[key] = var
            slider = ctk.CTkSlider(frame, from_=from_, to=to, variable=var)
            slider.pack(side="left", fill="x", expand=True, padx=10)
            val_lbl = ctk.CTkLabel(frame, text=f"{var.get():.2f}", width=40)
            val_lbl.pack(side="left")
            
            # Değer değiştiğinde hem etiketi güncelle hem ön izlemeyi tetikle
            def _update(val, l=val_lbl): 
                l.configure(text=f"{float(val):.2f}")
                schedule_preview()
            slider.configure(command=_update)

        create_slider(tab_color, "Parlaklık", "brightness", -1.0, 1.0, 0.0)
        create_slider(tab_color, "Kontrast", "contrast", -2.0, 2.0, 1.0)
        create_slider(tab_color, "Doygunluk", "saturation", 0.0, 3.0, 1.0)
        create_slider(tab_color, "Gama", "gamma", 0.1, 3.0, 1.0)
        create_slider(tab_color, "Ton (Hue)", "hue", 0.0, 360.0, 0.0)

        def create_switch(parent, text, key):
            var = ctk.BooleanVar(value=eff.get(key, False))
            vars_dict[key] = var
            ctk.CTkSwitch(parent, text=text, variable=var, command=schedule_preview).pack(anchor="w", pady=6, padx=10)

        create_slider(tab_fx, "Bulanıklık (Blur)", "blur", 0.0, 20.0, 0.0)
        create_switch(tab_fx, "Siyah Beyaz", "bw")
        create_switch(tab_fx, "Sepya (Sepia)", "sepia")
        create_switch(tab_fx, "Kırmızı Filtre", "red_filter")
        create_switch(tab_fx, "Mavi Filtre", "blue_filter")
        create_switch(tab_fx, "Vignette (Karartma)", "vignette")
        create_switch(tab_fx, "Keskinleştir", "sharpen")
        create_switch(tab_fx, "Renkleri Ters Çevir", "invert")

        create_switch(tab_trans, "Ayna (Yatay Çevir)", "mirror")
        create_switch(tab_trans, "Dikey Çevir", "vflip")
        create_switch(tab_trans, "Döndür (90° Sağa)", "rotate")

        ctk.CTkLabel(tab_trans, text="Solarak Girme (Fade In) Sn:", anchor="w").pack(fill="x", pady=(15, 0), padx=10)
        fade_in_var = ctk.StringVar(value=str(eff.get("fade_in", 0.0)))
        vars_dict["fade_in"] = fade_in_var
        ent1 = ctk.CTkEntry(tab_trans, textvariable=fade_in_var)
        ent1.pack(fill="x", pady=4, padx=10)
        
        ctk.CTkLabel(tab_trans, text="Solarak Çıkma (Fade Out) Sn:", anchor="w").pack(fill="x", pady=(10, 0), padx=10)
        fade_out_var = ctk.StringVar(value=str(eff.get("fade_out", 0.0)))
        vars_dict["fade_out"] = fade_out_var
        ent2 = ctk.CTkEntry(tab_trans, textvariable=fade_out_var)
        ent2.pack(fill="x", pady=4, padx=10)

        def _save_and_close():
            for k, v in vars_dict.items():
                val = v.get()
                if isinstance(v, ctk.StringVar):
                    try: val = float(val)
                    except ValueError: val = 0.0
                self.images[idx]["effects"][k] = val
            win.destroy()

        save_btn = ctk.CTkButton(left_frame, text="💾 Ayarları Kaydet", command=_save_and_close, fg_color=ACCENT, hover_color="#1a6e2a")
        save_btn.pack(pady=15, side="bottom")

        # Pencere ilk açıldığında varsayılan ön izlemeyi yükle
        schedule_preview()

    def _pick_output(self):
        p = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if p: self.out_path_var.set(p)

    def _get_target_res(self):
        res_str = self.res_var.get()
        if res_str == "Özel":
            try: return int(self.cust_w.get()), int(self.cust_h.get())
            except: return 1920, 1080
        w, h = res_str.split("x")
        return int(w), int(h)

    def _generate(self):
        if not self.images:
            messagebox.showwarning("Uyarı", "Lütfen en az bir görsel ekleyin.")
            return
        out_path = self.out_path_var.get()
        if not out_path:
            messagebox.showwarning("Uyarı", "Lütfen çıktı dosyası konumunu seçin.")
            return

        self.gen_btn.configure(state="disabled")
        self.status_lbl.configure(text="⏳ İşleniyor... Lütfen bekleyin.", text_color=YELLOW)

        def _run_ffmpeg():
            tmp_dir = tempfile.mkdtemp()
            w, h = self._get_target_res()
            try:
                temp_clips = []
                for i, img in enumerate(self.images):
                    clip_path = os.path.join(tmp_dir, f"clip_{i:03d}.mp4")
                    dur = max(0.1, img["duration"])
                    eff = img.get("effects", {})
                    
                    # Filtre listesini ortak fonksiyondan çek
                    vf_list = self._build_vf_list(eff, w, h, dur=dur, is_preview=False)
                    vf_string = ",".join(vf_list)

                    cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(dur), "-i", img["path"],
                           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30"]
                    if vf_string:
                        cmd += ["-vf", vf_string]
                    cmd.append(clip_path)
                    
                    r = subprocess.run(cmd, capture_output=True, timeout=60, **_no_window())
                    if r.returncode != 0:
                        raise RuntimeError(f"Görsel işleme hatası: {r.stderr.decode('utf-8', errors='ignore')[:120]}")
                    temp_clips.append(clip_path)

                list_path = os.path.join(tmp_dir, "list.txt")
                with open(list_path, "w", encoding="utf-8") as f:
                    for c in temp_clips:
                        f.write(f"file '{c.replace(chr(92), '/')}'\n")

                cmd_merge = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                             "-c", "copy", "-movflags", "+faststart", out_path]
                r2 = subprocess.run(cmd_merge, capture_output=True, timeout=60, **_no_window())
                if r2.returncode == 0:
                    self.after(0, lambda: self._finish(True, "✅ Video başarıyla oluşturuldu!"))
                else:
                    raise RuntimeError(f"Birleştirme hatası: {r2.stderr.decode('utf-8', errors='ignore')[:120]}")
                    
            except Exception as e:
                self.after(0, lambda: self._finish(False, f"❌ Hata: {str(e)}"))
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        threading.Thread(target=_run_ffmpeg, daemon=True).start()

    def _finish(self, success, msg):
        self.gen_btn.configure(state="normal")
        color = ACCENT if success else RED
        self.status_lbl.configure(text=msg, text_color=color)
        if success:
            messagebox.showinfo("Tamamlandı", msg)