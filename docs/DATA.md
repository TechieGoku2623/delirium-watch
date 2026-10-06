# Data

Phase 0 does not download MIMIC-IV, MIMIC-IV-Note, or any PhysioNet file.
The committed objects are:

- `data/sample/generate.py` — seeded (0) generator for 50 synthetic stays
- `data/sample/*.json` — MIMIC-like tables produced by that generator
- `data/sample/README.md` — why the five designed patients exist

No patient-identifiable data. No restricted-access corpus. IDs `P001`–
`P050` are designed probes, not `subject_id` values from PhysioNet.

**Do not commit any MIMIC row, note, or derived parquet.** `data/*` is
gitignored except `data/sample/`.

## MIMIC-IV access (weeks, not hours)

Real incidence, timing, and label-agreement numbers require credentialed
access. Exact steps:

1. Create an account at [PhysioNet](https://physionet.org/).
2. Complete CITI Program training: **Data or Specimens Only Research**
   (CITI course used by PhysioNet; if your home institution is not a CITI
   subscriber, affiliate with Massachusetts Institute of Technology as
   PhysioNet documents). Budget 4–8 hours of modules plus 1–7 calendar
   days if an institutional administrator must verify affiliation.
3. Upload the CITI completion report to your PhysioNet profile.
4. Sign the **MIMIC-IV Data Use Agreement** on the MIMIC-IV project page.
5. Request access to **MIMIC-IV**. Wait for human credentialing review.
   Typical review is several business days; backlog can push this to
   two–three weeks.
6. If nursing notes are in scope, request **MIMIC-IV-Note** as a separate
   PhysioNet project and sign its DUA. Do not assume the MIMIC-IV
   approval covers notes.
7. After approval, download via PhysioNet `wget` or the then-current
   cloud copy (BigQuery / AWS Open Data if still hosted). Full MIMIC-IV
   plus notes is tens to hundreds of GB.
8. Keep raw files in gitignored bronze storage. Later phases write a
   manifest (source URL, retrieval timestamp, row count, sha256).

**Calendar time: plan on 2–8 weeks** from starting CITI to a usable local
copy. Phase 0 does not start that clock; it documents it.

Demo and CI run only on the synthetic cohort (`make demo-data`).
