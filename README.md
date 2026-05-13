# CrediSense AI

CrediSense AI; kimlik, maaş bordrosu, banka hesap dökümü ve başvuru formu bilgilerini
kullanarak kredi ön değerlendirmesi yapan katmanlı bir yapay zeka prototipidir.

Bu repo şu anda terminal üzerinden çalışan bir backend çekirdeği içerir. Web arayüzü ve
dosya yükleme ekranları sonraki geliştirme adımlarında eklenecektir.

## Ne İşe Yarar?

Proje örnek belgeler üzerinden şu akışı çalıştırır:

1. PDF dosyalarından metin çıkarır.
2. Belgenin kimlik, maaş bordrosu veya banka hesap dökümü olduğunu anlar.
3. Belgelerden ad soyad, kimlik numarası, maaş, IBAN ve işlem satırları gibi alanları çıkarır.
4. Belgeler arası tutarlılık kontrolü yapar.
5. Banka hareketlerinden gelir, gider, bakiye ve harcama/gelir oranı gibi finansal özellikler üretir.
6. Baseline formül veya eğitimli model ile risk skoru hesaplar.
7. Sonucu terminale basar, istenirse JSON ve Markdown raporu üretir.

## Proje Klasörleri

| Yol | Açıklama |
|---|---|
| `backend/credisense` | Ana Python kodları ve analiz katmanları |
| `ornek_belgeler` | Çalıştırmaya hazır sentetik PDF belgeleri ve örnek başvuru formu |
| `veri` | Küçük sentetik veri seti ve veri klasörü açıklamaları |
| `modeller` | Eğitimden sonra oluşacak model dosyalarının yeri |
| `raporlar` | Analiz sonrası oluşacak raporların yeri |
| `dokumanlar` | Veri seti, model ve başvuru formu notları |
| `tests` | Otomatik testler |

## Gereksinimler

Başlamadan önce bilgisayarda şunlar olmalı:

- Python 3.10 veya üzeri
- Git
- Windows PowerShell, Windows Terminal veya benzer bir terminal

## Kurulum

Aşağıdaki komutları repo kök klasöründe çalıştırın. Repo kökü, bu `README.md` dosyasının
bulunduğu klasördür.

Örnek:

```powershell
cd C:\Users\bessi\Desktop\credisenseai\CrediSense-AI
```

Sanal ortam oluşturun:

```powershell
python -m venv .venv
```

Sanal ortamı aktif edin:

```powershell
.\.venv\Scripts\Activate.ps1
```

Terminal satırının başında `(.venv)` görürseniz sanal ortam aktiftir.

Bağımlılıkları kurun:

```powershell
python -m pip install -r requirements.txt
```

Kurulumdan sonra testleri çalıştırın:

```powershell
python -m pytest
```

Beklenen çıktı şu şekildedir:

```text
17 passed
```

## İlk Çalıştırma

Örnek kimlik, maaş bordrosu, banka hesap dökümü ve başvuru formuyla tam analizi çalıştırmak için:

```powershell
python -B -m backend.credisense.terminal `
  "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" `
  "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" `
  --form "ornek_belgeler\ornek_basvuru_formu.json"
```

Bu komut iki şey yapar:

- Terminale analiz sonucunu JSON olarak basar.
- `raporlar` klasörüne `.json` ve `.md` rapor dosyaları üretir.

Sadece terminal çıktısı almak, rapor dosyası üretmemek için:

```powershell
python -B -m backend.credisense.terminal `
  "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" `
  "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" `
  --form "ornek_belgeler\ornek_basvuru_formu.json" `
  --no-report
```

## Çıktıda Neye Bakılır?

Analiz çıktısında en önemli alanlar şunlardır:

| Alan | Anlamı |
|---|---|
| `documents` | PDF'lerden çıkarılan belge alanları |
| `document_quality` | Her PDF için belge türü, güven skoru, eksik alanlar ve PDF okuma bilgisi |
| `features` | Risk hesabına giren sayısal özellikler |
| `consistency` | Belgelerin birbirleriyle uyumu ve anomali uyarıları |
| `risk.risk_score` | 0 ile 1 arasında risk skoru |
| `risk.risk_level` | `Düşük`, `Orta` veya `Yüksek` risk etiketi |
| `risk.decision_summary.decision_code` | Ön onay, uzman incelemesi veya detaylı inceleme kararı |
| `risk.decision_source` | Kararın baseline formülden mi eğitimli modelden mi geldiği |

Eğer `decision_source` alanı `baseline_formula` ise sistem eğitimli model dosyası olmadan
açıklanabilir formülle karar üretmiştir. Bu normaldir; repo model dosyasını bilerek taşımaz.

## Model Eğitimi

Model eğitimi için büyük ham veri setleri GitHub'a eklenmez. Bu nedenle ilk kurulumdan sonra
eğitim komutu doğrudan çalışmayabilir. Önce ham veri setlerinin `veri/kaynak_veri_setleri`
altına yerleştirilmesi veya indirme/dönüştürme akışının tamamlanması gerekir.

Varsayılan eğitim akışı:

```powershell
python -B -m backend.credisense.veri_seti_donustur --dataset all
python -B -m backend.credisense.model_egitimi
```

Eğitim başarılı olursa şu dosyalar oluşur:

| Dosya | Açıklama |
|---|---|
| `modeller/risk_modeli.pkl` | Eğitimli model ve beklenen kolon listesi |
| `modeller/risk_modeli_sonuclari.json` | Model karşılaştırma metrikleri |

Bu dosyalar `.gitignore` ile hariç tutulur.

## Sık Karşılaşılan Sorunlar

`python` komutu bulunamıyor:

Python kurulu değildir veya PATH'e eklenmemiştir. Windows'ta `py --version` komutunu da
deneyebilirsiniz.

PowerShell sanal ortamı aktifleştirmeye izin vermiyor:

Şu komutu bir kez çalıştırıp terminali yeniden açın:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

`No module named pytest` hatası:

Sanal ortam aktif değil veya bağımlılıklar kurulmamıştır. Şunları tekrar çalıştırın:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Başvuru formu bulunamadı hatası:

Komuttaki `--form` yolu yanlış olabilir. Örnek form şu yoldadır:

```text
ornek_belgeler\ornek_basvuru_formu.json
```

Model dosyası bulunamadı mesajı:

Bu hata değil, beklenen davranıştır. `modeller/risk_modeli.pkl` yoksa final karar baseline
formülden üretilir.

## API Olarak Çalıştırma

Terminal kullanmadan HTTP API üzerinden analiz yapmak için FastAPI servisini başlatabilirsiniz.

Önce sanal ortamın aktif olduğundan emin olun:

```powershell
.\.venv\Scripts\Activate.ps1
```

Servisi başlatın:

```powershell
python -m uvicorn backend.credisense.api:app --reload
```

Beklenen adresler:

| Adres | Açıklama |
|---|---|
| `http://127.0.0.1:8000/health` | Servisin çalışıp çalışmadığını kontrol eder. |
| `http://127.0.0.1:8000/docs` | Swagger arayüzünü açar. Buradan dosya yükleyerek test yapılabilir. |

