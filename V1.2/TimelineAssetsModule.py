# TimelineAssetsModule.py
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser

# Referans çözünürlük — ffmpeg'de W*/H* ile ölçeklenir, çözünürlük bağımsız
REF_W = 1920
REF_H = 1080

# ──────────────────────────────────────────────────────────────
#  VERİ MODELİ: Piksel tabanlı koordinat sistemi (1920x1080 ref)
# ──────────────────────────────────────────────────────────────
class AssetOverlay:
    def __init__(self, overlay_type="rect", path="",
                 x_px=100, y_px=100, w_px=400, h_px=200,
                 start_time=0.0, end_time=5.0,
                 color="#ffffff", thickness=3, opacity=1.0):
        self.uid        = id(self)
        self.type       = overlay_type   # "rect", "circle", "line", "image"
        self.path       = path           # Sadece image tipi için
        self.x_px       = int(x_px)     # Sol kenar, piksel (0 - REF_W)
        self.y_px       = int(y_px)     # Üst kenar, piksel (0 - REF_H)
        self.w_px       = max(1, int(w_px))  # Genişlik, piksel
        self.h_px       = max(1, int(h_px))  # Yükseklik, piksel
        self.start_time = start_time
        self.end_time   = end_time
        self.color      = color
        self.thickness  = int(thickness)
        self.opacity    = float(opacity)  # 0.0 – 1.0 (image için)

    # ffmpeg için normalize oranlar
    @property
    def x_pct(self): return self.x_px / REF_W
    @property
    def y_pct(self): return self.y_px / REF_H
    @property
    def w_pct(self): return self.w_px / REF_W
    @property
    def h_pct(self): return self.h_px / REF_H

    @property
    def name(self):
        if self.type == "image":
            base = os.path.basename(self.path)
            return f"🖼️ {base[:15]}" + ("..." if len(base) > 15 else "")
        type_map = {"rect": "⬜", "circle": "⭕", "line": "📏"}
        return f"{type_map.get(self.type, '📦')} {self.type.upper()} {self.x_px},{self.y_px}"


