# Crop-zoom live check (after)

| photo | region | staged pack | first read | zoom read | final | verdict | forced crop read |
|---|---|---|---|---|---|---|---|
| drawer_landscape.jpg | 89f303be32e4-0 | Norvasc 10 mg | readable, 4298 tok | - | Norvasc 10 mg | correct | readable, 793 tok, correct |
| drawer_landscape.jpg | 89f303be32e4-2 | Beloc-Zok 100 mg | readable, 4297 tok | - | Beloc-Zok 100 mg | correct | readable, 965 tok, correct |
| drawer_landscape.jpg | 89f303be32e4-1 | Concor 5 mg | readable, 4296 tok | - | Concor 5 mg Bisoprolol fumarate 30 film-coated tablets | correct | readable, 912 tok, correct |
| drawer_portrait.jpg | d09ceceb993b-0 | Beloc-Zok 100 mg | readable, 4298 tok | - | Beloc-Zok 100 mg Metoprolol succinate Prolonged-release tablets | correct | readable, 965 tok, correct |
| drawer_portrait.jpg | d09ceceb993b-2 | Norvasc 10 mg | readable, 4297 tok | - | Norvasc 10 mg | correct | readable, 841 tok, correct |
| drawer_portrait.jpg | d09ceceb993b-1 | Concor 5 mg | readable, 4297 tok | - | Concor 5 mg Bisoprolol fumarate 30 film-coated tablets | correct | readable, 912 tok, correct |
| foil_landscape.jpg | 4ed135281ae9-1 | Glucophage 850 mg | readable, 4298 tok | - | Glucophage 850 mg metformin hydrochloride | correct | readable, 1001 tok, correct |
| foil_landscape.jpg | 4ed135281ae9-0 | Panadol 500 mg | readable, 4296 tok | - | Panadol 500 mg | correct | readable, 465 tok, correct |
| foil_portrait.jpg | - | Glucophage 850 mg, Panadol 500 mg | not read | - | - | missed | - |

Spend this run $0.11856; ledger total $0.48270 of $5.00 cap.

The loop logged no `zoom_read` step on any photo (see each JSON's `report.steps`): every first read was `readable`. The last column is a forced crop read of the same region, outside the loop, for comparison.
