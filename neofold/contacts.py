"""Specific, pre-registered contact measurements in a peptide-MHC complex.

Why this exists: we measured that Boltz's own confidence scores barely
distinguish a correct peptide/allele pairing from a deliberately wrong one.
So if the UI is going to claim anything structural, it has to measure a
named, chemically-motivated contact that was specified in advance from an
experimental structure -- not go fishing through a predicted model for
whatever looks different.

The KRAS G12D / HLA-C*08:02 case has exactly such a contact. HLA-C*08:02 has
a strong preference for Asp at peptide position 3, and crystal structure 6ULN
shows a salt bridge between that p3 Asp and Arg156 of the heavy chain. The
G12D substitution is what puts Asp at p3; the wild-type residue is Gly, which
has no side chain, so the contact is impossible by chemistry rather than by
prediction. That is the honest version of "the mutation is why this candidate
exists".
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import gemmi

# Charged-group atoms, so we measure the interaction rather than an arbitrary
# centre-of-mass distance.
SALT_BRIDGE_ATOMS = {
    "ASP": ("OD1", "OD2"),
    "GLU": ("OE1", "OE2"),
    "ARG": ("NH1", "NH2", "NE"),
    "LYS": ("NZ",),
    "HIS": ("ND1", "NE2"),
}

# A salt bridge is conventionally called at 4 A between charged-group heavy atoms.
SALT_BRIDGE_CUTOFF_A = 4.0


@dataclass
class ContactMeasurement:
    peptide_residue: str      # e.g. "ASP3"
    mhc_residue: str          # e.g. "ARG156"
    min_distance_a: float
    is_salt_bridge: bool
    possible: bool            # False when a residue simply has no such group
    note: str

    def as_dict(self) -> dict:
        return {
            "peptide_residue": self.peptide_residue,
            "mhc_residue": self.mhc_residue,
            "min_distance_a": (None if math.isnan(self.min_distance_a)
                               else round(self.min_distance_a, 2)),
            "is_salt_bridge": self.is_salt_bridge,
            "chemically_possible": self.possible,
            "note": self.note,
        }


def _load(path) -> gemmi.Structure:
    st = gemmi.read_structure(str(path))
    st.setup_entities()
    st.remove_ligands_and_waters()
    st.remove_hydrogens()
    return st


def _chain(st: gemmi.Structure, cid: str) -> gemmi.Chain:
    for ch in st[0]:
        if ch.name == cid:
            return ch
    raise KeyError(f"chain {cid!r} not found; have {[c.name for c in st[0]]}")


def _residue_at(chain: gemmi.Chain, seq_index: int) -> gemmi.Residue | None:
    """Positional lookup (1-based) along the chain, ignoring numbering gaps.

    Peptide positions are conventionally counted p1..p9 from the N-terminus,
    which is not necessarily the author numbering in a crystal structure.
    """
    residues = list(chain)
    if 1 <= seq_index <= len(residues):
        return residues[seq_index - 1]
    return None


def _residue_by_number(chain: gemmi.Chain, number: int) -> gemmi.Residue | None:
    for res in chain:
        if res.seqid.num == number:
            return res
    return None


def measure_salt_bridge(
    cif_path,
    peptide_position: int,
    mhc_residue_number: int,
    peptide_chain: str = "C",
    mhc_chain: str = "A",
) -> ContactMeasurement:
    """Distance between two named charged groups.

    `peptide_position` is 1-based along the peptide (p1..p9).
    `mhc_residue_number` is the author numbering in the heavy chain.
    """
    st = _load(cif_path)
    pep_res = _residue_at(_chain(st, peptide_chain), peptide_position)
    mhc_res = _residue_by_number(_chain(st, mhc_chain), mhc_residue_number)

    if pep_res is None or mhc_res is None:
        return ContactMeasurement(
            f"?{peptide_position}", f"?{mhc_residue_number}", float("nan"),
            False, False, "residue not present in structure")

    pep_label = f"{pep_res.name}{peptide_position}"
    mhc_label = f"{mhc_res.name}{mhc_residue_number}"

    pep_atoms = SALT_BRIDGE_ATOMS.get(pep_res.name)
    mhc_atoms = SALT_BRIDGE_ATOMS.get(mhc_res.name)
    if not pep_atoms or not mhc_atoms:
        missing = pep_res.name if not pep_atoms else mhc_res.name
        return ContactMeasurement(
            pep_label, mhc_label, float("nan"), False, False,
            f"{missing} has no charged side-chain group -- this contact is "
            f"chemically impossible, not merely unfavourable")

    best = float("inf")
    for pa in pep_atoms:
        a = pep_res.find_atom(pa, "*")
        if not a:
            continue
        for ma in mhc_atoms:
            b = mhc_res.find_atom(ma, "*")
            if b:
                best = min(best, a.pos.dist(b.pos))

    if math.isinf(best):
        return ContactMeasurement(pep_label, mhc_label, float("nan"), False, True,
                                  "charged-group atoms missing from the model")

    formed = best <= SALT_BRIDGE_CUTOFF_A
    return ContactMeasurement(
        pep_label, mhc_label, best, formed, True,
        (f"salt bridge formed ({best:.2f} A)" if formed
         else f"charged groups present but {best:.2f} A apart -- no salt bridge"))


def peptide_sequence(cif_path, peptide_chain: str = "C") -> str:
    st = _load(cif_path)
    return gemmi.one_letter_code(
        [r.name for r in _chain(st, peptide_chain)]).upper()
