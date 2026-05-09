# CrediSense AI Terminal Backend

Bu klasör, CrediSense AI projesinin arayüzsüz backend çekirdeğini içerir.
Şu aşamada sistem terminal üzerinden çalışır. Web arayüzü ve dosya yükleme ekranları daha sonra eklenecektir.

## Katmanlı Akış

1. PDF belgelerinden metin çıkarılır.
2. Belge türü belirlenir:
   - kimlik
   - maaş bordrosu
   - banka hesap dökümü
3. Belgelerden alanlar çıkarılır.
4. Belgeler arası tutarlılık kontrol edilir.
5. Banka hareketlerinden finansal özellikler üretilir.
6. Baseline formül ve eğitilmiş model ile risk skoru hesaplanır.
7. JSON ve Markdown analiz raporu üretilir.

## Dosya Yapısı

| Dosya | Görev |
|---|---|
| `katman_01_pdf_okuma.py` | PDF belgelerinden metin çıkarır. |
| `katman_02_belge_anlama.py` | Belge türünü tanır ve kimlik/bordro/banka alanlarını çıkarır. |
| `katman_03_tutarlilik_anomali.py` | Belgeler arası tutarlılık ve anomali kontrollerini yapar. |
| `katman_04_finansal_ozellikler.py` | Banka hareketlerinden finansal özellikler üretir. |
| `katman_05_risk_tahmini.py` | Basit ve açıklanabilir risk skoru hesaplar. |
| `analiz_akisi.py` | Tüm katmanları sırayla çalıştırır. |
| `terminal.py` | Terminalden analiz çalıştırmak için giriş noktasıdır. |
| `model_egitimi.py` | İşlenmiş CSV verisiyle risk modeli eğitir. |
| `rapor_uret.py` | Analiz sonucundan JSON ve Markdown rapor üretir. |

## Terminal Kullanımı

Sadece Katman 01 PDF okuma testi:

```powershell
python -m backend.credisense.katman_01_pdf_okuma "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf"
```

Tüm analiz akışı:

```powershell
python -m backend.credisense.terminal `
  "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" `
  "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" `
  --form "ornek_belgeler\ornek_basvuru_formu.json"
```

## Notlar

PDF metin çıkarımı, sentetik Chrome PDF'leri için yazılmış küçük bir çıkarıcıdır. Gerçek belgelerle çalışırken `PyMuPDF`, `pdfplumber`, OCR veya belge anlama modeli eklenmelidir.

Risk skoru hem açıklanabilir baseline formül hem de eğitilmiş Random Forest modeliyle hesaplanabilir. Form verisi yeterliyse final karar modelden gelir; form verisi eksikse baseline karar korunur.
