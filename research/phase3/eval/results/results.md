delirium-watch evaluation (synthetic cohort)
Synthetic cohort only. Not MIMIC-IV. Not a medical device. Not for patient care.

raw n=50  included n=49  excluded=P004
primary label: cam_icu  (three defs remain competing)

Horizon curve (AUPRC / Brier)
   H     n    n+   model AUPRC   model Brier   PRE-DELIRIC  E-PRE-DELIRIC
   6    40     4         0.124         0.132         0.172          0.231
  12    40    11         0.338         0.205         0.291          0.320
  24    40    15         0.395         0.266         0.364          0.386

Calibration (12h, reliability bins)
     bin     n    mean p    mean y
0.0-0.2    23     0.165     0.348
0.2-0.4    15     0.244     0.133
0.4-0.6     0     0.000     0.000
0.6-0.8     1     0.601     0.000
0.8-1.0     1     0.959     1.000

Subgroup table (12h, model)
subgroup             n    n+    AUPRC    Brier
age>=65             24     6    0.380    0.185
age<65              16     5    0.386    0.234
sex=F               27     8    0.389    0.215
sex=M               13     3    0.304    0.183
ventilated           8     1    0.167    0.130
not_ventilated      32    10    0.403    0.223

Alert-burden (12h)
  threshold=0.20  alerts=17  PPV=0.176  alarms/100-pt-days=8.35
  threshold=0.40  alerts=2  PPV=0.500  alarms/100-pt-days=0.98

Competing labels at 12h (same model, different endpoint)
  cam_icu        n=40  n+=11  AUPRC=0.338  Brier=0.205
  antipsychotic  n=42  n+=10  AUPRC=0.219  Brier=0.220
  restraint      n=43  n+=8  AUPRC=0.229  Brier=0.179

PRE-DELIRIC / E-PRE-DELIRIC are publication-formula stand-ins on synthetic features, not validated bedside ports.
PRE-DELIRIC / E-PRE-DELIRIC AUPRC are stand-ins, not published MIMIC numbers.
