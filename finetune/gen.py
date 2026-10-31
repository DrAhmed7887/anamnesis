"""Generate the fine-tune's data (evidence/finetune/plan.md): seeded and deterministic, every answer built
in code from the same random choices as its utterance, and checked by the product's own parser before it is
written.

    .venv/bin/python finetune/gen.py [--seed N] [--out DIR] [--vocab v1|v2]

Writes, to finetune/data/ by default:
- <split>.jsonl, Fireworks chat SFT lines holding only "messages" (system and user weight 0, the answer 1);
- <split>.answers.jsonl, one line per example: the intended claims, the turns, the template ids, the drugs and
  the noise applied (the scorer reads these);
- meta.json: the seed, the noise rate, the held-out drugs, the template split and the brand rule's results.
Splits: train 1,200, val 150, test_iid 100 (train templates and drugs), test_shift 120 (test-only templates
and the 10 held-out drugs only), test_codeswitch 50 (train templates and drugs, heavy Arabic-English mixing).

--vocab v2 (r2, plan.md amended 29 Oct) writes to finetune/data_v2/ by default: train and val as above, with
each training medicine's Spanish brands from evidence/data/drugs_v2.json (AEMPS CIMA) beside its US ones, and
test_spain 60 (train templates, said only by the Spanish brands held out of training). The 10 held-out drugs
are r1's, drawn the same way. v1 is untouched: the same seed writes the same files.
"""

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anamnesis.providers.stated import stated_amounts  # noqa: E402
from anamnesis.schema import AudioTurn  # noqa: E402
from finetune.common import (  # noqa: E402
    DATA_DIR,
    Amount,
    ClaimSpec,
    answer_text,
    chat_row,
    check_example,
    format_turns,
    number,
    write_jsonl,
)
from finetune.drugs import (  # noqa: E402
    DRUGS_V2_FILE,
    Medicine,
    Strength,
    dropped_brands,
    held_out_keys,
    load_medicines,
    load_medicines_v2,
    spain_medicines,
    spain_split,
)
from finetune.phrases import (  # noqa: E402
    AR_UNITS,
    CLOSERS,
    CONNECTORS,
    EN_UNITS,
    FORM,
    FRAMES,
    FREQ,
    KIND_WEIGHTS,
    OPENERS,
    PRN,
    RANGE_FREQ,
    RANGE_UNITS,
    UNITS,
    UNITS_WEIGHTS,
    WHEN,
    Frame,
    ar_words,
    digits,
    en_words,
    status_of,
)
from finetune.real_slice import distinct_transcripts  # noqa: E402

SEED = 20261029
NOISE_RATE = 0.25  # share of each split's notes given one speech-to-text slip of the kinds seen on 28 Oct
SPLITS = (("train", 1200), ("val", 150), ("test_iid", 100), ("test_shift", 120), ("test_codeswitch", 50))
SPLITS_V2 = (("train", 1200), ("val", 150), ("test_spain", 60))
DATA_V2_DIR = DATA_DIR.parent / "data_v2"
STANDARD_MIX = (("en", 45), ("ar", 40), ("light", 15))  # light: Arabic templates, Latin names, some English
CODESWITCH_MIX = (("heavy", 1),)  # heavy: each template and each slot in either language
MEDS_PER_NOTE = ((1, 40), (2, 35), (3, 25))
MULTI_TURN_SHARE = 0.35  # of notes with two or more sentences
STRIP_PUNCTUATION_SHARE = 0.5  # Voice Transcribe sometimes returned no punctuation at all
WORDS_SHARE = 0.5  # amounts in words rather than digits, where the language can say them
INDIC_SHARE = 0.2  # Arabic-Indic digits, of Arabic amounts written as digits
NOISE_KINDS = ("repeat_word", "repeat_number", "double_brand", "runon_brand")

