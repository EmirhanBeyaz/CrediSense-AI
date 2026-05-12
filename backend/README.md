# CrediSense AI Backend

Bu klasör CrediSense AI projesinin Python backend çekirdeğini içerir. Şu aşamada backend
bir web servisi değildir; terminal komutlarıyla çalışır.

Ana README'deki kurulum adımlarını tamamlamadan buradaki komutları çalıştırmayın:

```powershell
cd C:\Users\bessi\Desktop\credisenseai\CrediSense-AI
.\.venv\Scripts\Activate.ps1
```

Tüm komutlar repo kök klasöründen çalıştırılmalıdır.

## Katmanlar

| Katman | Dosya | Görev |
|---|---|---|
| 01 | `credisense/katman_01_pdf_okuma.py` | PDF dosyasından metin çıkarır. |
| 02 | `credisense/katman_02_belge_anlama.py` | Belge türünü ve belge alanlarını çıkarır. |
| 03 | `credisense/katman_03_tutarlilik_anomali.py` | Belgeler arası tutarlılık ve anomali kontrolü yapar. |
| 04 | `credisense/katman_04_finansal_ozellikler.py` | Banka hareketlerinden sayısal finansal özellikler üretir. |
| 05 | `credisense/katman_05_risk_tahmini.py` | Risk skoru, risk seviyesi ve karar özeti üretir. |
| Akış | `credisense/analiz_akisi.py` | Bütün katmanları sırayla çalıştırır. |
| CLI | `credisense/terminal.py` | Terminalden analiz başlatır. |
| API | `credisense/api.py` | HTTP üzerinden analiz endpoint'leri sağlar. |

## Tek Tek Deneme Komutları

PDF okuma katmanını dene:

```powershell
python -m backend.credisense.katman_01_pdf_okuma "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf"
```

Belge anlama katmanını dene:

```powershell
python -m backend.credisense.katman_02_belge_anlama "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf"
```

Tutarlılık ve anomali katmanını dene:

```powershell
python -m backend.credisense.katman_03_tutarlilik_anomali `
  "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" `
  "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf"
```

Finansal özellik çıkarımını dene:

```powershell
python -m backend.credisense.katman_04_finansal_ozellikler `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" `
  --payroll-pdf "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf"
```

Tüm analiz akışını çalıştır:

```powershell
python -m backend.credisense.terminal `
  "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" `
  "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" `
  "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" `
  --form "ornek_belgeler\ornek_basvuru_formu.json"
```

## API Kullanımı

FastAPI servisini başlat:

```powershell
python -m uvicorn backend.credisense.api:app --reload
```

Sağlık kontrolü:

```powershell
curl http://127.0.0.1:8000/health
```

Tarayıcıdan test etmek için:

```text
http://127.0.0.1:8000/docs
```

`POST /analyze` endpoint'i multipart form bekler:

| Alan | Tip | Açıklama |
|---|---|---|
| `documents` | PDF dosyaları | Kimlik, maaş bordrosu ve banka hesap dökümü PDF'leri |
| `application_form` | JSON metni | Başvuru formu sözlüğü |
| `use_dataset_summary` | boolean | Sentetik veri seti özetini çıktıya ekler |
| `create_report` | boolean | JSON ve Markdown rapor dosyası üretir |

Başarılı analiz cevabında `analysis_id` döner. `create_report=true` gönderildiyse raporlar şu
endpoint'lerden indirilebilir:

```text
GET /reports/{analysis_id}/json
GET /reports/{analysis_id}/md
```

API hata cevapları şu ortak gövdeyi kullanır:

```json
{
  "error": {
    "code": "bad_request",
    "message": "Hata açıklaması"
  }
}
```

## Geliştirirken Dikkat Edilecekler

- Yeni davranış eklerken `tests` altında test ekleyin.
- Mevcut terminal JSON çıktısındaki ana alanları gereksiz yere değiştirmeyin.
- PDF okuma başarısızsa sistemin bunu raporda açıkça göstermesi gerekir.
- Model dosyası yoksa risk katmanı baseline formülle çalışmaya devam etmelidir.
- Gerçek belge desteği eklenirken sentetik örnek akışı bozulmamalıdır.

## PDF Okuma Davranışı

PDF okuma katmanı önce `PyMuPDF` ile metin çıkarmayı dener. Bu yöntem gerçek PDF yapıları için
yerel okuyucudan daha dayanıklıdır. `PyMuPDF` metin çıkaramazsa veya hata verirse sistem mevcut
yerel okuyucuya düşer.

Katman 01 çıktısında şu alanlar bu davranışı izlemek için kullanılır:

| Alan | Açıklama |
|---|---|
| `extractor` | `pymupdf`, `builtin` veya `none` değerini alır. |
| `warnings` | Fallback veya metin çıkarma sorunlarını listeler. |
| `extraction_ok` | Metin çıkarılıp çıkarılamadığını gösterir. |

Taranmış belgeler ve tamamen görsel içerikli PDF'ler için OCR hâlâ eklenmelidir.

## Belge Kalite Özeti

Tam analiz çıktısında `document_quality` alanı bulunur. Bu alan her PDF için belge anlama
kalitesini gösterir:

| Alan | Açıklama |
|---|---|
| `file_name` | Analiz edilen PDF dosyası |
| `document_type` | `identity`, `payroll`, `bank_statement` veya `unknown` |
| `confidence` | Çıkarılan alanların doluluk oranına göre 0-1 arası skor |
| `missing_fields` | Beklenen ama çıkarılamayan alanlar |
| `warnings` | Belge türü veya alan çıkarma uyarıları |
| `pdf_extraction` | Katman 01 PDF okuma sonucu |

Markdown raporda bu bilgiler `Belge Okuma Kalitesi` başlığı altında gösterilir.

## Bilinen Sınırlar

Risk tahmini iki şekilde çalışabilir:

- `modeller/risk_modeli.pkl` yoksa final karar baseline formülden gelir.
- Model dosyası varsa ve giriş kapsamı yeterliyse final karar eğitimli modelden gelebilir.
