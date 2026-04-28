# 🎬 Aptoza Screen Recorder Pro

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![UI](https://img.shields.io/badge/UI-CustomTkinter-purple)
![FFmpeg](https://img.shields.io/badge/Powered%20by-FFmpeg-orange)

**Çizim, Ses Efektleri, Webcam ve Görsel-Video Dönüşümünü Tek Uygulamada Birleştiren Gelişmiş Ekran Kaydedici**

</div>

---

## 📸 Windows Kurulum

---

---

https://github.com/user-attachments/assets/3c15b9af-b437-414a-8b5a-b25421670967

---

---

## 📸 Genel Bakış
---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7787c870-5ee8-4675-81b6-aaa05df0d2cd" />

---

**Aptoza Screen Recorder Pro**, Python ile geliştirilmiş kapsamlı bir masaüstü ekran kaydedici uygulamasıdır. Temel kayıt özelliklerinin çok ötesine geçerek; canlı çizim/anotasyon katmanı, webcam PiP (Picture-in-Picture) desteği, tam özellikli ses efektleri stüdyosu ve görselden video dönüştürücü modüllerini tek bir çatı altında sunar.

GitHub'ın koyu renk temasından ilham alan arayüzü ve CollapsibleSection tabanlı duyarlı düzeni ile hem profesyonel hem de gündelik kullanıma uygundur.

---

## ✨ Özellikler

---

https://github.com/user-attachments/assets/0d17d1ff-aa74-4c0a-8244-50155869723a

---
### 🎥 Ekran Kaydı

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/fc5cd73b-925a-4f12-b17e-f867284d4c02" />

---
- **Tam Ekran veya Bölge Seçimi** — Mouse sürükleyerek piksel hassasiyetle kayıt alanı belirleyin
- **Ayarlanabilir FPS** — İhtiyaca göre kare hızı kontrolü
- **CRF Kalite Kontrolü** — Dosya boyutu / kalite dengesini yönetin
- **FFmpeg Pipe** — `ultrafast` preset ile gerçek zamanlı H.264 kodlama; FFmpeg yoksa OpenCV fallback
- **Duraklat / Devam** — Kayıt süresini etkilemeden durdurma/devam etme
- **Otomatik Dosya Adlandırma** — `kayit_YYYYMMDD_HHMMSS.mp4` formatında zaman damgalı dosyalar
- **Çıktı Klasörü Seçimi** — Kayıt konumunu serbestçe belirleyin

### 📷 Webcam Entegrasyonu (PiP)
- **Picture-in-Picture (PiP)** — Webcam görüntüsünü kayda gömün
- **4 Konum Seçeneği** — `top-left`, `top-right`, `bottom-left`, `bottom-right`
- **Gölge ve Kenarlık Efekti** — Profesyonel görünüm için çerçeve ve gölge
- **Ayarlanabilir PiP Boyutu** — Küçük overlay'den büyük ekrana kadar esnek boyutlandırma
- **Canlı Webcam Önizleme** — Kayıt sırasında ayrı kayan pencerede gerçek zamanlı önizleme
- **Çoklu Kamera Desteği** — Kamera indeksi seçimi (0, 1, 2…)
- **Thread-safe Stream** — `WebcamVideoStream` sınıfı ile bağımsız okuma döngüsü

### 🖌️ Çizim ve Anotasyon Katmanı
---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/b54e1b8a-417f-410d-9de2-482c74c0514e" />

---

- **8 Çizim Aracı** — Fare imleci, dikdörtgen, daire, ok, çizgi, serbest çizim, metin, silgi
- **Kayan Araç Paneli** — Her zaman üstte duran bağımsız araç çubuğu penceresi
- **Şeffaf Overlay** — Ekranın üzerinde çizim yaparken altta çalışan uygulamaları etkilemez
- **Renk ve Kalınlık Kontrolü** — Renk seçici + 1–15 px kalınlık slider'ı
- **Tek Tıkla Temizle** — Tüm çizim katmanını sıfırla
- **Çizim Modu Kısayolu** — Hotkey ile çizimi hızlıca etkinleştir/devre dışı bırak

### 🔍 Zoom (Büyütme)

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/5c807859-6040-4b9d-97ba-b84ddd1dd058" />

---

- **1.0×–4.0× Anlık Zoom** — Kayıt sırasında fareyi takip ederek ekrana yakınlaştırma
- **Gerçek Zamanlı Uygulama** — Kayda anında yansır, performansı düşürmez

### 🖱️ İmleç Vurgusu
---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/b1a5e8c9-b2ca-4cac-b026-bd521779d17a" />

---
- **Özelleştirilebilir İmleç Dairesi** — Renk ve boyutu ayarlanabilir görsel vurgulama efekti

### 💧 Filigran (Watermark)

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/052f1f48-db04-4660-8416-2732dc205383" />

---

- **Metin Filigranı** — Font boyutu, opaklık ve konum ayarlı metin ekleme
- **Görsel Filigran** — PNG/JPG logo veya marka görseli bindirme
- **5 Konum** — `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center`
- **Opaklık Kontrolü** — 0–100% arası şeffaflık ayarı

### ⏰ Zamanlanmış Kayıt

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/49298bab-f242-4620-a6f5-8430ac22951f" />

---

- **Başlangıç/Bitiş Saati** — Belirtilen saatle otomatik kayıt başlatma/durdurma
- **Arka Plan İzleyici** — Uyku modunu engellemez; daemon thread ile çalışır

### ⌨️ Global Kısayol Tuşları

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7a611387-303c-4d92-946a-d0f65005b5b0" />

---

- **5 Eyleme Atama** — Kayıt başlat, duraklat, durdur, ekran görüntüsü, çizim modu
- **`pynput` ile Global** — Uygulama odakta olmasa bile çalışır
- **Canlı Yakalama** — Diyalog kutusuyla anlık tuş ataması
- **Ayarlara Kaydedilir** — Oturumlar arası kısayollar korunur

### 📸 Ekran Görüntüsü

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/3381aeb3-7bab-4748-95fd-a830052dc0e0" />

---

- **Tek Tuşla Screenshot** — Mevcut ekranı PNG olarak kaydet

### ✂️ Video Düzenleme Araçları

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/2f2130ae-acf6-4af1-9670-dce1df6134d7" />

---

- **Kırpma (Trim)** — Başlangıç/bitiş saniyesi girerek video kesme
- **Birleştirme (Merge)** — Birden fazla videoyu sırayla tek dosyaya birleştirme
- **Format Dönüştürme** — MP4, AVI, MKV, MOV, WebM çıktı desteği
- **Süre Okuma** — Kaynak videonun toplam süresini otomatik gösterme
- **Thread'li İşlem** — UI donmadan arka planda çalışır

### 💾 Ayarlar
- **JSON Kalıcılığı** — `~/.ekran_kayit_pro.json` dosyasında tüm ayarlar saklı
- **Oturumlar Arası Bellek** — FPS, kalite, kısayollar ve çıktı klasörü hatırlanır

---

## 🎛️ Ses Efektleri Stüdyosu (`AudioEffectsModule.py`)

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/d82eb9af-a08a-4617-af0d-9107e852fde7" />

---

Bağımsız bir modül olarak dahil edilen ses efektleri stüdyosu, FFmpeg filtre zinciri oluşturarak ses dosyalarını profesyonel düzeyde işlemenizi sağlar.

### Profesyonel İyileştirmeler
| Özellik | Açıklama |
|---|---|
| Otomatik Normalizasyon | `loudnorm` filtresi — I=-16 LUFS hedef seviyesi |
| Gürültü Temizleme | `afftdn=nf=-25` — Arka plan gürültüsünü azaltır |
| Kompresör | `acompressor` — Ses patlamalarını önler |
| Sessizlik Silme | `silenceremove` — Boş kısımları otomatik kaldırır |
| Mono → Stereo | Pan filtresi ile mono sesi stereo kanala kopyalar |

### Ekolayzer & Frekans Filtreleri
- **Bass / Treble** — Alçak ve yüksek frekans gain ayarı (dB)
- **High-Pass / Low-Pass** — Bant geçiren filtreler
- **Panning** — Sol/Sağ kanal dengesi (−1.0 ile +1.0)
- **Vokal Silici** — Faz iptali tekniğiyle karaoke efekti

### Yaratıcı Efektler
- **Pitch (Ses Tonu)** — 0.5×–2.0× arası kalın/ince ses ayarı
- **Tempo / Hız** — Tonu bozmadan hızlandır/yavaşlat
- **Echo** — Yankı ve derinlik efekti
- **Reverse** — Sesi tersine çevir

### Audacity Tarzı Modülasyonlar
- **Chorus** — Koro efekti
- **Flanger** — Metalik faz efekti
- **Tremolo** — Ses titremesi (5 Hz)
- **Vibrato** — Ton titremesi (7 Hz)

### Geçişler ve Diğer
- **Fade In / Fade Out** — Saniye cinsinden yavaşça giriş/çıkış
- **Dalga Formu Görselleştirme** — FFmpeg `showwavespic` ile gerçek zamanlı waveform
- **Önizleme** — Pygame ile 45 saniyelik anlık önizleme
- **Toplu İşlem** — Birden fazla dosyayı aynı anda işle
- **Çoklu Format** — MP3, WAV, AAC, M4A çıktı desteği

---

## 🖼️ Görsel → Video Dönüştürücü (`ImageToVideoModule.py`)

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/beed65de-2d3c-4e43-a0a9-e8cd87422dfd" />

---

Fotoğraflardan slayt gösterisi tarzı videolar oluşturmak için eksiksiz bir editör.

### Temel Özellikler
- **Sürükle-Bırak Görseli Sırası** — Her görsel için bağımsız süre ayarı
- **Çözünürlük Seçimi** — 1080p, 720p, 480p veya özel boyut
- **Gerçek Zamanlı Efekt Önizlemesi** — Her ayar değişikliğinde anlık güncelleme
- **FFmpeg Tabanlı Render** — Geçici klipler oluşturulup birleştirilir

### Per-Görsel Efekt Zinciri

---

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/8a097bb6-2c6d-4c5a-9b59-6ef315ecf4c2" />

---

**Renk Ayarları**
- Parlaklık, Kontrast, Doygunluk, Gama, Ton (Hue)

**Görsel Filtreler**
- Bulanıklık (Blur), Siyah Beyaz, Sepya, Kırmızı Filtre, Mavi Filtre
- Vignette (Karartma), Keskinleştirme, Renk Ters Çevirme

**Geometri**
- Yatay Ayna, Dikey Çevirme, 90° Sağa Döndürme

**Geçişler**
- Fade In / Fade Out (saniye cinsinden)

---

## 🚀 Kurulum

### Ön Koşullar

1. **Python 3.8 veya üstü**
2. **FFmpeg** — Sisteminize kurulu ve PATH'e eklenmiş olmalıdır

   ```bash
   # Windows (winget)
   winget install Gyan.FFmpeg

   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg
   ```

3. **FFmpeg kurulumunu doğrulayın:**
   ```bash
   ffmpeg -version
   ```

### Python Bağımlılıklarını Yükleyin

```bash
pip install -r requirements.txt
```

### Uygulamayı Başlatın

```bash
python main.py
```

> **Not:** Windows kullanıcıları için `AQ2.ico` dosyası çalışma dizininde bulunmalıdır (ikon için). Yoksa uygulama çalışmaya devam eder, yalnızca araç paneli ikonu gösterilmez.

---

## 📁 Proje Yapısı

```
EkranKayitPro/
│
├── main.py                  # Ana uygulama — UI + Kayıt Motoru
├── AudioEffectsModule.py    # Ses efektleri stüdyosu modülü
├── ImageToVideoModule.py    # Görsel → Video dönüştürücü modülü
├── requirements.txt         # Python bağımlılıkları
├── AQ2.ico                  # Uygulama ikonu (isteğe bağlı)
└── README.md
```

---

## 🖥️ Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---|---|---|
| İşletim Sistemi | Windows 10, macOS 11, Ubuntu 20.04 | Windows 11, macOS 13+ |
| Python | 3.8 | 3.11+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 500 MB (geçici dosyalar dahil) | 2 GB+ |
| GPU | — | H.264 hızlandırma için desteklenen GPU |

---

## ⚙️ Yapılandırma

Uygulama ayarları `~/.ekran_kayit_pro.json` dosyasında otomatik saklanır:

```json
{
  "output_dir": "C:/Kullanıcılar/Ad/Videolar",
  "fps": 30,
  "quality": 18,
  "cursor_hl": true,
  "cursor_sz": 20,
  "wm_text": "© 2025",
  "wm_pos": "bottom-right",
  "wm_opacity": 0.6,
  "shortcuts": {
    "start": "F9",
    "pause": "F10",
    "stop": "F11",
    "screenshot": "F8",
    "draw": "F7"
  }
}
```

---

## 📦 Modül Mimarisi

```
App (ctk.CTk)
 ├── RecordingEngine            — Ekran/ses kayıt döngüleri, FFmpeg pipe
 │    ├── WebcamVideoStream     — Thread-safe kamera okuyucu
 │    └── VideoEditor           — Kırpma, birleştirme, dönüştürme
 │
 ├── DrawingOverlay             — Şeffaf çizim katmanı (Tkinter Canvas)
 ├── FloatingToolWindow         — Kayan araç & zoom paneli
 ├── WebcamPreviewWindow        — Canlı webcam önizlemesi
 ├── RegionSelector             — Ekran bölgesi seçici
 ├── CollapsibleSection         — Katlanabilir UI bölümleri
 │
 ├── AudioEffectsTab            — Ses efektleri modülü (AudioEffectsModule.py)
 │    └── AudioEffectsEngine    — FFmpeg filtre zinciri oluşturucu
 │
 └── ImageToVideoEditor         — Görsel-video editörü (ImageToVideoModule.py)
```

---

## 🐛 Sorun Giderme

| Sorun | Çözüm |
|---|---|
| `ffmpeg: command not found` | FFmpeg'i yükleyin ve PATH'e ekleyin |
| `pyaudio` kurulum hatası | Windows: `pip install pipwin && pipwin install pyaudio`; Linux: `sudo apt install portaudio19-dev` ardından `pip install pyaudio` |
| Webcam açılmıyor | Kamera indeksini 0'dan 1'e değiştirin; başka bir program kamerayı kilitlemiş olabilir |
| Kayıt donuyor / yavaş | FPS'i düşürün veya FFmpeg kurulu değilse kurun (`ultrafast` preset gereklidir) |
| Hotkey çalışmıyor | `pynput` yüklendiğini doğrulayın; Linux'ta erişim izinleri gerekebilir |
| Çizim araçları görünmüyor | "Araç Paneli" butonuna tıklayın; pencere ekranın dışına çıkmış olabilir |

---

## 🤝 Katkı

1. Bu depoyu fork edin
2. Yeni bir dal oluşturun: `git checkout -b ozellik/yeni-ozellik`
3. Değişikliklerinizi commit edin: `git commit -m 'Yeni özellik: ...'`
4. Dalı push edin: `git push origin ozellik/yeni-ozellik`
5. Pull Request açın

---

## 📄 Lisans

Bu proje MIT Lisansı altında dağıtılmaktadır. Ayrıntılar için `LICENSE` dosyasına bakın.

---

<div align="center">
<sub>Aptoza Screen Recorder Pro — Python ile geliştirilmiş, FFmpeg ile güçlendirilmiş.</sub>
</div>
