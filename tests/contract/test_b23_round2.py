"""Batch 23 contract, round 2: the supervisor's findings (evidence/batches/23/supervisor.md, #1-#6), the Gemini 4
check of round 1 (evidence/grills/m6-timeline/qm.md, #3, #4, #6) and Muse's own report. Written by the CEO; Muse must
not edit it.

- The volume rule (SPEC §2 "A volume other than 1 ml") missed the Arabic decimal sign, IU, cc, the Unicode slashes,
  "لكل", "each", a spoon and the volume-first wording, so a strength printed per 5 ml was kept. And «مل» matched the
  start of «ملجم», so Arabic combination tablets lost theirs.
- The call budget (SPEC §4 Budget): with a fixed 12, the third SAM concept ran it out on a four-photo intake, and a
  pack the patient had sent was reported as not photographed.
- A requested photo (add_photo) used two concepts, and nothing checked that its steps add up to spend_usd.
"""

import inspect
import json
from decimal import Decimal

import pytest

from anamnesis.agent import run_intake
from anamnesis.providers.base import ProviderTrace
from anamnesis.providers.spark import parse_label_json
from anamnesis.review import add_photo, new_review, request_photo
from anamnesis.schema.report import AgentAction
from tests.contract import test_b19_brief as b19
from tests.contract import test_b20_review as b20


def label(text, *parts, per="ml"):
    ingredients = [{"inn": inn, "amount": amount, "unit": unit} for inn, amount, unit in parts]
    return json.dumps({"label_text": text, "inn": parts[0][0], "country": None, "readability": "readable",
                       "strength": {"ingredients": ingredients, "per": per, "release": "unknown"}})


PARACETAMOL_250 = ("paracetamol", "250", "mg")

# --- the volume rule: what it drops ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,part", [
    ("باراسيتامول ٢٫٥ مجم / ٥ مل", ("paracetamol", "2.5", "mg")),
    ("Drops ٢٫٥ مجم/٥ مل", ("paracetamol", "2.5", "mg")),
    ("Drops 2٫5 mg/5 ml", ("paracetamol", "2.5", "mg")),
    ("Paracetamol 2.5 mg / 5 ml", ("paracetamol", "2.5", "mg")),
    ("Vitamin D3 400 IU / 5 ml", ("colecalciferol", "400", "iu")),
    ("Vitamin D3 100000 IU/5 ml", ("colecalciferol", "100000", "iu")),
    ("Each 5 ml contains paracetamol 250 mg", PARACETAMOL_250),
    ("كل ٥ مل تحتوي على باراسيتامول ٢٥٠ مجم", PARACETAMOL_250),
    ("باراسيتامول ٢٥٠ مجم لكل ٥ مل", PARACETAMOL_250),
    ("Paracetamol 250 mg in each 5 ml", PARACETAMOL_250),
    ("Paracetamol 250 mg per teaspoonful (5 ml)", PARACETAMOL_250),
    ("Paracetamol 250mg/5cc", PARACETAMOL_250),
    ("Amoxil 250/5 ml", ("amoxicillin", "250", "mg")),
    ("Paracetamol 250 mg∕5 ml", PARACETAMOL_250),
    ("Paracetamol 250 mg／5 ml", PARACETAMOL_250),
])
@pytest.mark.parametrize("per", ["ml", "dose", "tablet"])
def test_a_strength_printed_per_a_volume_other_than_1_ml_is_dropped(text, part, per):
    reading = parse_label_json(label(text, part, per=per), "r1")
    assert reading.strength is None
    assert reading.label_text == text


# --- the volume rule: what it keeps ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,parts,per", [
    ("Paracetamol 250 mg / ml", [PARACETAMOL_250], "ml"),
    ("Paracetamol 250 mg / 1.0 ml", [PARACETAMOL_250], "ml"),
    ("Cetirizine 5 mg/ml, 5 ml bottle", [("cetirizine", "5", "mg")], "ml"),
    ("Ibuprofen 100 mg tablets, 100 ml", [("ibuprofen", "100", "mg")], "tablet"),
    ("Panadol 500 mg effervescent, dissolve in 100 ml of water", [("paracetamol", "500", "mg")], "tablet"),
    ("Augmentin ٨٧٥ ملجم/١٢٥ ملجم أقراص", [("amoxicillin", "875", "mg"), ("clavulanic acid", "125", "mg")], "tablet"),
    ("Augmentin 875 mg/125 mg tablets", [("amoxicillin", "875", "mg"), ("clavulanic acid", "125", "mg")], "tablet"),
])
def test_a_volume_that_is_not_the_amounts_denominator_keeps_the_strength(text, parts, per):
    reading = parse_label_json(label(text, *parts, per=per), "r1")
    assert reading.strength is not None
    assert [part.amount for part in reading.strength.ingredients] == [Decimal(amount) for _, amount, _ in parts]


