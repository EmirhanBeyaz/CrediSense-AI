# CrediSense AI Veri Seti Kaynakları

Bu dosya, proje için kullanılacak açık veri setlerini ve durumlarını takip etmek için hazırlanmıştır.

## İndirilen Açık Veri Setleri

Bu veri setleri `backend.credisense.veri_setlerini_indir` betiği ile indirildi.

| Veri seti | Konum | Durum | Kullanım amacı |
|---|---|---|---|
| Statlog German Credit Data | `veri/kaynak_veri_setleri/statlog_german_credit` | İndirildi | Basit iyi/kötü kredi riski sınıflandırması |
| South German Credit | `veri/kaynak_veri_setleri/south_german_credit` | İndirildi | German Credit veri setinin düzeltilmiş alternatifi |
| Default of Credit Card Clients | `veri/kaynak_veri_setleri/default_of_credit_card_clients` | İndirildi | Kredi kartı temerrüt tahmini |
| Statlog Australian Credit Approval | `veri/kaynak_veri_setleri/statlog_australian_credit_approval` | İndirildi | Kredi başvurusu onay/red sınıflandırması |

## Kaggle Üzerinden Alınacak Veri Setleri

Bu veri setleri genelde Kaggle hesabı veya API token istediği için otomatik indirme sürecine ilk aşamada eklenmedi.
Kullanıcı tarafından indirilen dosyalar `veri/kaynak_veri_setleri/kaggle` altında tutulacaktır.

| Veri seti | Durum | Not |
|---|---|---|
| Give Me Some Credit | İndirildi | Ana risk tahmin modeli için en uygun adaylardan biri |
| Home Credit Default Risk | Kısmen indirildi | Şu an yalnızca `application_train.csv` var; başlangıç için yeterli |
| German Credit Data Kaggle sürümü | İndirildi | German Credit'in CSV formatlı Kaggle sürümü |
| LendingClub Loan Data | İndirildi | Çok büyük olduğu için başlangıçta sadece örnekleme veya seçili kolonlarla kullanılmalı |
| Türkiye Bankacılık Ürünleri ve Kullanımı Veri Seti | İndirildi | Türkiye bağlamı için yardımcı olabilir; sentetik veri olduğu ayrıca belirtilmeli |

## Kaggle Klasöründe Kontrol Edilen Dosyalar

Son kontrol sonucu:

| Dosya | Satır | Sütun | Not |
|---|---:|---:|---|
| `kaggle/german_credit_data.csv` | 1.000 | 10 | Küçük ve kolay anlaşılır kredi veri seti |
| `kaggle/GiveMeSomeCredit/cs-training.csv` | 150.000 | 12 | Eğitim için ana aday |
| `kaggle/GiveMeSomeCredit/cs-test.csv` | 101.503 | 12 | Kaggle test dosyası, hedef alanı boş olabilir |
| `kaggle/GiveMeSomeCredit/sampleEntry.csv` | 101.503 | 2 | Kaggle örnek gönderim dosyası, model eğitiminde gerekmez |
| `kaggle/Home Credit Default Risk/application_train.csv` | 307.511 | 122 | Büyük ama başlangıç için yalnızca bu dosya kullanılabilir |
| `kaggle/All Lending Club Loan Data/accepted_2007_to_2018Q4.csv` | 2.260.701 | 151 | Çok büyük; doğrudan ana akışa alınmamalı |
| `kaggle/All Lending Club Loan Data/rejected_2007_to_2018Q4.csv` | 27.648.741 | 9 | Çok büyük; gerekirse örnekleme yapılmalı |
| `kaggle/Türkiye Bankacılık Ürünleri ve Kullanımı Veri Seti/turkiye_2026_bankacilik_verisi.csv` | 100.000 | 21 | Türkiye bağlamı için uygun yardımcı veri |

## İşlenmiş Veri Setleri

İlk dönüşüm Give Me Some Credit eğitim verisi üzerinden yapılmıştır.

| İşlenmiş dosya | Kaynak | Satır | Not |
|---|---|---:|---|
| `veri/islenmis/give_me_some_credit_ortak_format.csv` | `cs-training.csv` | 150.000 | Risk modeli için ana aday |
| `veri/islenmis/german_credit_kaggle_ortak_format.csv` | `german_credit_data.csv` | 1.000 | Hedef etiketi yok; model eğitimi için kullanılmamalı |
| `veri/islenmis/turkiye_bankacilik_ortak_format.csv` | `turkiye_2026_bankacilik_verisi.csv` | 100.000 | Hedef etiketi skor/gecikme/limit kullanımından türetildi |
| `veri/islenmis/home_credit_application_train_ortak_format.csv` | `application_train.csv` | 307.511 | Orijinal `TARGET` alanı kullanıldı |

Bu dosyada hedef değişken:

- `hedef_risk = 0`: düşük risk
- `hedef_risk = 1`: yüksek risk

Sınıf dağılımı:

- Düşük risk: 139.974
- Yüksek risk: 10.026

Diğer dönüştürülen veri setleri için kısa durum:

| Veri seti | Düşük risk | Yüksek risk | Bilinmeyen risk | Hedef kaynağı |
|---|---:|---:|---:|---|
| German Credit Kaggle | 0 | 0 | 1.000 | Yok |
| Türkiye Bankacılık 2026 | 82.443 | 17.557 | 0 | Türetilmiş |
| Home Credit Default Risk | 282.686 | 24.825 | 0 | Orijinal |

LendingClub dosyaları çok büyük olduğu için henüz ortak formata dönüştürülmedi. Bu veri seti için daha sonra örnekleme veya seçili kolonlarla ayrı bir dönüşüm yapılmalıdır.

## Proje İçinde Üretilen Sentetik Belgeler

Belge anlama katmanı için açık ve gerçek kimlik/bordro/banka PDF veri setleri bulmak zordur. Bu yüzden proje içinde sentetik belgeler kullanılacaktır.

| Belge | Konum | Kullanım amacı |
|---|---|---|
| Sentetik Kimlik Belgesi | `ornek_belgeler/Sentetik Kimlik Belgesi Ornegi.pdf` | Kimlik alanı çıkarımı |
| Sentetik Maaş Bordrosu | `ornek_belgeler/Sentetik Maas Bordrosu Ornegi.pdf` | Gelir ve işveren alanı çıkarımı |
| Sentetik Banka Hesap Dökümü | `ornek_belgeler/Sentetik Banka Hesap Dokumu Ornegi.pdf` | Gelir-gider hareketleri ve anomali kontrolü |

## Sonraki Teknik Adım

İndirilen ham veri setlerini ortak bir CSV formatına çevirmek gerekir. Önerilen ortak kolonlar:

- `dataset_name`
- `age`
- `monthly_income`
- `credit_amount`
- `debt_ratio`
- `payment_delay_count`
- `target`

Her veri setinde bu kolonların hepsi bulunmayabilir. Eksik alanlar boş bırakılabilir veya veri setine özel dönüştürme yapılabilir.
