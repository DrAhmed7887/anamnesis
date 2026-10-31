"""Words and templates for the generated notes, in English and Egyptian Arabic.

The patient's speech is not run through assert_no_advice, as the product doesn't run it there: patients
say "I take ..." and "I stopped taking ...". The check covers the answer's claim fields only
(common.check_example), and a medicine name never holds a word such as "take".
"""

import random
from dataclasses import dataclass
from decimal import Decimal

from finetune.common import number

# ------------------------------------------------------------------------------------------- number words
_EN_ONES = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
            "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_EN_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_AR_ONES = ("", "واحد", "اتنين", "تلاتة", "اربعة", "خمسة", "ستة", "سبعة", "تمانية", "تسعة", "عشرة", "حداشر",
            "اتناشر", "تلتاشر", "اربعتاشر", "خمستاشر", "ستاشر", "سبعتاشر", "تمنتاشر", "تسعتاشر")
_AR_TENS = ("", "", "عشرين", "تلاتين", "اربعين", "خمسين", "ستين", "سبعين", "تمانين", "تسعين")
_AR_HUNDREDS = ("", "مية", "ميتين", "تلتمية", "ربعمية", "خمسمية", "ستمية", "سبعمية", "تمنمية", "تسعمية")
_INDIC = str.maketrans("0123456789.", "٠١٢٣٤٥٦٧٨٩٫")


def _en_int(n: int, rng: random.Random) -> str:
    if n < 20:
        return _EN_ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _EN_TENS[tens] if not ones else _EN_TENS[tens] + rng.choice(("-", " ")) + _EN_ONES[ones]
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        head = f"{_EN_ONES[hundreds]} hundred"
        return head if not rest else head + rng.choice((" and ", " ")) + _en_int(rest, rng)
    return "one thousand"


def en_words(value: Decimal, rng: random.Random) -> str | None:
    """English number words the product's stated_amounts reads back as the value, or None."""
    whole = int(value)
    fraction = value - whole
    if whole > 1000 or (whole == 1000 and fraction):
        return None
    if not fraction:
        return _en_int(whole, rng)
    head = _en_int(whole, rng) if whole else rng.choice(("zero", ""))
    if fraction == Decimal("0.5") and whole and rng.random() < 0.5:
        return f"{head} and a half"
    digits = number(fraction)[2:]  # "0.25" -> "25"
    return f"{head} point {' '.join(_EN_ONES[int(digit)] for digit in digits)}".strip()


def _ar_int(n: int) -> str:
    if n < 20:
        return _AR_ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _AR_TENS[tens] if not ones else f"{_AR_ONES[ones]} و{_AR_TENS[tens]}"
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return _AR_HUNDREDS[hundreds] if not rest else f"{_AR_HUNDREDS[hundreds]} و{_ar_int(rest)}"
    return "الف"


def ar_words(value: Decimal) -> str | None:
    """Egyptian Arabic number words stated_amounts reads back as the value (halves with «ونص»), or None."""
    whole = int(value)
    fraction = value - whole
    if whole > 1000 or (whole == 1000 and fraction) or fraction not in (0, Decimal("0.5")):
        return None
    if not fraction:
        return _ar_int(whole)
    return "نص" if not whole else f"{_ar_int(whole)} ونص"


def digits(value: Decimal, indic: bool = False) -> str:
    text = number(value)
    return text.translate(_INDIC) if indic else text


# ------------------------------------------------------------------------------------------- vocabularies
# Unit words: English (plural, singular or adjective), Arabic. Arabic notes never say grams: «جرام» alone
# means one gram but states no number, so the product would drop it.
EN_UNITS = {
    "mg": (("milligrams", "mg"), ("milligram", "mg")),
    "mcg": (("micrograms", "mcg"), ("microgram", "mcg")),
    "g": (("grams", "g"), ("gram", "g")),
}
AR_UNITS = {"mg": ("ملي جرام", "مللي جرام", "ملليجرام", "مليجرام"), "mcg": ("ميكروجرام", "ميكرو جرام")}