# ──────────────────────────────────────────────────────────────
#  FFMPEG FİLTRE ÜRETİCİSİ
# ──────────────────────────────────────────────────────────────
def build_asset_vf(assets, clip_start, clip_dur, vid_w=1920, vid_h=1080):
    """
    Asset listesini ffmpeg -vf parçalarına çevirir.

    drawbox W/H değişkenini desteklemez — koordinatlar sabit piksel olarak
    vid_w/vid_h referans alınarak hesaplanır.
    geq filtresi W/H/X/Y destekler, daire için kullanılmaya devam eder.
    Image assetleri filter_complex zincirine (movie+overlay) dönüştürülür.
    """
    # vid_w/vid_h sıfır gelirse güvenli varsayılan
    if not vid_w or not vid_h:
        vid_w, vid_h = REF_W, REF_H

    simple_parts = []
    img_data = []

    for a in assets:
        s = max(0.0, a.start_time - clip_start)
        e = min(a.end_time - clip_start, clip_dur)
        if e <= s:
            continue
        enable = f"enable='between(t,{s:.3f},{e:.3f})'"

        # Sabit piksel koordinatları: REF çözünürlüğünden gerçek çözünürlüğe ölçekle
        px_x = int(round(a.x_px * vid_w / REF_W))
        px_y = int(round(a.y_px * vid_h / REF_H))
        px_w = max(2, int(round(a.w_px * vid_w / REF_W)))
        px_h = max(2, int(round(a.h_px * vid_h / REF_H)))

        if a.type == "rect":
            hex_color = a.color.lstrip("#").upper().zfill(6)
            simple_parts.append(
                f"drawbox=x={px_x}:y={px_y}:w={px_w}:h={px_h}:"
                f"color=0x{hex_color}:thickness={a.thickness}:{enable}"
            )

        elif a.type == "circle":
            cx = px_x + px_w / 2
            cy = px_y + px_h / 2
            rx = max(1, px_w / 2)
            ry = max(1, px_h / 2)
            th = max(2, a.thickness)
            try:
                r_c = int(a.color[1:3], 16)
                g_c = int(a.color[3:5], 16)
                b_c = int(a.color[5:7], 16)
            except Exception:
                r_c, g_c, b_c = 255, 255, 255
            # geq: W/H/X/Y destekler — normalize koordinatlar güvenli
            cx_n  = cx  / vid_w
            cy_n  = cy  / vid_h
            rx_n  = rx  / vid_w
            ry_n  = ry  / vid_h
            rx_in = max(0.001, rx - th) / vid_w
            ry_in = max(0.001, ry - th) / vid_h
            dist    = (f"pow((X/W-{cx_n:.6f})/{rx_n:.6f}\\,2)"
                       f"+pow((Y/H-{cy_n:.6f})/{ry_n:.6f}\\,2)")
            dist_in = (f"pow((X/W-{cx_n:.6f})/{rx_in:.6f}\\,2)"
                       f"+pow((Y/H-{cy_n:.6f})/{ry_in:.6f}\\,2)")
            cond = f"lte({dist}\\,1.0)*gte({dist_in}\\,1.0)"
            simple_parts.append(
                f"geq="
                f"r='if({cond}\\,{r_c}\\,r(X\\,Y))':"
                f"g='if({cond}\\,{g_c}\\,g(X\\,Y))':"
                f"b='if({cond}\\,{b_c}\\,b(X\\,Y))':"
                f"{enable}"
            )

        elif a.type == "line":
            px_h_line = max(2, int(round(a.thickness * vid_h / REF_H)))
            hex_color = a.color.lstrip("#").upper().zfill(6)
            simple_parts.append(
                f"drawbox=x={px_x}:y={px_y}:w={px_w}:h={px_h_line}:"
                f"color=0x{hex_color}:thickness=-1:{enable}"
            )

        elif a.type == "image" and os.path.exists(a.path):
            img_data.append((a, s, e))

    result = []

    if img_data:
        movie_parts   = []
        overlay_parts = []
        prev_label    = "0:v"

        for idx, (a, s, e) in enumerate(img_data):
            safe_path = a.path.replace("\\", "/").replace("'", "\\'")
            enable    = f"enable='between(t,{s:.3f},{e:.3f})'"
            im_tag    = f"im{idx}"
            is_last   = (idx == len(img_data) - 1)
            out_tag   = "[vout]" if is_last else f"[ov{idx}]"
            # Sabit piksel koordinatları
            ox = int(round(a.x_px * vid_w / REF_W))
            oy = int(round(a.y_px * vid_h / REF_H))
            ow = max(2, int(round(a.w_px * vid_w / REF_W)))
            oh = max(2, int(round(a.h_px * vid_h / REF_H)))
            # Opacity için colorchannelmixer kullan (overlay alpha parametresi yok)
            if a.opacity < 0.99:
                ch_tag = f"ch{idx}"
                movie_parts.append(
                    f"movie='{safe_path}':loop=0[{im_tag}_raw];"
                    f"[{im_tag}_raw]scale={ow}:{oh},"
                    f"colorchannelmixer=aa={a.opacity:.3f}[{im_tag}]"
                )
            else:
                movie_parts.append(
                    f"movie='{safe_path}':loop=0[{im_tag}_raw];"
                    f"[{im_tag}_raw]scale={ow}:{oh}[{im_tag}]"
                )
            overlay_parts.append(
                f"[{prev_label}][{im_tag}]overlay="
                f"x={ox}:y={oy}:shortest=0:eof_action=repeat:{enable}{out_tag}"
            )
            if not is_last:
                prev_label = f"ov{idx}"

        img_chain = ";".join(movie_parts + overlay_parts)
        result.append(img_chain)

    result.extend(simple_parts)
    return result