SLOT = re.compile(r"\{(\w+)\}")
NUMBER_SLOTS = ("dose", "sdose", "sdose_pl")
WORD_SLOTS = ("freq", "prn", "when", "units", "range_units", "range_freq")
MIXABLE = ("number", "unit", "freq", "prn", "when", "units", "range_units", "range_freq")
ARABIC = re.compile(r"[؀-ۿ]")
WORD = re.compile(r"\S+")
NOT_REPEATED = ("and", "a", "point", "و", "not", "no", "مش", "لا")
END_PUNCTUATION = re.compile(r"[.,،](?=\s|$)")


@dataclass(frozen=True)
class Token:
    kind: str  # "lit" or a slot name
    text: str
    unit: str = ""  # number slots: the unit words said after the number
    value: Decimal | None = None  # number slots: the amount

    def render(self) -> str:
        return f"{self.text} {self.unit}" if self.unit else self.text


@dataclass
class Mention:
    medicine: Medicine
    frame: Frame
    parts: list[list[Token]]
    name_slot: str
    name: str
    name_is_brand: bool
    connector: str
    fields: dict = field(default_factory=dict)  # ClaimSpec fields other than name_text and turn_ids


@dataclass(frozen=True)
class Note:
    turns: list[AudioTurn]
    specs: list[ClaimSpec]
    mentions: list[Mention]
    mix: str
    noise: list[dict]


def weighted(rng: random.Random, options: tuple[tuple[object, int], ...]) -> object:
    return rng.choices([option for option, _ in options], weights=[weight for _, weight in options])[0]


def slots_of(frame: Frame) -> list[str]:
    return list(dict.fromkeys(SLOT.findall(frame.text)))


def name_pools(medicine: Medicine, mode: str) -> tuple[list[str], list[str]]:
    """(brand names, ingredient names) a patient in this mode may say."""
    latin, arabic = list(medicine.brands), list(medicine.aliases)
    brands = {"en": latin, "light": latin, "ar": arabic or latin, "heavy": arabic + latin}[mode]
    return brands, list(medicine.ingredient_names)


def fits(frame: Frame, medicine: Medicine, mode: str) -> bool:
    slots = slots_of(frame)
    brands, ingredients = name_pools(medicine, mode)
    if set(slots) & set(NUMBER_SLOTS) and not medicine.strengths:
        return False
    if "inn" in slots:
        return bool(brands and ingredients)
    return bool(brands or ingredients)


def pick_frame(rng: random.Random, frames: list[Frame], lang: str, medicine: Medicine, mode: str) -> Frame:
    usable: dict[str, list[Frame]] = {}
    for frame in frames:
        if frame.lang == lang and fits(frame, medicine, mode):
            usable.setdefault(frame.kind, []).append(frame)
    kinds = tuple((kind, weight) for kind, weight in KIND_WEIGHTS.items() if kind in usable)
    return rng.choice(usable[weighted(rng, kinds)])


def capitalised(text: str) -> str:
    return text[:1].upper() + text[1:] if text[:1].isascii() and text[:1].islower() else text


def pick_name(rng: random.Random, medicine: Medicine, mode: str, brand_only: bool) -> tuple[str, bool]:
    brands, ingredients = name_pools(medicine, mode)
    is_brand = bool(brands) and (brand_only or not ingredients or rng.random() < 0.65)
    name = rng.choice(brands if is_brand else ingredients)
    if is_brand and "-" in name:  # Voice Transcribe wrote Beloc-Zok as "BelocZok"
        name = rng.choices([name, name.replace("-", ""), name.replace("-", " ")], weights=[1, 2, 1])[0]
    return name, is_brand


