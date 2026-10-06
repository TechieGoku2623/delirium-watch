# leakage_audit results

Pipeline rejected leakage: true. Offending feature on P005: heart_rate at 2024-01-07T06:00:00.

P003 notes signal: True. After ablating notes: False. Ablation loses P003: True.

| case | rejected | feature | timestamp | subject |
| --- | --- | --- | --- | --- |
| P005 committed post-cutoff heart_rate | True | heart_rate | 2024-01-07T06:00:00 | P005 |
| P001 injected post-cutoff lactate | True | injected_post_cutoff_lactate | 2024-01-03T06:00:00 | P001 |
