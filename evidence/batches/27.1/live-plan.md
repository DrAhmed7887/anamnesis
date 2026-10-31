# Batch 27.1: the live check, written before any call (31 Oct, 14:17 CET)

- **What runs:** the relation audit's live probe again (`evidence/batches/27/probe_after.py`, the ten invented traps), once each on Spark 1.3 and the tuned Glimmer on Modal, on merged `main`.
- **Expected:** no wrong finding shown as fact. Trap J on Glimmer, a false `strength_mismatch` through its tablet count in the batch 27 probe, should now fail safe if Glimmer writes the same reply; Glimmer's replies vary between calls, so what it writes is reported as it comes.
- **Spend:** about $0.14 of Meta (ten Spark calls) and one Modal cold start (about $1.6 of credit), reconciled from Modal's billing.