def pick_dose(
    rng: random.Random, strength: Strength, number_lang: str, unit_lang: str, adjective: bool,
) -> tuple[Decimal, str, str, str]:
    """(value, unit, number words or digits, unit words). Under 1 mg may be said in micrograms, and a whole
    gram in English as grams; both are the marketed strength, said in the patient's unit."""
    value, unit = strength.mg, "mg"
    if value < 1 and rng.random() < 0.5:
        value, unit = value * 1000, "mcg"
    elif value >= 1000 and value % 1000 == 0 and unit_lang == "en" and rng.random() < 0.4:
        value, unit = value / 1000, "g"
    value = Decimal(number(value))
    words = None
    if rng.random() < WORDS_SHARE:
        words = en_words(value, rng) if number_lang == "en" else ar_words(value)
    said = words or digits(value, indic=number_lang == "ar" and rng.random() < INDIC_SHARE)
    if unit_lang == "en":
        plural, singular = EN_UNITS[unit]
        options = singular if adjective or value == 1 else plural
        unit_words = options[0] if words else rng.choice(options)
    else:
        unit_words = rng.choice(AR_UNITS[unit])
    return value, unit, said, unit_words


def pick_units(rng: random.Random, lang: str, form: str) -> tuple[Decimal, str]:
    rows = [(row, weight) for row, weight in zip(UNITS[lang], UNITS_WEIGHTS, strict=True)
            if row[1 if form == "tablet" else 2] is not None]
    count, tablets, capsules = weighted(rng, tuple(rows))
    return count, tablets if form == "tablet" else capsules


def _slot_langs(rng: random.Random, mode: str, frame_lang: str) -> dict[str, str]:
    if mode == "light":
        return {slot: "en" if rng.random() < 0.25 else "ar" for slot in MIXABLE}
    if mode == "heavy":
        return {slot: rng.choice(("en", "ar")) for slot in MIXABLE}
    return dict.fromkeys(MIXABLE, frame_lang)


def _tokens(part: str, values: dict[str, Token], later_part: bool) -> list[Token]:
    tokens, position = [], 0
    for match in SLOT.finditer(part):
        if match.start() > position:
            tokens.append(Token("lit", part[position:match.start()]))
        token = values[match.group(1)]
        if later_part and match.start() == 0 and token.kind in NUMBER_SLOTS:
            token = replace(token, text=capitalised(token.text))  # "Five milligrams once a day."
        tokens.append(token)
        position = match.end()
    if position < len(part):
        tokens.append(Token("lit", part[position:]))
    return tokens


def fill(
    rng: random.Random, frame: Frame, medicine: Medicine, mode: str, connector: str, sentence_start: bool,
) -> Mention:
    """Fill one template with choices, and record the claim those same choices mean."""
    slots = slots_of(frame)
    langs = _slot_langs(rng, mode, frame.lang)
    name, is_brand = pick_name(rng, medicine, mode, brand_only="inn" in slots)
    if sentence_start and frame.text.startswith("{name}"):
        name = capitalised(name)
    strength = rng.choice(medicine.strengths) if set(slots) & set(NUMBER_SLOTS) else None
    forms = strength.forms if strength else tuple(form for item in medicine.strengths for form in item.forms)
    form = "capsule" if forms and "tablet" not in forms else "tablet"  # tamsulosin is only ever a capsule
    said_inn = rng.choice(medicine.ingredient_names) if "inn" in slots else None
    fields: dict = {"status": status_of(frame), "inn": said_inn or (None if is_brand else name)}
    values: dict[str, Token] = {}
    for slot in slots:
        if slot in ("name", "al_name"):
            values[slot] = Token(slot, f"ال{name}" if slot == "al_name" and ARABIC.search(name) else name)
        elif slot in NUMBER_SLOTS:
            value, unit, said, unit_words = pick_dose(rng, strength, langs["number"], langs["unit"],
                                                      adjective=slot == "sdose")
            values[slot] = Token(slot, said, unit_words, value)
            if "range_units" not in slots:  # a range in the count drops the amount with it (SPEC §2)
                fields["intake" if slot == "dose" else "strength"] = Amount(value, unit, said_inn or name)
                if slot != "dose":
                    fields["per"] = form
        elif slot == "form":
            values[slot] = Token(slot, FORM[frame.lang][form])
        elif slot == "units":
            count, words = pick_units(rng, langs["units"], form)
            values[slot] = Token(slot, words)
            fields["units"] = count
        elif slot == "freq":
            words, per_day = rng.choice(FREQ[langs["freq"]])
            values[slot] = Token(slot, words)
            fields["per_day"] = Decimal(per_day)
        elif slot == "prn":
            values[slot] = Token(slot, rng.choice(PRN[langs["prn"]]))
            fields["as_needed"] = True
        elif slot == "when":
            values[slot] = Token(slot, rng.choice(WHEN[langs["when"]]))
        elif slot == "range_units":
            values[slot] = Token(slot, rng.choice(RANGE_UNITS[langs["range_units"]][form]))
        elif slot == "range_freq":
            values[slot] = Token(slot, rng.choice(RANGE_FREQ[langs["range_freq"]]))
        elif slot == "inn":
            values[slot] = Token(slot, said_inn)
    parts = [_tokens(part, values, index > 0) for index, part in enumerate(frame.text.split("|"))]
    name_slot = "al_name" if "al_name" in slots else "name"
    return Mention(medicine, frame, parts, name_slot, values[name_slot].text, is_brand, connector, fields)