# ──────────────────────────────────────────────────────────────
#  UI DİYALOĞU — Piksel tabanlı giriş
# ──────────────────────────────────────────────────────────────
PREVIEW_W = 384   # 1920 / 5
PREVIEW_H = 216   # 1080 / 5
SCALE     = PREVIEW_W / REF_W  # 0.2

class AssetEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save, existing=None):
        super().__init__(parent)
        self.on_save = on_save
        is_edit = existing is not None

        self.title("Şekil / Görsel Düzenle" if is_edit else "Şekil / Görsel Ekle")
        self.geometry("560x640")
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
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.grab_set()
        self.configure(fg_color="#161b22")

        # Başlık
        ctk.CTkLabel(self,
                     text="✏️ Varlık Düzenle" if is_edit else "🎨 Varlık Ekle",
                     font=ctk.CTkFont("Arial", 15, "bold"),
                     text_color="#e6edf3").pack(pady=(12, 6))

        # ── Tip seçimi ──────────────────────────────────────────
        self.type_var = ctk.StringVar(value=existing.type if is_edit else "rect")
        type_f = ctk.CTkFrame(self, fg_color="transparent")
        type_f.pack(fill="x", padx=16, pady=4)
        for t, txt in [("rect","⬜ Dikdörtgen"),("circle","⭕ Daire"),
                        ("line","📏 Çizgi"),("image","🖼️ Görsel")]:
            ctk.CTkRadioButton(type_f, text=txt, variable=self.type_var, value=t,
                               text_color="#e6edf3",
                               command=self._on_type_change).pack(side="left", padx=6)

        # ── Görsel yolu ─────────────────────────────────────────
        self.path_var = ctk.StringVar(value=existing.path if is_edit else "")
        self.path_entry = ctk.CTkEntry(self, textvariable=self.path_var,
                                       placeholder_text="Görsel yolu (image tipi için)...",
                                       state="disabled")
        self.path_entry.pack(fill="x", padx=16, pady=(4,2))
        self.btn_pick = ctk.CTkButton(self, text="📂 Görsel Seç",
                                      command=self._pick_image, fg_color="#1f538d", height=28)
        self.btn_pick.pack(fill="x", padx=16, pady=(0,6))

        # ── Piksel giriş alanları ───────────────────────────────
        grid = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=8)
        grid.pack(fill="x", padx=16, pady=4)

        def _px_field(parent, label, var, max_val, row, col):
            ctk.CTkLabel(parent, text=label, text_color="#8b949e",
                         font=ctk.CTkFont("Arial", 11)).grid(row=row, column=col*2,
                         padx=(12,4), pady=5, sticky="e")
            e = ctk.CTkEntry(parent, textvariable=var, width=80,
                             font=ctk.CTkFont("Arial", 11))
            e.grid(row=row, column=col*2+1, padx=(0,12), pady=5, sticky="w")
            ctk.CTkLabel(parent, text="px", text_color="#444",
                         font=ctk.CTkFont("Arial", 10)).grid(row=row, column=col*2+1,
                         padx=(65,0), pady=5, sticky="w")
            return e

        def _iv(existing_val, default):
            return str(int(existing_val)) if is_edit else str(default)

        self.x_var = ctk.StringVar(value=_iv(existing.x_px if is_edit else 0, 100))
        self.y_var = ctk.StringVar(value=_iv(existing.y_px if is_edit else 0, 100))
        self.w_var = ctk.StringVar(value=_iv(existing.w_px if is_edit else 0, 400))
        self.h_var = ctk.StringVar(value=_iv(existing.h_px if is_edit else 0, 200))

        _px_field(grid, "X (sol):",    self.x_var, REF_W, 0, 0)
        _px_field(grid, "Y (üst):",    self.y_var, REF_H, 0, 1)
        _px_field(grid, "Genişlik:",   self.w_var, REF_W, 1, 0)
        _px_field(grid, "Yükseklik:",  self.h_var, REF_H, 1, 1)

        ctk.CTkLabel(grid, text=f"Referans çözünürlük: {REF_W}×{REF_H}",
                     text_color="#444", font=ctk.CTkFont("Arial", 9)
                     ).grid(row=2, column=0, columnspan=4, pady=(0,6))

        # Değiştiğinde önizlemeyi güncelle
        for v in (self.x_var, self.y_var, self.w_var, self.h_var):
            v.trace_add("write", lambda *_: self._update_preview())

        # ── Mini önizleme canvas ────────────────────────────────
        prev_outer = ctk.CTkFrame(self, fg_color="#0d1117", corner_radius=8)
        prev_outer.pack(padx=16, pady=4)
        ctk.CTkLabel(prev_outer, text=f"Önizleme  (1:{int(1/SCALE)})",
                     text_color="#8b949e", font=ctk.CTkFont("Arial", 10)
                     ).pack(pady=(4,2))
        import tkinter as tk
        self._canvas = tk.Canvas(prev_outer, width=PREVIEW_W, height=PREVIEW_H,
                                 bg="#1a1a2e", highlightthickness=1,
                                 highlightbackground="#30363d")
        self._canvas.pack(padx=8, pady=(0,8))

        # ── Zaman ───────────────────────────────────────────────
        t_f = ctk.CTkFrame(self, fg_color="transparent")
        t_f.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(t_f, text="Başlangıç:", text_color="#8b949e").pack(side="left")
        self.t0_var = ctk.StringVar(value=str(existing.start_time) if is_edit else "0.0")
        ctk.CTkEntry(t_f, textvariable=self.t0_var, width=65).pack(side="left", padx=4)
        ctk.CTkLabel(t_f, text="sn    Bitiş:", text_color="#8b949e").pack(side="left", padx=(4,0))
        self.t1_var = ctk.StringVar(value=str(existing.end_time) if is_edit else "5.0")
        ctk.CTkEntry(t_f, textvariable=self.t1_var, width=65).pack(side="left", padx=4)
        ctk.CTkLabel(t_f, text="sn", text_color="#8b949e").pack(side="left")

        # ── Renk, Kalınlık, Opaklık ─────────────────────────────
        c_f = ctk.CTkFrame(self, fg_color="transparent")
        c_f.pack(fill="x", padx=16, pady=4)
        init_color = existing.color if is_edit else "#ff0000"
        self.col_var = ctk.StringVar(value=init_color)
        self.col_btn = ctk.CTkButton(c_f, text="🎨 Renk", width=80, height=28,
                                     command=self._pick_color,
                                     fg_color=init_color, text_color="#000")
        self.col_btn.pack(side="left")
        ctk.CTkLabel(c_f, text="Kalınlık:", text_color="#8b949e").pack(side="left", padx=(10,4))
        self.thick_var = ctk.StringVar(value=str(existing.thickness if is_edit else 3))
        ctk.CTkEntry(c_f, textvariable=self.thick_var, width=50).pack(side="left")
        ctk.CTkLabel(c_f, text="px", text_color="#444").pack(side="left", padx=(2,12))
        # Opaklık (image için)
        self.opacity_lbl = ctk.CTkLabel(c_f, text="Opaklık:", text_color="#8b949e")
        self.opacity_lbl.pack(side="left", padx=(0,4))
        self.opacity_var = ctk.StringVar(value=f"{existing.opacity:.2f}" if is_edit else "1.00")
        self.opacity_entry = ctk.CTkEntry(c_f, textvariable=self.opacity_var, width=50)
        self.opacity_entry.pack(side="left")

        # ── Kaydet ─────────────────────────────────────────────
        ctk.CTkButton(self, text="💾 Güncelle" if is_edit else "💾 Timeline'a Ekle",
                      height=38, fg_color="#238636", hover_color="#1a6e2a",
                      font=ctk.CTkFont("Arial", 13, "bold"),
                      command=self._save).pack(fill="x", padx=16, pady=12)

        self._on_type_change()
        self._update_preview()

    # ── Yardımcılar ─────────────────────────────────────────────
    def _on_type_change(self):
        """Image seçilince görsel butonu aktif olur."""
        is_img = self.type_var.get() == "image"
        self.btn_pick.configure(state="normal" if is_img else "disabled",
                                fg_color="#1f538d" if is_img else "#2a2a2a")
        self.opacity_lbl.configure(text_color="#8b949e" if is_img else "#333")
        self.opacity_entry.configure(state="normal" if is_img else "disabled")
        self._update_preview()

    def _update_preview(self):
        """Mini canvas'ta şeklin pozisyonunu göster."""
        c = self._canvas
        c.delete("all")
        # Izgara çizgileri (üçte bir)
        for i in range(1, 3):
            c.create_line(PREVIEW_W*i//3, 0, PREVIEW_W*i//3, PREVIEW_H, fill="#222")
            c.create_line(0, PREVIEW_H*i//3, PREVIEW_W, PREVIEW_H*i//3, fill="#222")
        try:
            x  = int(self.x_var.get()) * SCALE
            y  = int(self.y_var.get()) * SCALE
            w  = max(2, int(self.w_var.get()) * SCALE)
            h  = max(2, int(self.h_var.get()) * SCALE)
            col = self.col_var.get()
            t   = self.type_var.get()
            if t == "rect":
                c.create_rectangle(x, y, x+w, y+h, outline=col, width=2)
            elif t == "circle":
                c.create_oval(x, y, x+w, y+h, outline=col, width=2)
            elif t == "line":
                th = max(1, int(self.thick_var.get() or 2)) 
                c.create_rectangle(x, y, x+w, y+th, fill=col, outline="")
            elif t == "image":
                c.create_rectangle(x, y, x+w, y+h, outline=col, dash=(4,2), width=1)
                c.create_text(x+w/2, y+h/2, text="IMG", fill=col,
                              font=("Arial", max(8, int(h/4))))
        except Exception:
            pass

    def _pick_image(self):
        p = filedialog.askopenfilename(
            title="Görsel Seç",
            filetypes=[("Görseller", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if p:
            self.path_var.set(p)

    def _pick_color(self):
        c = colorchooser.askcolor(color=self.col_var.get(), title="Renk Seç")
        if c and c[1]:
            self.col_var.set(c[1])
            self.col_btn.configure(fg_color=c[1])
            self._update_preview()

    def _parse_int(self, var, default, min_val=0, max_val=99999):
        try:
            return max(min_val, min(max_val, int(var.get())))
        except (ValueError, TypeError):
            return default

    def _save(self):
        try:
            t0, t1 = float(self.t0_var.get()), float(self.t1_var.get())
            if t1 <= t0: raise ValueError("Bitiş > Başlangıç olmalı")
        except ValueError as ex:
            return messagebox.showerror("Hata", str(ex))

        x_px = self._parse_int(self.x_var, 100, 0, REF_W)
        y_px = self._parse_int(self.y_var, 100, 0, REF_H)
        w_px = self._parse_int(self.w_var, 400, 1, REF_W)
        h_px = self._parse_int(self.h_var, 200, 1, REF_H)

        try:
            thickness = max(1, int(self.thick_var.get()))
        except (ValueError, TypeError):
            thickness = 3

        try:
            opacity = max(0.0, min(1.0, float(self.opacity_var.get())))
        except (ValueError, TypeError):
            opacity = 1.0

        asset = AssetOverlay(
            overlay_type=self.type_var.get(),
            path=self.path_var.get(),
            x_px=x_px, y_px=y_px, w_px=w_px, h_px=h_px,
            start_time=t0, end_time=t1,
            color=self.col_var.get(), thickness=thickness, opacity=opacity
        )
        self.on_save(asset)
        self.destroy()
