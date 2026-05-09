# Kaynak Veri Setleri

Bu klasör, CrediSense AI projesinde risk tahmin modelini geliştirmek için kullanılan açık veri setlerini saklamak içindir.

İlk aşamada otomatik indirilecek veri setleri:

| Veri seti | Kaynak | Kullanım amacı |
|---|---|---|
| Statlog German Credit Data | UCI | Basit iyi/kötü kredi riski sınıflandırması |
| South German Credit | UCI | German Credit veri setinin düzeltilmiş alternatifi |
| Default of Credit Card Clients | UCI | Kredi kartı temerrüt tahmini |
| Statlog Australian Credit Approval | UCI | Kredi kartı başvuru onay/red sınıflandırması |

Kaggle veri setleri ayrıca değerlendirilecektir:

- Give Me Some Credit
- Home Credit Default Risk
- LendingClub Loan Data
- Türkiye Bankacılık Ürünleri ve Kullanımı Veri Seti

Kaggle veri setleri çoğu zaman kullanıcı girişi veya API anahtarı istediği için otomatik indirme sürecine ilk aşamada eklenmemiştir.

İndirme komutu:

```powershell
python -B -m backend.credisense.veri_setlerini_indir
```
