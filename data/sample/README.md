# Sample data

These tables are **synthetic**. They are not MIMIC-IV, not derived from
MIMIC-IV, and not a de-identified extract. They exist so `make demo`,
`make test`, and `make research` run with no PhysioNet credentials and
no network.

Real incidence, timing, and label-agreement numbers require credentialed
access to MIMIC-IV (and MIMIC-IV-Note if nursing text is in scope). That
process takes weeks. See `docs/DATA.md`. Do not commit any MIMIC row.

The generator is `data/sample/generate.py` (`make demo-data`). Seed 0.
Structure mirrors a MIMIC-like schema: `patients`, `chartevents`
(CAM-ICU, RASS), `prescriptions`, `procedureevents` (restraints),
`noteevents`, `vitalsigns`.

| ID | Why it is here |
| --- | --- |
| P001 | Develops delirium after a clear physiological prodrome. All three labels fire. |
| P002 | High anticholinergic burden, no event. False-positive pressure for ACB features. |
| P003 | Only signal is in nursing notes. Ablating notes loses this one. Structured labels negative. |
| P004 | Comfort care. Must be excluded from every analysis set. |
| P005 | Post-cutoff `heart_rate` at icu_intime+30h. Leakage audit must name and reject it. |

P006–P050 fill pairwise label cells so agreement is measurable. They are
designed fillers, not a population sample. Do not quote their base rate
as a clinical incidence.