# ------------------------------------------------------------------------------------------------ noise
def _is_numberish(word: str) -> bool:
    """Number words, and negations: "not not on" would blur the very status the answer records."""
    return bool(stated_amounts(word)) or word.casefold() in NOT_REPEATED


def _word_spans(text: str) -> list[tuple[int, int]]:
    """Whole words of letters only, without trailing punctuation, that aren't number words."""
    spans = []
    for match in WORD.finditer(text):
        core = match.group(0).rstrip(".,،")
        if core and all(ch.isalpha() for ch in core) and not _is_numberish(core):
            spans.append((match.start(), match.start() + len(core)))
    return spans


def noise_candidates(rng: random.Random, mentions: list[Mention]) -> dict[str, list[dict]]:
    """Every slip that fits this note, by kind, each with its exact position fixed now."""
    found: dict[str, list[dict]] = {kind: [] for kind in NOISE_KINDS}
    for m_index, mention in enumerate(mentions):
        for p_index, part in enumerate(mention.parts):
            for t_index, token in enumerate(part):
                where = {"mention": m_index, "part": p_index, "token": t_index}
                if token.kind == "lit" or token.kind in WORD_SLOTS:
                    spans = _word_spans(token.text)
                    if t_index == 0 and spans and spans[0][0] == 0:
                        spans = spans[1:]  # a first word may be lowercased after "And", so it isn't repeated
                    for s_index, span in enumerate(spans):
                        after = spans[s_index + 1] if s_index + 1 < len(spans) else None
                        adjacent = after is not None and token.text[span[1]:after[0]] == " "
                        phrase = adjacent and rng.random() < 0.3  # "once a once a day"
                        end = spans[s_index + 1][1] if phrase else span[1]
                        found["repeat_word"].append({"type": "repeat_word", **where, "span": (span[0], end)})
                elif token.kind in NUMBER_SLOTS:
                    cross = rng.random() < 0.25
                    found["repeat_number"].append({"type": "repeat_number", **where, "cross": cross})
                elif token.kind == mention.name_slot and mention.name_is_brand:
                    found["double_brand"].append({"type": "double_brand", **where})
                    found["runon_brand"].append({"type": "runon_brand", **where})
    return found


def apply_noise(mentions: list[Mention], slip: dict) -> tuple[list[Mention], str]:
    """The mentions with one slip applied, and the slipped words as they now read in the transcript."""
    mention = mentions[slip["mention"]]
    token = mention.parts[slip["part"]][slip["token"]]
    text = token.text
    if slip["type"] == "repeat_word":
        start, end = slip["span"]
        said = f"{text[start:end]} {text[start:end]}"
        text = f"{text[:start]}{said}{text[end:]}"
    elif slip["type"] == "repeat_number":
        # "ten ten", "10 10" or "ten 10", as on 28 Oct. Several number words repeat only as "words digits":
        # "twenty five twenty five" would state 50, not 25.
        words = not any(ch.isdigit() for ch in text)
        cross = words and (slip["cross"] or len(text.split()) > 1)
        said = text = f"{text} {number(token.value) if cross else text}"
    elif slip["type"] == "double_brand":
        said = text = f"{text} {text}"
    else:  # runon_brand: the end of the name said again and run together, "BelocZokZok"
        said = text = text + text[-3:]
    parts = [list(part) for part in mention.parts]
    parts[slip["part"]][slip["token"]] = replace(token, text=text)
    changed = [*mentions[:slip["mention"]], replace(mention, parts=parts), *mentions[slip["mention"] + 1:]]
    return changed, said


