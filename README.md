# FJS-12 — Forgotten Joint Score Web Uygulaması

Doç. Dr. Özgür Karakoyun için diz protezi, kalça protezi ve osseointegrasyon
hastalarının takibinde kullanılmak üzere geliştirilen çok dilli FJS-12 anketi.

## Özellikler

- **4 prosedür tipi:** Diz protezi, kalça protezi, osseointegrasyon, soketli protez
- **4 dil:** Türkçe, İngilizce, Arapça (RTL), Bulgarca
- **Tek/çift taraf desteği:** Çift taraf seçilirse her soru sağ ve sol için ayrı yanıtlanır, iki ayrı FJS skoru hesaplanır
- **Prosedüre göre dinamik form:**
  - Diz/kalça → ameliyat tarihi (ay+yıl)
  - Osseointegrasyon → osseointegrasyon ameliyat tarihi + amputasyon yılı + amputasyon düzeyi
  - Soketli protez → amputasyon tarihi (ay+yıl) + amputasyon düzeyi
- **Prosedüre göre dinamik soru tanıtımı** (eklem / implant / protez)
- **Otomatik FJS-12 skoru** (0–100, yüksek = daha iyi)
- **Admin paneli:** Tüm yanıtları görüntüleme + CSV dışa aktarma
- **Yazdırılabilir** sonuç sayfası
- **Railway** üzerinde tek tıkla deploy edilebilir
- **KVKK uyumu:** Telefon dahil iletişim bilgisi alınmaz, sadece ad+yaş+klinik veri saklanır

---

## Yerel kurulum

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Tarayıcıdan `http://localhost:5000` açın.

---

## Railway'e Deploy

### 1. Repository hazırlığı
Bu klasörü bir GitHub repository'ye yükleyin:
```bash
git init
git add .
git commit -m "FJS-12 initial"
git remote add origin git@github.com:YOUR_USERNAME/fjs-app.git
git push -u origin main
```

### 2. Railway'de proje oluşturma
1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Bu repo'yu seçin. Railway, `Procfile` ve `railway.json`'u otomatik tanır.

### 3. Environment variables (Variables sekmesi)

| Değişken | Önerilen değer | Not |
|---|---|---|
| `SECRET_KEY` | (rastgele 32+ karakter) | Flask session güvenliği için zorunlu |
| `ADMIN_PASSWORD` | (güçlü bir parola) | `/admin` paneli için |
| `DB_PATH` | `/data/fjs.db` | Volume kullanılıyorsa |

**`SECRET_KEY` üretmek için:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Volume ekleme (KRİTİK — yoksa veriler kaybolur)
Railway her deploy'da dosya sistemini sıfırlar. SQLite verilerinin kalıcı olması için:

1. Servis sayfasında **Settings → Volumes → New Volume**
2. Mount path: `/data`
3. `DB_PATH=/data/fjs.db` env variable'ını yukarıdaki gibi ayarladığınızdan emin olun
4. Servisi yeniden deploy edin

### 5. Domain bağlama
- **Settings → Networking → Generate Domain** (Railway alt domain) veya
- **Custom Domain** ekleyip DNS CNAME'i Railway'in verdiği adrese yöneltin

---

## Kullanım

| URL | İşlev |
|---|---|
| `/` | Karşılama, dil seçimi |
| `/start` | Hasta bilgileri formu |
| `/questions` | FJS-12 soruları |
| `/result/<id>` | Sonuç sayfası |
| `/admin/login` | Yönetici girişi |
| `/admin` | Tüm yanıtlar |
| `/admin/export.csv` | CSV indirme |
| `/healthz` | Sağlık kontrolü |

---

## FJS-12 Skorlama

- Her soru 0–4 arası puanlanır (0 = Hiçbir zaman, 4 = Çoğu zaman)
- Toplam ham puan: 0–48
- **FJS-12 = (1 − ham/48) × 100** → 0–100 arası
- **Yüksek puan = daha iyi sonuç** (eklem daha az fark ediliyor)
- En az 9/12 soru cevaplanmalı (uygulama 12'sini de zorunlu tutar)

Çift taraf hastalarda sağ ve sol için iki ayrı skor hesaplanır.

---

## Referans

Behrend H, Giesinger K, Giesinger JM, Kuster MS. The "Forgotten Joint" as the
ultimate goal in joint arthroplasty: validation of a new patient-reported
outcome measure. *J Arthroplasty.* 2012;27(3):430–436.

---

## Lisans

Klinik kullanım için. FJS-12 anketi telif hakkı © Behrend ve ark., 2012.
