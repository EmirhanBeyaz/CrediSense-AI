# CrediSense AI Başvuru Formu Alanları

Bu form alanları, kullanıcıdan PDF belgelerine ek olarak alınacak yapılandırılmış başvuru verilerini tanımlar. Alanlar ilk prototip için yeterli olacak şekilde seçilmiştir.

## 1. Kimlik ve İletişim Bilgileri

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| ad_soyad | Metin | Evet | Kullanıcının ad ve soyad bilgisi. |
| tckn_test_no | Metin | Evet | Gerçek sistemde TCKN, prototipte sentetik test numarası. |
| dogum_tarihi | Tarih | Evet | Yaş hesaplaması için kullanılır. |
| telefon | Metin | Hayır | Kullanıcı iletişim bilgisi. |
| eposta | Metin | Hayır | Kullanıcı iletişim bilgisi. |
| adres | Metin | Hayır | Başvuru kaydı için kullanılabilir. |

## 2. Çalışma ve Gelir Bilgileri

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| meslek | Metin | Evet | Kullanıcının mesleği. |
| isveren_adi | Metin | Evet | Bordro, SGK veya banka açıklaması ile karşılaştırılır. |
| calisma_suresi_ay | Sayı | Hayır | Aynı işyerinde çalışma süresi. |
| beyan_edilen_aylik_gelir | Sayı | Evet | Kullanıcının formda beyan ettiği gelir. |
| ek_gelir | Sayı | Hayır | Varsa kira, serbest çalışma veya diğer gelirler. |
| gelir_turu | Seçim | Evet | Maaşlı, serbest meslek, emekli, diğer. |

## 3. Kredi Talep Bilgileri

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| talep_edilen_kredi_tutari | Sayı | Evet | Kullanıcının talep ettiği kredi miktarı. |
| vade_ay | Sayı | Evet | Kredi vadesi. |
| kredi_amaci | Seçim | Hayır | İhtiyaç, taşıt, eğitim, diğer. |

## 4. Mevcut Borç ve Finansal Yük

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| mevcut_kredi_borcu | Sayı | Hayır | Kullanıcının mevcut kredi borcu. |
| kredi_karti_borcu | Sayı | Hayır | Kredi kartı borcu. |
| aylik_taksit_toplami | Sayı | Hayır | Devam eden borçların aylık ödeme toplamı. |
| acik_kredi_sayisi | Sayı | Hayır | Kullanıcının açık kredi / kredi hattı sayısı. |
| gayrimenkul_kredi_sayisi | Sayı | Hayır | Konut veya gayrimenkul bağlantılı kredi sayısı. |
| bakmakla_yukumlu_kisi_sayisi | Sayı | Hayır | Kullanıcının bakmakla yükümlü olduğu kişi sayısı. |
| gecikme_30_59_sayisi | Sayı | Hayır | 30-59 gün gecikme geçmişi sayısı. |
| gecikme_60_89_sayisi | Sayı | Hayır | 60-89 gün gecikme geçmişi sayısı. |
| gecikme_90_sayisi | Sayı | Hayır | 90 gün ve üzeri gecikme geçmişi sayısı. |
| gecikme_gun_sayisi | Sayı | Hayır | En güncel veya bilinen gecikme gün sayısı. |
| kira_oduyor_mu | Boolean | Hayır | Kira gideri olup olmadığı. |
| aylik_kira_tutari | Sayı | Hayır | Kira gideri varsa aylık tutar. |

## 5. Yüklenecek Belgeler

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| kimlik_belgesi_pdf | Dosya | Evet | Sentetik kimlik belgesi veya resmi olmayan test belgesi. |
| gelir_belgesi_pdf | Dosya | Evet | Maaş bordrosu veya SGK hizmet dökümü. |
| banka_hesap_dokumu_pdf | Dosya | Evet | Son 3-6 aylık banka hesap dökümü. |
| ek_belge_pdf | Dosya | Hayır | Kredi kartı ekstresi, ek gelir belgesi vb. |

## 6. Sistem Tarafından Üretilecek Alanlar

Bu alanlar kullanıcıdan alınmaz; belge anlama ve analiz katmanları tarafından üretilir.

| Alan | Açıklama |
|---|---|
| document_confidence_score | Belgelerden çıkarılan verinin güvenilirlik skoru. |
| consistency_score | Kimlik, gelir belgesi ve banka dökümü arasındaki uyum skoru. |
| anomaly_score | Olağandışı finansal hareket veya belge uyumsuzluğu skoru. |
| avg_monthly_income | Banka dökümünden hesaplanan ortalama aylık gelir. |
| expense_income_ratio | Aylık giderlerin gelire oranı. |
| avg_balance | Ortalama hesap bakiyesi. |
| debt_to_income_ratio | Mevcut borcun aylık gelire oranı. |
| risk_score | Nihai modelin ürettiği 0-1 arası kredi risk skoru. |
| risk_level | Düşük, orta veya yüksek risk seviyesi. |

## 7. Örnek Başvuru Kaydı

| Alan | Değer |
|---|---|
| ad_soyad | Deniz Kaya |
| tckn_test_no | 11111111110 |
| dogum_tarihi | 12.04.1992 |
| meslek | Veri Analisti |
| isveren_adi | Nova Veri Teknolojileri A.S. |
| beyan_edilen_aylik_gelir | 42.350,75 TL |
| talep_edilen_kredi_tutari | 250.000 TL |
| vade_ay | 36 |
| mevcut_kredi_borcu | 125.000 TL |
| kredi_karti_borcu | 28.000 TL |
| acik_kredi_sayisi | 2 |
| gayrimenkul_kredi_sayisi | 0 |
| bakmakla_yukumlu_kisi_sayisi | 0 |
| gecikme_30_59_sayisi | 0 |
| gecikme_60_89_sayisi | 0 |
| gecikme_90_sayisi | 0 |
