# ruff: noqa: E501
"""The facts behind the plan grill's triage (effect.md), on main as it stands. From the repo root:

    PYTHONPATH=. .venv/bin/python evidence/grills/plan-2026-10-29/probes.py
"""

from anamnesis.core.catalogue import normalise
from anamnesis.providers.numbers import parse_amount_text
from anamnesis.providers.stated import stated_amounts


def show(label, value):
    print(f"{label:58} {value}")


for text in ("two point five milligrams", "ten and fifty milligrams", "eight hundred seventy five",
             "I take one tablet once a day", "one and a half tablets",
             "tomo quinientos miligramos dos veces al día", "ich nehme fünfhundert Milligramm",
             "dos coma cinco miligramos", "tomo 575 mg"):
    show(f"stated_amounts({text!r})", sorted(map(str, stated_amounts(text)), key=float))
for word in ("five", "fifty", "خمسة", "quinientos", "fünfzig"):
    show(f"parse_amount_text({word!r})", parse_amount_text(word))
for word in ("Fünfhundertfünfundsiebzig", "dreißig", "veintitrés"):
    show(f"normalise({word!r})", repr(normalise(word)))
