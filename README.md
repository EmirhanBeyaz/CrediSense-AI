# CrediSense AI

CrediSense AI, finansal belgeler ve başvuru formu verileri üzerinden kredi ön değerlendirmesi yapan katmanlı bir yapay zeka prototipidir.

Sistem şu an terminal üzerinden çalışır. Web arayüzü daha sonraki aşamada eklenecektir.

## Ana Akış

1. PDF belgelerinden metin çıkarılır.
2. Kimlik, maaş bordrosu ve banka hesap dökümü alanları ayrıştırılır.
3. Belgeler arası tutarlılık ve anomali kontrolü yapılır.
4. Banka hareketlerinden finansal özellikler çıkarılır.
5. Başvuru formu verisi modele eklenir.
6. Baseline formül ve eğitilmiş Random Forest modeliyle risk skoru üretilir.
7. JSON ve Markdown başvuru raporu oluşturulur.

## Klasör Yapısı

| Klasör | Açıklama |
|---|---|
| `backend/credisense` | Terminal backend ve katman kodları |
| `ornek_belgeler` | Sentetik PDF belgeleri ve örnek başvuru formu |
| `dokumanlar` | Proje, veri seti ve model notları |
| `veri` | Sentetik küçük veri ve veri klasörü açıklamaları |
| `modeller` | Model çıktıları için yerel klasör |
| `raporlar` | Analiz raporları için yerel klasör |

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Örnek Analiz

```powershell
python -B -m backend.credisense.terminal "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" --form "ornek_belgeler\ornek_basvuru_formu.json"
```

Bu komut terminale analiz sonucunu basar ve `raporlar` klasörüne `.json` ile `.md` rapor üretir.

Rapor üretmeden çalıştırmak için:

```powershell
python -B -m backend.credisense.terminal "ornek_belgeler\Sentetik Kimlik Belgesi Ornegi.pdf" "ornek_belgeler\Sentetik Maas Bordrosu Ornegi.pdf" "ornek_belgeler\Sentetik Banka Hesap Dokumu Ornegi.pdf" --form "ornek_belgeler\ornek_basvuru_formu.json" --no-report
```

## Model Eğitimi

Model eğitimi için ham Kaggle/UCI veri setleri GitHub'a eklenmez. Veri setleri yerelde `veri/kaynak_veri_setleri` altında tutulur.

Önce veri setleri ortak formata dönüştürülür:

```powershell
python -B -m backend.credisense.veri_seti_donustur --dataset all
```

Ardından model eğitilir:

```powershell
python -B -m backend.credisense.model_egitimi
```

Eğitim çıktıları `modeller` klasörüne yazılır. Model dosyaları GitHub'a eklenmez.

## GitHub Notu

Büyük ham veri setleri, işlenmiş CSV dosyaları, model pickle dosyaları ve otomatik üretilen raporlar `.gitignore` ile hariç bırakılmıştır. Repo; kaynak kod, örnek sentetik belgeler ve dokümantasyonu taşır.
