## Check 1: the relation audit's ten traps, on the merged code

| Case | Pattern | Right reply | Wrong reply | The wrong reply, shown as fact? |
|---|---|---|---|---|
| A | a negated amount | intake_differs_from_unit_strength | insufficient_information | no: fails safe |
| B | a past amount | match | insufficient_information | no: fails safe |
| C | another medicine's amount, same turn | insufficient_information | insufficient_information | no: the same findings as the right reply |
| D | a tablet count read as milligrams | intake_differs_from_unit_strength | insufficient_information | no: fails safe |
| E | one part of a combination | match | insufficient_information | no: fails safe |
| F | another medicine's amount, another turn | insufficient_information | insufficient_information | no: the same findings as the right reply |
| G | a stopped medicine read as active | discontinued_but_present | insufficient_information | no: fails safe |
| H | a negated amount, Egyptian Arabic | intake_differs_from_unit_strength | insufficient_information | no: fails safe |
| I | micrograms said, milligrams written | strength_mismatch | insufficient_information | no: fails safe |
| J | a daily total read as one intake | match | insufficient_information | no: fails safe |

## Check 3: every saved live report re-parsed


97 report files, 120 claims, 0 changed