FREQ = {
    "en": (("once a day", 1), ("once daily", 1), ("one time a day", 1), ("every morning", 1),
           ("every night", 1), ("every evening", 1), ("in the morning", 1), ("at night", 1),
           ("in the evening", 1), ("twice a day", 2), ("twice daily", 2), ("two times a day", 2),
           ("morning and night", 2),
           ("morning and evening", 2), ("three times a day", 3), ("three times daily", 3),
           ("four times a day", 4)),
    "ar": (("مرة في اليوم", 1), ("مرة واحدة في اليوم", 1), ("مرة يوميا", 1), ("كل يوم الصبح", 1),
           ("الصبح", 1), ("بالليل", 1), ("قبل النوم", 1), ("كل يوم بالليل", 1), ("مرتين في اليوم", 2),
           ("مرتين يوميا", 2), ("الصبح وبالليل", 2), ("تلات مرات في اليوم", 3), ("تلات مرات يوميا", 3),
           ("اربع مرات في اليوم", 4)),
}
PRN = {
    "en": ("when I need it", "as needed", "only when I have pain", "when I have a headache", "if I need it",
           "only when I need it"),
    "ar": ("لما احتاجه", "وقت اللزوم", "لما يكون عندي وجع", "لما يكون عندي صداع", "بس لما احتاجه"),
}
# (count, tablet words, capsule words); None where the form can't take it (half a capsule).
UNITS = {
    "en": ((Decimal("0.5"), "half a tablet", None), (Decimal(1), "one tablet", "one capsule"),
           (Decimal(2), "two tablets", "two capsules"), (Decimal(3), "three tablets", "three capsules")),
    "ar": ((Decimal("0.5"), "نص حباية", None), (Decimal(1), "حباية واحدة", "كبسولة واحدة"),
           (Decimal(2), "حبايتين", "كبسولتين"), (Decimal(3), "تلات حبايات", "تلات كبسولات")),
}
UNITS_WEIGHTS = (10, 45, 35, 10)
RANGE_UNITS = {
    "en": {"tablet": ("one or two tablets", "two or three tablets", "half a tablet or a whole one"),
           "capsule": ("one or two capsules", "two or three capsules")},
    "ar": {"tablet": ("حباية أو اتنين", "حباية ولا اتنين", "حبايتين أو تلاتة"),
           "capsule": ("كبسولة أو اتنين", "كبسولة ولا اتنين")},
}
RANGE_FREQ = {
    "en": ("two or three times a day", "once or twice a day", "three or four times a day"),
    "ar": ("مرة أو مرتين في اليوم", "مرتين تلاتة في اليوم", "مرتين أو تلات مرات في اليوم"),
}
WHEN = {
    "en": ("last month", "two weeks ago", "a few months ago", "last year", "last week", "a while ago", ""),
    "ar": ("من شهر", "من اسبوعين", "من كام شهر", "من سنة", "من فترة", "من اسبوع", ""),
}
FORM = {"en": {"tablet": "tablets", "capsule": "capsules"},
        "ar": {"tablet": "الحباية", "capsule": "الكبسولة"}}
OPENERS = {"en": ("", "", "Hi doctor.", "Hello.", "So,", "These are my medicines."),
           "ar": ("", "", "السلام عليكم يا دكتور.", "اهلا يا دكتور.", "بص يا دكتور،",
                  "دي الادوية اللي باخدها.")}
CLOSERS = {"en": ("", "", "That's all.", "That's it.", "That's everything I'm on."),
           "ar": ("", "", "بس كده.", "هو ده كل حاجة.", "بس.")}
# Before the second and third medicine. Arabic «و» joins the next word, so it never goes before a name.
CONNECTORS = {"en": ("", "And ", "Also, ", "Plus "), "ar": ("", "و", "وكمان ", "كمان ")}


# ------------------------------------------------------------------------------------------------ templates
@dataclass(frozen=True)
class Frame:
    """One template for one medicine. Slots: {name} {al_name} (Arabic article + name) {dose} (intake)
    {sdose} {sdose_pl} (the tablet's strength) {form} {units} {freq} {prn} {when} {inn} {range_units}
    {range_freq}. "|" marks a turn boundary, honoured only in notes of several turns."""

    id: str
    lang: str
    kind: str
    text: str
    test_only: bool


_KIND_STATUS = {"stopped": "discontinued", "unsure": "unknown"}