def amounts_stated(specs: list[ClaimSpec], turns: list[AudioTurn]) -> bool:
    """Whether every intended amount is still stated in the turns its claim cites, as the product requires."""
    texts = {turn.turn_id: turn.transcript for turn in turns}
    for spec in specs:
        said: set[Decimal] = set()
        for turn_id in spec.turn_ids:
            said |= stated_amounts(texts[turn_id])
        if any(amount is not None and amount.value not in said for amount in (spec.intake, spec.strength)):
            return False
    return True


# ------------------------------------------------------------------------------------------------ notes
def tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"\s+([.,،])", r"\1", text).strip()


def _join(prefix: str, sentence: str, literal_start: bool) -> str:
    """A connector, or an opener ending in a comma, runs on into the sentence: "And my Concor ...". Only a
    template's own first word is lowercased, never a name."""
    if not prefix:
        return sentence
    if literal_start and prefix.endswith((",", "،", " ")) and not sentence.startswith(("I ", "I'")):
        sentence = sentence[:1].lower() + sentence[1:] if sentence[:1].isascii() else sentence
    return f"{prefix}{sentence}" if prefix.endswith((" ", "و")) else f"{prefix} {sentence}"


@dataclass(frozen=True)
class Layout:
    opener: str
    closer: str
    multi_turn: bool
    strip: bool
    lang: str
    timing: tuple[int, tuple[int, ...], tuple[float, ...]]  # first start, gaps, length factors


def render(mentions: list[Mention], layout: Layout) -> tuple[list[AudioTurn], list[ClaimSpec]]:
    sentences: list[tuple[int, str]] = []
    for m_index, mention in enumerate(mentions):
        for p_index, part in enumerate(mention.parts):
            text = tidy("".join(token.render() for token in part))
            if p_index == 0:
                text = _join(mention.connector, text, part[0].kind == "lit")
            sentences.append((m_index, text))
    groups = [[sentence] for sentence in sentences] if layout.multi_turn else [sentences]
    texts = [" ".join(text for _, text in group) for group in groups]
    first = mentions[0].parts[0][0]
    texts[0] = _join(layout.opener, texts[0], first.kind == "lit")
    texts[-1] = f"{texts[-1]} {layout.closer}".strip()
    if layout.strip:
        texts = [tidy(END_PUNCTUATION.sub("", text)) for text in texts]
    start, gaps, factors = layout.timing
    turns = []
    for index, text in enumerate(texts):
        per_char = 118 if len(ARABIC.findall(text)) * 3 > len(text) else 57
        end = start + max(600, round(len(text) * per_char * factors[index] / 20) * 20)
        turns.append(AudioTurn(turn_id=f"turn-{index}", start_ms=start, end_ms=end, transcript=text,
                               lang_hint=layout.lang))
        start = end + gaps[index]
    specs = []
    for m_index, mention in enumerate(mentions):
        cited = tuple(dict.fromkeys(
            f"turn-{g_index}"
            for g_index, group in enumerate(groups) for owner, _ in group if owner == m_index
        ))
        specs.append(ClaimSpec(name_text=mention.name, turn_ids=cited, **mention.fields))
    return turns, specs


def pick_medicines(rng: random.Random, pool: list[Medicine], count: int) -> list[Medicine]:
    """Distinct medicines sharing no ingredient, so no note names one drug twice."""
    chosen: list[Medicine] = []
    while len(chosen) < count:
        taken = {inn for medicine in chosen for inn in medicine.inns}
        options = [medicine for medicine in pool if not taken & set(medicine.inns)]
        chosen.append(rng.choice(options))
    return chosen


