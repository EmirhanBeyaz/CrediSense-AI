# Model Eğitimi Notları

Bu aşamada ilk gerçek makine öğrenmesi modeli `Give Me Some Credit` veri setiyle eğitildi.

## Kullanılan Veri

| Alan | Değer |
|---|---|
| Kaynak dosya | `veri/islenmis/give_me_some_credit_ortak_format.csv` |
| Toplam kayıt | 150.000 |
| Düşük risk | 139.974 |
| Yüksek risk | 10.026 |

Veri setinde yüksek risk sınıfı düşük risk sınıfına göre daha az olduğu için modellerde `class_weight="balanced"` kullanıldı.

## Karşılaştırılan Modeller

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Lojistik Regresyon | 0.7769 | 0.1818 | 0.6678 | 0.2858 | 0.8018 |
| Random Forest | 0.8229 | 0.2381 | 0.7496 | 0.3614 | 0.8681 |

## Seçilen Model

İlk eğitimde en iyi F1 skorunu verdiği için **Random Forest** seçildi.

Kaydedilen model:

```text
modeller/risk_modeli.pkl
```

Kaydedilen metrikler:

```text
modeller/risk_modeli_sonuclari.json
```

## Not

Bu sonuçlar ilk baseline model sonuçlarıdır. Sonraki aşamada:

- eşik değeri ayarı,
- özellik seçimi,
- Home Credit ile ikinci eğitim,
- XGBoost / LightGBM denemesi,
- SHAP ile açıklanabilirlik

eklenebilir.
