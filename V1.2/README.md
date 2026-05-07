# 🎥 EkranKayıt Pro

**EkranKayıt Pro**, Python ile geliştirilmiş, gelişmiş özellikler sunan bir masaüstü ekran kaydedici uygulamasıdır. Modern ve karanlık temalı arayüzü, güçlü video/ses düzenleme modülleri ve esnek yapılandırma seçenekleriyle profesyonel düzeyde ekran kaydı almanızı sağlar.

---

## ✨ Özellikler

### 🖥️ Ekran Kaydı
- Tam ekran veya seçili bölge kaydı
- Ayarlanabilir FPS (kare hızı) ve kalite
- Webcam katmanı (pip - picture-in-picture) desteği
- İmleç vurgulama ve özel imleç rengi
- Zoom (yakınlaştırma) desteği
- Zamanlanmış kayıt (başlangıç/bitiş saati)

### 🎙️ Ses Kaydı ve Efektleri
- Mikrofon ve sistem sesi kaydı
- Gürültü temizleme, normalizasyon, kompresör
- Ekolayzer (bas, tiz, high-pass, low-pass)
- Ses tonu (pitch) ve hız değiştirme
- Yankı, koro, flanger, tremolo, vibrato efektleri
- Fade in / Fade out geçişleri
- Toplu ses dosyası işleme
- Dalga formu önizleme

### 🖼️ Görselden Video Oluşturma
- Birden fazla görseli videolaştırma
- Her görsel için ayrı süre ayarı
- Parlaklık, kontrast, doygunluk, gama, ton ayarları
- Blur, siyah-beyaz, sepya, vignette, keskinleştirme efektleri
- Ayna, döndürme, çevirme dönüşümleri
- Görsel bazında fade in/out
- Gerçek zamanlı önizleme

### ✏️ Ekran Üzerine Çizim
- Kayıt sırasında anlık çizim (annotation) modu
- Dikdörtgen, daire, ok, çizgi, serbest çizim, metin, silgi araçları
- Renk ve boyut ayarı

### 🎬 Video Düzenleme
- Video kırpma (trim)
- Birden fazla videoyu birleştirme (merge)
- Format dönüştürme (MP4, AVI, MKV, MOV, vb.)

### ⚙️ Diğer
- Filigran (metin veya görsel) ekleme
- Ekran görüntüsü (screenshot) alma
- Özelleştirilebilir klavye kısayolları
- Ayarların otomatik kaydı ve yüklenmesi
- Daraltılabilir (collapsible) panel bölümleri

---

## 🗂️ Proje Yapısı

```
.
├── main.py                  # Ana uygulama ve arayüz
├── AudioEffectsModule.py    # Ses efektleri modülü
├── ImageToVideoModule.py    # Görselden video modülü
├── AQ2.ico                  # Uygulama ikonu
├── requirements.txt         # Python bağımlılıkları
└── README.md
```

---

## 🚀 Kurulum

### 1. Gereksinimler
- Python 3.9 veya üzeri
- [FFmpeg](https://ffmpeg.org/download.html) — Sistem PATH'ine eklenmiş olmalıdır

### 2. Python Bağımlılıklarını Kur

```bash
pip install -r requirements.txt
```

### 3. Uygulamayı Başlat

```bash
python main.py
```

---

## 📦 FFmpeg Kurulumu

### Windows
1. https://ffmpeg.org/download.html adresinden indirin
2. `C:\ffmpeg\bin` gibi bir konuma çıkartın
3. Sistem ortam değişkenlerinde `PATH`'e ekleyin

### macOS
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install ffmpeg
```

---

## 💾 Ayarlar

Uygulama ayarları otomatik olarak kullanıcının ev dizinine `~/.ekran_kayit_pro.json` dosyası olarak kaydedilir. Çıkış dizini, FPS, kalite, klavye kısayolları ve filigran bilgileri bu dosyada tutulur.

---

## 🛠️ Geliştirici Notları

- Uygulama `customtkinter` kütüphanesi üzerine inşa edilmiştir; karanlık tema varsayılandır.
- Ses işlemleri `pyaudio` ve `ffmpeg`, video işlemleri `opencv-python` ve `ffmpeg` ile gerçekleştirilir.
- `pynput` kütüphanesi yüklü değilse global klavye kısayolları devre dışı kalır; uygulama çalışmaya devam eder.
- `pygame` yüklü değilse ses önizleme özelliği devre dışı kalır.

---

## 📄 Lisans

Bu proje kişisel ve eğitim amaçlı kullanım için geliştirilmiştir.