def make_note(
    rng: random.Random, pool: list[Medicine], frames: list[Frame], mix: tuple, noisy: bool,
) -> tuple[Note, int]:
    """One note and the number of slips refused because they would have unstated an intended amount."""
    mode = weighted(rng, mix)
    note_lang = {"en": "en", "ar": "ar", "light": "ar"}.get(mode) or rng.choice(("en", "ar"))
    opener, closer = rng.choice(OPENERS[note_lang]), rng.choice(CLOSERS[note_lang])
    mentions = []
    for index, medicine in enumerate(pick_medicines(rng, pool, weighted(rng, MEDS_PER_NOTE))):
        lang = {"en": "en", "ar": "ar", "light": "ar"}.get(mode) or rng.choice(("en", "ar"))
        frame = pick_frame(rng, frames, lang, medicine, mode)
        connector = rng.choice(CONNECTORS[lang]) if index else ""
        if connector.strip(" ,").casefold().removeprefix("و") in ("also", "كمان") and (
            "also" in frame.text or "كمان" in frame.text
        ):
            connector = ""  # not "Also, I'm also on"
        if connector == "و" and frame.text.startswith("{"):
            connector = "وكمان "  # «و» never joins a name
        start = connector == "" and not (index == 0 and opener.endswith((",", "،")))
        mentions.append(fill(rng, frame, medicine, mode, connector, start))
    parts = sum(len(mention.parts) for mention in mentions)
    multi = parts > 1 and rng.random() < MULTI_TURN_SHARE
    turns_count = parts if multi else 1
    timing = (
        0 if rng.random() < 0.9 else rng.choice((60, 100, 140, 200)),
        tuple(round(rng.uniform(200, 900) / 20) * 20 for _ in range(turns_count)),
        tuple(rng.uniform(0.9, 1.1) for _ in range(turns_count)),
    )
    layout = Layout(opener, closer, multi, rng.random() < STRIP_PUNCTUATION_SHARE, note_lang, timing)
    noise, refused = [], 0
    if noisy:
        candidates = noise_candidates(rng, mentions)
        while any(candidates.values()):
            kind = rng.choice([kind for kind in NOISE_KINDS if candidates[kind]])
            slip = candidates[kind].pop(rng.randrange(len(candidates[kind])))
            slipped, said = apply_noise(mentions, slip)
            turns, specs = render(slipped, layout)
            if amounts_stated(specs, turns):  # "twenty five twenty five" states 50, not 25: try another slip
                noise = [{"type": kind, "mention": slip["mention"], "text": said}]
                mentions = slipped
                break
            refused += 1
    turns, specs = render(mentions, layout)
    return Note(turns, specs, mentions, mode, noise), refused


# ------------------------------------------------------------------------------------------------ splits
def _sidecar(split: str, index: int, note: Note, parsed: list) -> dict:
    return {
        "index": index,
        "id": f"{split}-{index:04d}",
        "split": split,
        "mix": note.mix,
        "langs": [mention.frame.lang for mention in note.mentions],
        "templates": [mention.frame.id for mention in note.mentions],
        "drugs": [mention.medicine.key for mention in note.mentions],
        "noise": note.noise,
        "turns": [turn.model_dump() for turn in note.turns],
        "claims": [claim.model_dump(mode="json") for claim in parsed],
    }