# --- the call budget covers every call ------------------------------------------------------------------------

def photo(colour):
    return b19.png(600, 300, colour)


class ByPhoto:
    """SAM that finds the given region on a photo only with the given concept."""

    def __init__(self, plan):
        self.plan = plan  # sha256 -> (concept, region)

    def segment(self, image, concept, *, mime):
        import hashlib
        wanted, region = self.plan[hashlib.sha256(image).hexdigest()]
        return ([region] if concept == wanted else []), b19.trace("sam")


def test_four_photos_with_package_only_packs_still_reach_the_last_photo():
    photos = [photo((200, 200, 200)), photo((190, 210, 200)), photo((210, 190, 200)), photo((200, 200, 190))]
    regions = [b19.region_on(image, (10, 20, 139, 279), 0, 0.9) for image in photos]
    plan = {region.image_sha256: ("package", region) for region in regions[:3]}
    plan[regions[3].image_sha256] = ("medicine box", regions[3])
    norvasc = b19.reading("Norvasc 5 mg\nAmlodipine", b19.st(b19.mg("amlodipine", 5)))
    concor = b19.reading("Concor 5 mg\nBisoprolol fumarate", b19.st(b19.mg("bisoprolol fumarate", 5)))
    reads = {region.region_id: [norvasc] for region in regions[:3]} | {regions[3].region_id: [concor]}
    report = run_intake(b19.AUDIO[0], [(image, "image/png") for image in photos],
                        transcriber=b19.Transcriber(b19.TURNS[:1]), extractor=b19.Extractor(b19.CLAIMS[:1]),
                        segmenter=ByPhoto(plan), reader=b19.Reader(reads), catalogue=b19.CAT)
    assert AgentAction.BUDGET_EXHAUSTED not in [step.action for step in report.steps]
    assert [finding.type.value for finding in report.findings if finding.claim_id == "c1"] == ["match"]


def test_an_explicit_budget_still_caps_the_calls():
    report = run_intake(b19.AUDIO[0], [(b19.PHOTO, "image/png")], transcriber=b19.Transcriber(b19.TURNS),
                        extractor=b19.Extractor(b19.CLAIMS), segmenter=b19.Segmenter({b19.RC.image_sha256: [b19.RC]}),
                        reader=b19.Reader(b19.reads()), catalogue=b19.CAT, max_provider_calls=2)
    assert report.calls == 2
    assert report.steps[-1].action is AgentAction.BUDGET_EXHAUSTED or AgentAction.BUDGET_EXHAUSTED in [
        step.action for step in report.steps]


# --- a requested photo: the same concepts, and its steps add up --------------------------------------------------

class Recorder:
    """Finds nothing, and records every concept it is asked for."""

    def __init__(self):
        self.asked = []

    def segment(self, image, concept, *, mime):
        self.asked.append(concept)
        return [], ProviderTrace(call_id=f"s{len(self.asked)}", model_id="sam-3.1", latency_ms=1, input_tokens=0,
                                 output_tokens=0, cost_usd=Decimal("0.0025"))


def test_add_photo_and_run_intake_share_their_default_concepts():
    shared = inspect.signature(run_intake).parameters["concepts"].default
    assert shared == ("medicine box", "label", "package")
    assert inspect.signature(add_photo).parameters["concepts"].default == shared


def test_a_requested_photo_asks_all_three_concepts():
    report = b20.first_intake()
    review = request_photo(new_review(report), report, "o1")
    [request] = review.requests
    segmenter = Recorder()
    add_photo(report, review, request.request_id, (b20.PHOTO2, "image/png"), b20.IMAGES, b20.AUDIO,
              segmenter=segmenter, reader=b20.Reader({}), catalogue=b20.CAT)
    assert segmenter.asked == ["medicine box", "label", "package"]


def test_after_a_requested_photo_the_steps_still_add_up_to_the_spend():
    report = b20.first_intake()
    review = request_photo(new_review(report), report, "o1")
    [request] = review.requests
    new_report, _, _, _ = b20.answer(report, review, request.request_id)
    assert new_report.spend_usd > report.spend_usd
    assert sum((step.cost_usd for step in new_report.steps), Decimal(0)) == new_report.spend_usd