# (kind, text, test_only), numbered per language and kind in this order.
_EN = (
    ("intake", "I'm on {name} {dose} {freq}.", False),
    ("intake", "I've been taking {name} {dose} {freq}.", False),
    ("intake", "{name} {dose} {freq}.", False),
    ("intake", "I'm taking {name}, {dose}, {freq}.", False),
    ("intake", "I use {name} {dose} {freq}.", False),
    ("intake", "I'm on {name} {dose}.", False),
    ("intake", "I have {name} {dose}.", False),
    ("intake", "I'm also on {name}.|{dose} {freq}.", False),
    ("intake", "My {name} is {dose}, {freq}.", True),
    ("intake", "I've got {name} {dose}, {freq}.", True),
    ("intake", "There's {name} as well, {dose}.", True),
    ("intake", "And then {name}.|It's {dose}, {freq}.", True),
    ("strength", "I'm on the {sdose} {name} {form}, {units} {freq}.", False),
    ("strength", "I have {name}, the {sdose} {form}, {units} {freq}.", False),
    ("strength", "My {name} {form} are {sdose_pl} each, and I have {units} {freq}.", True),
    ("units", "I'm on {name} {dose}, {units} at a time.", False),
    ("units", "{name} {dose}, {units} each time.", True),
    ("prn", "I'm taking {name} {dose} {prn}.", False),
    ("prn", "I use {name} {prn}.", False),
    ("prn", "{name} {dose}, {prn}.", False),
    ("prn", "Sometimes I have {name} {dose}, {prn}.", True),
    ("plain", "I'm also on {name}.", False),
    ("plain", "I'm on {name} {freq}.", False),
    ("plain", "{name} {freq}.", False),
    ("plain", "I have {name} too, {freq}.", True),
    ("plain", "There's also {name}.", True),
    ("stopped", "I stopped taking {name} {when}.", False),
    ("stopped", "I quit {name} {when}.", False),
    ("stopped", "I used to be on {name} {dose}, but I stopped it {when}.", False),
    ("stopped", "I'm not on {name} anymore.", False),
    ("stopped", "{name}, I stopped that {when}.", True),
    ("stopped", "I came off {name} {dose} {when}.", True),
    ("unsure", "I'm not sure if I'm still on {name}.", False),
    ("unsure", "Maybe I still have {name}, I don't remember.", True),
    ("range_units", "I'm taking {name} {dose}, {range_units} {prn}.", False),
    ("range_units", "{name}, {range_units} {freq}.", False),
    ("range_units", "For {name} I have {range_units}, {prn}.", True),
    ("range_freq", "I'm on {name} {dose} {range_freq}.", False),
    ("range_freq", "{name} {dose}, maybe {range_freq}.", True),
    ("brand_inn", "I'm on {name}, that's {inn}, {dose} {freq}.", False),
    ("brand_inn", "{name}, which is {inn}, {dose} {freq}.", True),
    # "take", as patients say it (added after the rest, so the ids above don't move).
    ("intake", "I take {name} {dose} {freq}.", False),
    ("intake", "I also take {name}, {dose} {freq}.", False),
    ("intake", "I take {name} {dose}.", False),
    ("intake", "I take {name} too.|{dose} {freq}.", False),
    ("strength", "I take the {sdose} {name} {form}, {units} {freq}.", False),
    ("units", "I take {name} {dose}, {units} at a time.", False),
    ("prn", "I take {name} {dose} {prn}.", False),
    ("prn", "I take {name} {prn}.", False),
    ("plain", "I take {name} {freq}.", False),
    ("plain", "I also take {name}.", False),
    ("stopped", "I don't take {name} anymore.", False),
    ("stopped", "I used to take {name} {dose}, but I stopped it {when}.", False),
    ("unsure", "I'm not sure if I still take {name}.", False),
    ("range_units", "I take {name} {dose}, {range_units} {prn}.", False),
    ("range_freq", "I take {name} {dose} {range_freq}.", False),
    ("brand_inn", "I take {name}, that's {inn}, {dose} {freq}.", False),
    ("intake", "The {name} I take is {dose}, {freq}.", True),
    ("intake", "I take my {name}, {dose}, {freq}.", True),
    ("strength", "The {name} I take comes as {sdose} {form}, {units} {freq}.", True),
    ("units", "{name} {dose}, I take {units} each time.", True),
    ("prn", "I only take {name} {dose} {prn}.", True),
    ("plain", "I take {name} as well, {freq}.", True),
    ("stopped", "I don't take {name} now, I stopped it {when}.", True),
    ("unsure", "I don't know if I still take {name}.", True),
    ("range_units", "I take {range_units} of {name} {prn}.", True),
    ("range_freq", "I take {name} {dose}, maybe {range_freq}.", True),
    ("brand_inn", "I take {name}, which is {inn}, {dose} {freq}.", True),
)
_AR = (
    ("intake", "انا باخد {name} {dose} {freq}.", False),
    ("intake", "باخد {name} {dose} {freq}.", False),
    ("intake", "{name} {dose} {freq}.", False),
    ("intake", "انا ماشي على {name} {dose} {freq}.", False),
    ("intake", "بستعمل {name} {dose} {freq}.", False),
    ("intake", "باخد {name} {dose}.", False),
    ("intake", "عندي كمان {name} {dose}.", False),
    ("intake", "باخد كمان {name}.|{dose} {freq}.", False),
    ("intake", "الدكتور كاتبلي {name} {dose} {freq}.", True),
    ("intake", "{name} بتاعي {dose}، باخده {freq}.", True),
    ("intake", "فيه كمان {name} {dose}.", True),
    ("intake", "وبعدين {name}.|ده باخده {dose} {freq}.", True),
    ("strength", "باخد {name} اللي {form} فيها {sdose}، {units} {freq}.", False),
    ("strength", "عندي {name} {form} فيها {sdose}، باخد {units} {freq}.", False),
    ("strength", "علبة {name} مكتوب عليها {sdose} في {form}، وباخد {units} {freq}.", True),
    ("units", "باخد {name} {dose}، {units} في المرة.", False),
    ("units", "{name} {dose}، باخد منه {units} كل مرة.", True),
    ("prn", "باخد {name} {dose} {prn}.", False),
    ("prn", "باخد {name} {prn}.", False),
    ("prn", "{name} {dose} {prn}.", False),
    ("prn", "ساعات باخد {name} {dose} {prn}.", True),
    ("plain", "كمان باخد {name}.", False),
    ("plain", "باخد {name} {freq}.", False),
    ("plain", "{name} {freq}.", False),
    ("plain", "عندي {name} برضه، {freq}.", True),
    ("plain", "فيه {name} كمان.", True),
    ("stopped", "وقفت {al_name} {when}.", False),
    ("stopped", "بطلت {name} {when}.", False),
    ("stopped", "كنت باخد {name} {dose} وبطلته {when}.", False),
    ("stopped", "مبقتش باخد {name}.", False),
    ("stopped", "{name} ده وقفته {when}.", True),
    ("stopped", "سبت {al_name} {when}.", True),
    ("unsure", "مش متأكد لسه باخد {name} ولا لأ.", False),
    ("unsure", "مش فاكر بطلت {name} ولا لسه.", True),
    ("range_units", "باخد {name} {dose}، {range_units} {prn}.", False),
    ("range_units", "{name}، {range_units} {freq}.", False),
    ("range_units", "من {name} باخد {range_units} {prn}.", True),
    ("range_freq", "باخد {name} {dose} {range_freq}.", False),
    ("range_freq", "{name} {dose}، يمكن {range_freq}.", True),
    ("brand_inn", "باخد {name} اللي هو {inn}، {dose} {freq}.", False),
    ("brand_inn", "{name}، يعني {inn}، {dose} {freq}.", True),
)


def _frames(lang: str, rows: tuple[tuple[str, str, bool], ...]) -> tuple[Frame, ...]:
    counts: dict[str, int] = {}
    frames = []
    for kind, text, test_only in rows:
        counts[kind] = counts.get(kind, 0) + 1
        frames.append(Frame(f"{lang}-{kind}-{counts[kind]}", lang, kind, text, test_only))
    return tuple(frames)


FRAMES = _frames("en", _EN) + _frames("ar", _AR)
KIND_WEIGHTS = {"intake": 33, "strength": 9, "units": 5, "prn": 8, "plain": 9, "stopped": 14, "unsure": 3,
                "range_units": 6, "range_freq": 5, "brand_inn": 5}


def status_of(frame: Frame) -> str:
    return _KIND_STATUS.get(frame.kind, "active")
