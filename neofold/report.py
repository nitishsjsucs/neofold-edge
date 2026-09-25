"""Local plain-language summary of the evidence for one candidate.

DESIGN CONSTRAINT. The model is given structured facts and asked to restate
them. It does not compute anything, does not decide anything, and does not
write the disclaimer -- that is appended by code. A language model is used
here for exactly one thing: turning a row of numbers into a paragraph a
human can read.

Two guardrails enforce that:

  * `verify_no_invented_numbers` checks every numeric token in the output
    against the facts that went in. A model that invents an affinity or a
    percentage fails the check and the summary is rejected.
  * The disclaimer is concatenated, never generated, so it cannot drift.

Everything runs on the local Ollama instance; no text leaves the machine.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:8b"

DISCLAIMER = (
    "Research prioritisation only. Every value above is a prediction, not a "
    "measurement. This is not a diagnosis, a treatment recommendation, or a "
    "vaccine design, and it requires expert review and laboratory validation."
)

SYSTEM_RULES = """You are writing one short paragraph for a computational biologist.

Rules you must follow exactly:
- Use ONLY the facts given below. Do not add any number that is not in them.
- RESTATE the facts. Do not interpret them, do not say what they imply, and
  do not say that one fact supports, confirms, enhances or validates another.
- Do not claim anything about immunogenicity, reliability, confidence in the
  result, rarity, or potential. Those conclusions are not in the facts.