def generate(out: Path = DATA_DIR, seed: int = SEED, vocab: str = "v1") -> dict:
    """Write every split and meta.json to `out`; return the meta."""
    medicines = load_medicines()
    held = held_out_keys(medicines, seed + 1)
    splits, spain, spanish = SPLITS, [], None
    if vocab == "v2":
        trained, held_spanish = spain_split(medicines, held, seed + 2)
        spain = spain_medicines(held_spanish, medicines)
        medicines = load_medicines_v2(trained)
        splits, spanish = SPLITS_V2, {"trained": trained, "held_out": held_spanish}
    training = [medicine for medicine in medicines if medicine.key not in held]
    shifted = [medicine for medicine in medicines if medicine.key in held]
    train_frames = [frame for frame in FRAMES if not frame.test_only]
    test_frames = [frame for frame in FRAMES if frame.test_only]
    plans = {
        "train": (training, train_frames, STANDARD_MIX), "val": (training, train_frames, STANDARD_MIX),
        "test_iid": (training, train_frames, STANDARD_MIX),
        "test_shift": (shifted, test_frames, STANDARD_MIX),
        "test_codeswitch": (training, train_frames, CODESWITCH_MIX),
        "test_spain": (spain, train_frames, STANDARD_MIX),
    }
    rng = random.Random(seed)
    # No generated note may repeat a transcript of the real slice word for word ("I take Concor five ...").
    seen = {tuple(turn.transcript for turn in entry["turns"]) for entry in distinct_transcripts()}
    stats: dict = {"refused_slips": 0, "duplicates_redrawn": 0, "splits": {}}
    for split, size in splits:
        pool, frames, mix = plans[split]
        rows, sidecars = [], []
        noisy_slots = set(rng.sample(range(size), round(size * NOISE_RATE)))  # an exact share per split
        while len(rows) < size:
            note, refused = make_note(rng, pool, frames, mix, noisy=len(rows) in noisy_slots)
            stats["refused_slips"] += refused
            key = tuple(turn.transcript for turn in note.turns)
            if key in seen:
                stats["duplicates_redrawn"] += 1
                continue
            seen.add(key)
            answer = answer_text(note.specs)
            parsed = check_example(note.turns, note.specs, answer)
            rows.append(chat_row(format_turns(note.turns), answer))
            sidecars.append(_sidecar(split, len(sidecars), note, parsed))
        write_jsonl(out / f"{split}.jsonl", rows)
        write_jsonl(out / f"{split}.answers.jsonl", sidecars)
        noisy = sum(1 for sidecar in sidecars if sidecar["noise"])
        stats["splits"][split] = {
            "examples": len(rows), "claims": sum(len(sidecar["claims"]) for sidecar in sidecars),
            "noisy": noisy, "noise_share": round(noisy / len(rows), 3),
        }
    meta = {
        "seed": seed,
        "noise_rate": NOISE_RATE,
        **stats,
        "held_out": [
            {"key": item.key, "inn": item.inns[0], "rxcui": item.rxcui, "brands": list(item.brands)}
            for item in shifted
        ],
        "templates": {
            "train": [frame.id for frame in train_frames], "test_only": [frame.id for frame in test_frames],
        },
        "rxnorm_brands_kept": {
            medicine.inns[0]: list(medicine.brands) for medicine in medicines if medicine.source == "rxnorm"
        },
        "rxnorm_brands_dropped": dropped_brands(),
    }
    if spanish is not None:
        meta = {**meta, "vocab": "v2", "spanish_brands": spanish,
                "drugs_v2_read": json.loads(DRUGS_V2_FILE.read_text(encoding="utf-8"))["meta"]["fetched"]}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", type=Path, default=None, help="finetune/data, or finetune/data_v2 for v2")
    parser.add_argument("--vocab", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    args.out = args.out or (DATA_V2_DIR if args.vocab == "v2" else DATA_DIR)
    args.out.mkdir(parents=True, exist_ok=True)
    meta = generate(args.out, args.seed, args.vocab)
    for split, row in meta["splits"].items():
        print(f"{split:16} {row['examples']:5} examples, {row['claims']:5} claims, noise in {row['noisy']} "
              f"({row['noise_share']:.1%})")
    print("held out:", ", ".join(item["inn"] for item in meta["held_out"]))
    print(f"refused slips {meta['refused_slips']}, duplicates redrawn {meta['duplicates_redrawn']}; "
          f"files in {args.out}")


if __name__ == "__main__":
    main()
