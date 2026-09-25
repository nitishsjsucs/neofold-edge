"""Guardrails on the local language-model summary.

The tests that matter are the ones that reject output. A model summarising
evidence can fail in two distinct ways, and we saw both on the first run.
"""
import pytest

from neofold.report import (BANNED_CLAIMS, DISCLAIMER, EvidenceCard,
                            fallback_summary, find_banned_claims,
                            verify_no_invented_numbers)

CARD = EvidenceCard(
    candidate_id="KRAS G12D", peptide="GADGVGKSA", wt_peptide="GAGGVGKSA",
    allele="HLA-C*08:02", affinity_nm=74.1, wt_affinity_nm=3656.5,
    affinity_percentile=0.188, binder_class="strong", wt_binder_class="non-binder",
    dai=23.5, mutation_site="TCR-facing", self_verdict="not-self",
    structure={"iptm": 0.9906},
    contact={"peptide_residue": "ASP3", "mhc_residue": "ARG156", "min_distance_a": 2.58},
)


def test_facts_contain_the_key_numbers():
    joined = " ".join(CARD.as_facts())
    for token in ("74", "3656", "23.5", "0.188", "2.58", "TCR-facing"):
        assert token in joined


def test_restating_a_supplied_number_passes():
    assert verify_no_invented_numbers("Affinity is 74 nM.", CARD.as_facts()) == []


def test_inventing_a_number_is_caught():
    bad = "It binds at 74 nM and shows 92 percent response."
    assert "92" in verify_no_invented_numbers(bad, CARD.as_facts())


def test_small_prose_numerals_are_not_flagged():
    """'three chains' is prose, not fabricated data."""
    assert verify_no_invented_numbers("There are three chains.", CARD.as_facts()) == []


def test_rounding_a_supplied_number_is_allowed():
    facts = ["Predicted affinity: 74.065 nM"]
    assert verify_no_invented_numbers("about 74 nM", facts) == []


# --- the second failure mode: correct numbers, unlicensed conclusions -------

def test_the_three_claims_our_first_run_actually_made_are_caught():
    """Verbatim from the first local run. Every number was correct; all three
    interpretations were wrong, and the third is contradicted by our own
    measurements of ipTM."""
    for claim in [
        "the index of 23.5, enhancing its immunogenic potential",
        "the percentile rank highlights its rarity within the human proteome",
        "the ipTM supports the reliability of the modeled interaction",
    ]:
        assert find_banned_claims(claim), f"not caught: {claim}"


def test_clinical_language_is_banned():
    for word in ("vaccine", "therapy", "patient", "cure"):
        assert find_banned_claims(f"This informs the {word} decision.")


def test_a_pure_restatement_passes_both_checks():
    good = ("The predicted affinity is 74 nM, classified strong. The germline "
            "counterpart is 3656 nM, classified non-binder. The mutation is at "
            "a TCR-facing position.")
    assert verify_no_invented_numbers(good, CARD.as_facts()) == []
    assert find_banned_claims(good) == []


def test_disclaimer_is_a_constant_not_generated():
    """It is concatenated by code so it cannot drift or be paraphrased away."""
    assert "not a diagnosis" in DISCLAIMER
    assert "vaccine design" in DISCLAIMER
    # And the model is explicitly told not to write one.
    from neofold.report import SYSTEM_RULES
    assert "appended separately" in SYSTEM_RULES


def test_fallback_needs_no_model_and_states_only_facts():
    text = fallback_summary(CARD)
    assert "74" in text and "3656" in text and "TCR-facing" in text
    assert find_banned_claims(text) == []
    assert verify_no_invented_numbers(text, CARD.as_facts()) == []


def test_banned_list_covers_the_conclusions_we_proved_false():
    """ipTM does not indicate reliability -- we showed that five times."""
    for term in ("reliability", "immunogenic", "supports the"):
        assert term in BANNED_CLAIMS