- Do not speculate about clinical benefit, treatment, or patient outcome.
- Do not use the words "vaccine", "therapy", "cure", "treat" or "patient".
- Say "predicted" whenever you mention a computed value.
- Three to five sentences. Plain prose, no bullet points, no headings.
- Do not add a disclaimer; one is appended separately."""

# Interpretive claims the evidence does not license. A model can pass numeric
# verification while still asserting these, and in our first run it asserted
# three of them: that the differential "enhanced immunogenic potential", that
# a percentile rank showed "rarity within the human proteome", and that ipTM
# "supports the reliability" of the interaction. All three are wrong, and the
# third is contradicted by our own measurements.
BANNED_CLAIMS = [
    "immunogenic", "immunogenicity", "reliability", "reliable",
    "supports the", "confirms", "validates", "proves", "demonstrates that",
    "potential", "rarity", "rare", "efficacy", "effective",
    "vaccine", "therapy", "therapeutic", "treat", "cure", "patient",
    "likely to be recognised", "likely to be recognized",
]


@dataclass
class EvidenceCard:
    """The facts, and only the facts, that go to the model."""
    candidate_id: str
    peptide: str
    wt_peptide: str
    allele: str
    affinity_nm: float
    wt_affinity_nm: float
    affinity_percentile: float | None
    binder_class: str
    wt_binder_class: str
    dai: float
    mutation_site: str
    self_verdict: str | None = None
    self_protein: str | None = None
    structure: dict | None = None
    contact: dict | None = None
    md: dict | None = None

    def as_facts(self) -> list[str]:
        f = [
            f"Candidate: {self.candidate_id}",
            f"Mutant peptide {self.peptide}, germline counterpart {self.wt_peptide}",
            f"HLA allele: {self.allele}",
            f"Predicted affinity: {self.affinity_nm:.0f} nM (classified {self.binder_class})",
            f"Germline predicted affinity: {self.wt_affinity_nm:.0f} nM "
            f"(classified {self.wt_binder_class})",
            f"Differential agretopicity index: {self.dai:.1f}",
            f"The mutation sits at a {self.mutation_site} position in the peptide",
        ]
        if self.affinity_percentile is not None:
            f.append(f"Predicted percentile rank: {self.affinity_percentile:.3f} percent")
        if self.self_verdict:
            f.append(f"Human proteome search: {self.self_verdict}" +
                     (f" (closest match {self.self_protein})" if self.self_protein else ""))
        if self.structure:
            f.append(f"Predicted structure confidence ipTM: {self.structure['iptm']:.3f}")
        if self.contact and self.contact.get("min_distance_a") is not None:
            f.append(f"Pre-registered contact {self.contact['peptide_residue']} to "
                     f"{self.contact['mhc_residue']}: {self.contact['min_distance_a']} angstroms")
        if self.md:
            f.append(f"Short molecular dynamics run: contact persistence "
                     f"{self.md['contact_persistence']:.2f} over "
                     f"{self.md['production_ns']:.2f} nanoseconds")
        return f


@dataclass
class Report:
    candidate_id: str
    summary: str
    facts: list[str]
    disclaimer: str = DISCLAIMER
    model: str = MODEL
    wall_seconds: float = 0.0
    verified: bool = True
    rejected_reason: str | None = None
    invented_numbers: list[str] = field(default_factory=list)
    banned_claims: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"candidate_id": self.candidate_id, "summary": self.summary,
                "facts": self.facts, "disclaimer": self.disclaimer,
                "model": self.model, "generated_locally": True,
                "wall_seconds": round(self.wall_seconds, 1),
                "verified": self.verified,
                "rejected_reason": self.rejected_reason,
                "invented_numbers": self.invented_numbers,
                "banned_claims": self.banned_claims}


NUMBER = re.compile(r"\d+(?:\.\d+)?")


def verify_no_invented_numbers(summary: str, facts: list[str]) -> list[str]:
    """Numeric tokens in the summary that do not appear in the facts.

    Deliberately strict about magnitudes and deliberately lenient about
    rounding: a model writing "74" for 74.065 is restating, while one writing
    "92" for nothing is inventing. Small integers up to 20 are ignored because
    they are almost always prose ("three sentences", "one contact") rather
    than data.
    """
    allowed: set[str] = set()
    for fact in facts:
        for tok in NUMBER.findall(fact):
            allowed.add(tok)
            allowed.add(tok.rstrip("0").rstrip("."))
            try:
                allowed.add(f"{round(float(tok))}")
                allowed.add(f"{float(tok):.1f}")
                allowed.add(f"{float(tok):.2f}")
            except ValueError:
                pass
    invented = []
    for tok in NUMBER.findall(summary):
        if tok in allowed:
            continue
        try:
            if float(tok) <= 20 and "." not in tok:
                continue            # prose numerals, not data
        except ValueError:
            pass
        invented.append(tok)
    return sorted(set(invented))


def find_banned_claims(summary: str) -> list[str]:
    """Interpretive assertions the facts do not license."""
    low = summary.lower()
    return sorted({p for p in BANNED_CLAIMS if p in low})


def generate(card: EvidenceCard, url: str = OLLAMA_URL, model: str = MODEL,
             timeout: float = 240.0) -> Report:
    """Ask the local model to restate the evidence, then verify it did."""
    import time

    facts = card.as_facts()
    prompt = (SYSTEM_RULES + "\n\nFacts:\n" +
              "\n".join(f"- {x}" for x in facts) +
              "\n\nWrite the paragraph now.")
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": 0.2, "num_predict": 260},
    }).encode()

    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = json.loads(resp.read())["response"].strip()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Report(card.candidate_id, summary="", facts=facts,
                      wall_seconds=time.perf_counter() - t0,
                      verified=False,
                      rejected_reason=f"local model unavailable: {exc}")
    wall = time.perf_counter() - t0

    invented = verify_no_invented_numbers(text, facts)
    banned = find_banned_claims(text)
    if invented or banned:
        reasons = []
        if invented:
            reasons.append("contained numbers absent from the supplied evidence")
        if banned:
            reasons.append("asserted conclusions the evidence does not license")
        return Report(card.candidate_id, summary="", facts=facts,
                      wall_seconds=wall, verified=False,
                      invented_numbers=invented, banned_claims=banned,
                      rejected_reason="summary rejected: " + " and ".join(reasons))
    return Report(card.candidate_id, summary=text, facts=facts, wall_seconds=wall)


def fallback_summary(card: EvidenceCard) -> str:
    """Deterministic template, used when no local model is available.

    The demo must not depend on a language model being up, and a template is
    honest about being one.
    """
    bits = [
        f"{card.candidate_id} is a {card.binder_class} predicted binder for "
        f"{card.allele} at {card.affinity_nm:.0f} nM.",
        f"Its germline counterpart {card.wt_peptide} is predicted to be a "
        f"{card.wt_binder_class} binder at {card.wt_affinity_nm:.0f} nM, "
        f"a differential agretopicity index of {card.dai:.1f}.",
        f"The mutation sits at a {card.mutation_site} position, which is how "
        f"that differential should be read.",
    ]
    if card.contact and card.contact.get("min_distance_a") is not None:
        bits.append(
            f"In the predicted structure the pre-registered contact "
            f"{card.contact['peptide_residue']}–{card.contact['mhc_residue']} "
            f"measures {card.contact['min_distance_a']} Å.")
    return " ".join(bits)