Sağlık kontrolü örneği:

```powershell
curl http://127.0.0.1:8000/health
```

Swagger ekranından analiz yapmak için:

1. Tarayıcıda `http://127.0.0.1:8000/docs` adresini açın.
2. `POST /analyze` bölümünü genişletin.
3. `documents` alanına üç örnek PDF dosyasını ekleyin.
4. `application_form` alanına `ornek_belgeler\ornek_basvuru_formu.json` içeriğini yapıştırın.
5. Rapor dosyası da oluşsun istiyorsanız `create_report` değerini `true` yapın.
6. `Execute` butonuna basın.

API de terminal ile aynı analiz motorunu kullanır. Bu yüzden JSON çıktısındaki ana alanlar aynıdır:
`analysis_id`, `documents`, `document_quality`, `features`, `consistency`, `risk` ve
`dataset_summary`.

`create_report=true` ile analiz yaptıysanız cevapta `report_files` alanı döner. Aynı raporları API
üzerinden indirmek için:

```text
http://127.0.0.1:8000/reports/{analysis_id}/json
http://127.0.0.1:8000/reports/{analysis_id}/md
```

Analiz sonucu varsayilan olarak yerel basvuru deposuna kaydedilir. Bu depo urun akisi icin
basvuru takibi ve banka karari isleme amaciyla kullanilir:

```text
http://127.0.0.1:8000/applications
http://127.0.0.1:8000/applications/{application_id}
http://127.0.0.1:8000/applications/{application_id}/decision
```

`POST /applications/{application_id}/decision` endpoint'i su karar tiplerini destekler:
`approve`, `reject`, `request_extra_document`, `send_to_deep_review`.

Kredi onaylandiktan sonra odeme plani ve odeme asistani endpoint'leri kullanilir:

```text
http://127.0.0.1:8000/applications/{application_id}/payment-plan
http://127.0.0.1:8000/payment-plans
http://127.0.0.1:8000/payment-plans/{loan_id}
http://127.0.0.1:8000/payment-plans/{loan_id}/installments/{installment_no}
http://127.0.0.1:8000/payment-plans/{loan_id}/assistant
```

Odeme asistani `question_type` ile kontrollu soru alabilir veya `message` alanindaki serbest metni
basit kurallarla siniflandirabilir. Desteklenen soru tipleri: `summary`, `next_payment`,
`payment_status`, `remaining_debt`, `early_payment`, `late_payment`, `overdue_payments`,
`change_due_date`. Odeme planlari varsayilan olarak `veri/odeme_planlari.db` SQLite dosyasinda
tutulur.

Basvuru kayitlari varsayilan olarak `veri/basvuru_kayitlari.db` SQLite dosyasinda tutulur.

Örnek:

```text
http://127.0.0.1:8000/reports/ANALIZ_ID_BURAYA/md
```

API hata cevapları şu formatta döner:

```json
{
  "error": {
    "code": "bad_request",
    "message": "Başvuru formu JSON nesnesi olmalı."
  }
}
```

## Geliştirme Komutları

Testleri çalıştır:

```powershell
python -m pytest
```

Python dosyalarının derlenebilir olduğunu kontrol et:

```powershell
python -m compileall backend tests
```

Sadece PDF okuma katmanını dene:

```powershell
python -m backend.credisense.katman_01_pdf_okuma "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf"
```

## Mevcut Sınırlar

- PDF okuma katmanı önce `PyMuPDF` kullanır, metin çıkarılamazsa yerel okuyucuya düşer.
- Her belge için `document_quality` alanında `confidence`, `missing_fields` ve `warnings` döner.
- Taranmış veya tamamen görsel tabanlı belgeler için OCR hâlâ gereklidir.
- Farklı banka/kimlik/bordro formatlarında alan çıkarma kuralları genişletilmelidir.
- Web arayüzü henüz yoktur.
- Eğitimli model dosyası repoda tutulmaz.
- Bu proje gerçek kredi kararı vermek için değil, prototip ve geliştirme çalışması için hazırlanmıştır.

Sonraki geliştirme planı için [ROADMAP.md](ROADMAP.md) dosyasına bakabilirsiniz.
