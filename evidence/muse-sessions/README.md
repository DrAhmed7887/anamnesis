# Muse Code's build sessions, one per batch round

Each file is a `muse export --redacted` of one Muse Code session that built a batch round, gzipped. Every event Muse recorded is kept: its messages, tool calls, file reads, edits, commands, results and billing records. Two things were removed for the public copy (`scripts/public/clean_muse_session.py`): the encrypted reasoning blobs, and the session owner's personal context (their own skill list). Paths are relative to the repository (`<repo>`). The briefs Muse worked from are in `briefs/`, its reports in `evidence/batches/<n>/builder.md`, and each round's gate in `evidence/batches/<n>/gate.json`.

Cost is priced from each session's own billing records at the documented Muse Spark prices (`scripts/muse_usage.py`); Meta's dashboard is the final word.

| Batch | Round | File | Model | Input tokens (cached) | Output tokens | Cost, USD |
|---|---|---|---|---|---|---|
| 16 | 1 | [`batch-16-muse_session.json.gz`](batch-16-muse_session.json.gz) | muse-spark-1.3 | 2,036,887 (1,841,516) | 29,897 | 0.6475 |
| 16 | 2 | [`batch-16-muse_session-r2.json.gz`](batch-16-muse_session-r2.json.gz) | muse-spark-1.3 | 1,254,808 (1,092,271) | 24,992 | 0.4732 |
| 17 | 1 | [`batch-17-muse_session.json.gz`](batch-17-muse_session.json.gz) | muse-spark-1.3 | 2,126,198 (1,931,583) | 39,948 | 0.7028 |
| 17 | 2 | [`batch-17-muse_session-r2.json.gz`](batch-17-muse_session-r2.json.gz) | muse-spark-1.3 | 1,767,261 (1,605,838) | 27,180 | 0.5582 |
| 18 | 1 | [`batch-18-muse_session.json.gz`](batch-18-muse_session.json.gz) | muse-spark-1.3 | 3,579,226 (3,364,778) | 37,620 | 0.9327 |
| 19 | 1 | [`batch-19-muse_session.json.gz`](batch-19-muse_session.json.gz) | muse-spark-1.3 | 3,374,352 (3,135,243) | 45,780 | 0.9637 |
| 19 | 2 | [`batch-19-muse_session-r2.json.gz`](batch-19-muse_session-r2.json.gz) | muse-spark-1.3 | 4,717,264 (4,426,327) | 75,201 | 1.3472 |
| 19.1 | 1 | [`batch-19.1-muse_session.json.gz`](batch-19.1-muse_session.json.gz) | muse-spark-1.3 | 2,657,634 (2,438,019) | 33,744 | 0.7836 |
| 19.1 | 2 | [`batch-19.1-muse_session-r2.json.gz`](batch-19.1-muse_session-r2.json.gz) | muse-spark-1.3 | 2,628,185 (2,444,803) | 27,315 | 0.7120 |
| 20 | 1 | [`batch-20-muse_session.json.gz`](batch-20-muse_session.json.gz) | muse-spark-1.3 | 12,652,211 (12,154,174) | 96,869 | 2.8574 |
| 20 | 2 | [`batch-20-muse_session-r2.json.gz`](batch-20-muse_session-r2.json.gz) | muse-spark-1.3 | 3,820,200 (3,606,849) | 41,830 | 0.9855 |
| 21 | 1 | [`batch-21-muse_session.json.gz`](batch-21-muse_session.json.gz) | muse-spark-1.3 | 7,083,058 (6,771,446) | 100,699 | 1.8332 |
| 21 | 2 | [`batch-21-muse_session-r2.json.gz`](batch-21-muse_session-r2.json.gz) | muse-spark-1.3 | 3,028,283 (2,864,049) | 37,928 | 0.7961 |
| 21 | 3 | [`batch-21-muse_session-r3.json.gz`](batch-21-muse_session-r3.json.gz) | muse-spark-1.3 | 1,213,775 (1,009,628) | 21,085 | 0.4962 |
| 22 | 1 | [`batch-22-muse_session.json.gz`](batch-22-muse_session.json.gz) | muse-spark-1.3 | 2,744,787 (2,542,482) | 40,788 | 0.8076 |
| 22 | 2 | [`batch-22-muse_session-r2.json.gz`](batch-22-muse_session-r2.json.gz) | muse-spark-1.3 | 1,843,146 (1,695,596) | 19,810 | 0.5230 |
| 23 | 1 | [`batch-23-muse_session.json.gz`](batch-23-muse_session.json.gz) | muse-spark-1.3 | 8,648,962 (8,332,739) | 62,124 | 1.9092 |
| 23 | 2 | [`batch-23-muse_session-r2.json.gz`](batch-23-muse_session-r2.json.gz) | muse-spark-1.3 | 3,473,832 (3,243,275) | 58,974 | 1.0253 |
| 23 | 3 | [`batch-23-muse_session-r3.json.gz`](batch-23-muse_session-r3.json.gz) | muse-spark-1.3 | 2,884,858 (2,654,896) | 58,196 | 0.9330 |
| 23 | 4 | [`batch-23-muse_session-r4.json.gz`](batch-23-muse_session-r4.json.gz) | muse-spark-1.3 | 5,828,407 (5,558,827) | 72,286 | 1.4780 |
| 23 | 5 | [`batch-23-muse_session-r5.json.gz`](batch-23-muse_session-r5.json.gz) | muse-spark-1.3 | 8,897,824 (8,538,833) | 138,654 | 2.3188 |
| 23 | 6 | [`batch-23-muse_session-r6.json.gz`](batch-23-muse_session-r6.json.gz) | muse-spark-1.3 | 3,890,751 (3,607,533) | 65,557 | 1.1738 |
| 23 | 7 | [`batch-23-muse_session-r7.json.gz`](batch-23-muse_session-r7.json.gz) | muse-spark-1.3 | 2,898,785 (2,686,708) | 47,733 | 0.8710 |
| 23 | 8 | [`batch-23-muse_session-r8.json.gz`](batch-23-muse_session-r8.json.gz) | muse-spark-1.3 | 1,423,456 (1,255,742) | 21,330 | 0.4887 |
| 23 | 9 | [`batch-23-muse_session-r9.json.gz`](batch-23-muse_session-r9.json.gz) | muse-spark-1.3 | 1,833,221 (1,649,779) | 23,641 | 0.5772 |
| 23.1 | 1 | [`batch-23.1-muse_session.json.gz`](batch-23.1-muse_session.json.gz) | muse-spark-1.3 | 1,695,274 (1,517,525) | 28,165 | 0.5695 |
| 24 | 1 | [`batch-24-muse_session.json.gz`](batch-24-muse_session.json.gz) | muse-spark-1.3 | 12,587,847 (11,971,923) | 137,438 | 3.1498 |
| 24 | 2 | [`batch-24-muse_session-r2.json.gz`](batch-24-muse_session-r2.json.gz) | muse-spark-1.3 | 2,634,312 (2,409,377) | 43,089 | 0.8257 |
| 24 | 3 | [`batch-24-muse_session-r3.json.gz`](batch-24-muse_session-r3.json.gz) | muse-spark-1.3 | 2,578,885 (2,380,012) | 35,911 | 0.7582 |
| 24 | 4 | [`batch-24-muse_session-r4.json.gz`](batch-24-muse_session-r4.json.gz) | muse-spark-1.3 | 2,215,297 (2,040,247) | 30,529 | 0.6546 |
| 24 | 5 | [`batch-24-muse_session-r5.json.gz`](batch-24-muse_session-r5.json.gz) | muse-spark-1.3 | 3,652,364 (3,432,723) | 44,064 | 0.9767 |
| 24 | 6 | [`batch-24-muse_session-r6.json.gz`](batch-24-muse_session-r6.json.gz) | muse-spark-1.3 | 4,027,795 (3,815,503) | 59,682 | 1.0913 |
| 24 | 7 | [`batch-24-muse_session-r7.json.gz`](batch-24-muse_session-r7.json.gz) | muse-spark-1.3 | 2,873,622 (2,676,506) | 45,560 | 0.8415 |
| 24 | 8 | [`batch-24-muse_session-r8.json.gz`](batch-24-muse_session-r8.json.gz) | muse-spark-1.3 | 3,667,643 (3,438,694) | 52,705 | 1.0260 |
| 24 | 9 | [`batch-24-muse_session-r9.json.gz`](batch-24-muse_session-r9.json.gz) | muse-spark-1.3 | 3,679,001 (3,457,382) | 53,183 | 1.0217 |
| 24 | 10 | [`batch-24-muse_session-r10.json.gz`](batch-24-muse_session-r10.json.gz) | muse-spark-1.3 | 1,659,763 (1,412,497) | 23,460 | 0.6207 |
| 24.1 | 1 | [`batch-24.1-muse_session.json.gz`](batch-24.1-muse_session.json.gz) | muse-spark-1.3 | 9,273,301 (8,914,913) | 66,544 | 2.0680 |
| 24.2 | 1 | [`batch-24.2-muse_session.json.gz`](batch-24.2-muse_session.json.gz) | muse-spark-1.3 | 2,910,626 (2,710,727) | 25,822 | 0.7662 |
| 25 | 1 | [`batch-25-muse_session.json.gz`](batch-25-muse_session.json.gz) | muse-spark-1.3 | 2,331,858 (2,090,166) | 50,634 | 0.8308 |
| 25 | 2 | [`batch-25-muse_session-r2.json.gz`](batch-25-muse_session-r2.json.gz) | muse-spark-1.3 | 1,070,906 (894,925) | 23,057 | 0.4522 |
| 26 | 1 | [`batch-26-muse_session.json.gz`](batch-26-muse_session.json.gz) | muse-spark-1.3 | 6,285,359 (5,996,494) | 64,831 | 1.5361 |
| 26 | 2 | [`batch-26-muse_session-r2.json.gz`](batch-26-muse_session-r2.json.gz) | muse-spark-1.3 | 3,451,091 (3,233,585) | 43,792 | 0.9430 |
| 26 | 3 | [`batch-26-muse_session-r3.json.gz`](batch-26-muse_session-r3.json.gz) | muse-spark-1.3 | 730,713 (599,779) | 20,730 | 0.3417 |
| 26.1 | 1 | [`batch-26.1-muse_session.json.gz`](batch-26.1-muse_session.json.gz) | muse-spark-1.3 | 1,954,903 (1,796,776) | 17,512 | 0.5416 |
| 27 | 1 | [`batch-27-muse_session.json.gz`](batch-27-muse_session.json.gz) | muse-spark-1.3 | 22,365,015 (21,819,336) | 212,047 | 4.8562 |
| 27 | 2 | [`batch-27-muse_session-r2.json.gz`](batch-27-muse_session-r2.json.gz) | muse-spark-1.3 | 1,227,671 (1,088,386) | 18,724 | 0.4169 |
| 27 | 3 | [`batch-27-muse_session-r3.json.gz`](batch-27-muse_session-r3.json.gz) | muse-spark-1.3 | 6,223,023 (5,953,361) | 55,588 | 1.4663 |
| 27.1 | 1 | [`batch-27.1-muse_session.json.gz`](batch-27.1-muse_session.json.gz) | muse-spark-1.3 | 3,903,051 (3,680,042) | 45,615 | 1.0246 |
| 27.1 | 2 | [`batch-27.1-muse_session-r2.json.gz`](batch-27.1-muse_session-r2.json.gz) | muse-spark-1.3 | 2,399,237 (2,211,075) | 37,980 | 0.7283 |
| 28 | 1 | [`batch-28-muse_session.json.gz`](batch-28-muse_session.json.gz) | muse-spark-1.3 | 8,372,997 (8,049,873) | 58,632 | 1.8606 |
| 28 | 2 | [`batch-28-muse_session-r2.json.gz`](batch-28-muse_session-r2.json.gz) | muse-spark-1.3 | 2,844,025 (2,677,206) | 29,211 | 0.7343 |
| 28 | 3 | [`batch-28-muse_session-r3.json.gz`](batch-28-muse_session-r3.json.gz) | muse-spark-1.3 | 1,713,230 (1,555,707) | 21,591 | 0.5220 |
| 29 | 1 | [`batch-29-muse_session.json.gz`](batch-29-muse_session.json.gz) | muse-spark-1.3 | 1,826,858 (1,642,144) | 19,535 | 0.5602 |
| 30 | 1 | [`batch-30-muse_session.json.gz`](batch-30-muse_session.json.gz) | muse-spark-1.3 | 2,773,984 (2,606,979) | 36,475 | 0.7548 |
| 30 | 2 | [`batch-30-muse_session-r2.json.gz`](batch-30-muse_session-r2.json.gz) | muse-spark-1.3 | 2,069,142 (1,894,034) | 34,739 | 0.6506 |
| 30 | 3 | [`batch-30-muse_session-r3.json.gz`](batch-30-muse_session-r3.json.gz) | muse-spark-1.3 | 1,987,033 (1,847,924) | 30,996 | 0.5828 |
| 31 | 1 | [`batch-31-muse_session.json.gz`](batch-31-muse_session.json.gz) | muse-spark-1.3 | 3,623,910 (3,397,884) | 39,902 | 0.9618 |
| 31 | 2 | [`batch-31-muse_session-r2.json.gz`](batch-31-muse_session-r2.json.gz) | muse-spark-1.3 | 4,547,537 (4,331,201) | 55,931 | 1.1578 |
| 31 | 3 | [`batch-31-muse_session-r3.json.gz`](batch-31-muse_session-r3.json.gz) | muse-spark-1.3 | 1,486,979 (1,334,199) | 28,252 | 0.5112 |
| 32 | 1 | [`batch-32-muse_session.json.gz`](batch-32-muse_session.json.gz) | muse-spark-1.3 | 1,395,174 (1,243,228) | 23,801 | 0.4776 |
| 32 | 2 | [`batch-32-muse_session-r2.json.gz`](batch-32-muse_session-r2.json.gz) | muse-spark-1.3 | 2,837,893 (2,611,128) | 66,711 | 0.9586 |
| 33 | 1 | [`batch-33-muse_session.json.gz`](batch-33-muse_session.json.gz) | muse-spark-1.3 | 2,555,167 (2,357,025) | 35,512 | 0.7522 |
| 34 | 1 | [`batch-34-muse_session.json.gz`](batch-34-muse_session.json.gz) | muse-spark-1.3 | 1,144,091 (1,011,902) | 19,686 | 0.4007 |
| 34 | 2 | [`batch-34-muse_session-r2.json.gz`](batch-34-muse_session-r2.json.gz) | muse-spark-1.3 | 787,218 (679,207) | 11,746 | 0.2868 |

64 sessions, $64.87 in all.
