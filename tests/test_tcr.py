"""pMHC:TCR ternary complex -- the recognition step.

Contains a hard-won methodological lesson. PDB 6ULN's biological assembly
applies DIFFERENT symmetry operators to the pMHC chains (A,B,C) and the TCR
chains (D,E). Comparing against the raw asymmetric-unit coordinates makes a
good prediction look like a 72 A catastrophe. Always build the assembly.
"""
import json
from pathlib import Path

import gemmi
import pytest

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "results" / "tcr" / "kras_tcr_ternary_model_0.cif"
ASM = ROOT / "results" / "reference" / "6ULN_assembly.pdb"
RAW = ROOT / "results" / "reference" / "6ULN.cif"

pytestmark = pytest.mark.skipif(not (PRED.exists() and ASM.exists()),
                                reason="ternary structures not present")


def _load(p):
    st = gemmi.read_structure(str(p)); st.setup_entities()
    st.remove_ligands_and_waters(); st.remove_hydrogens()
    return st


def _atoms(ch, names=("CA",)):
    return [a.pos for r in ch for n in names
            for a in [r.find_atom(n, "*")] if a]


def _aligned():
    ref, pred = _load(ASM), _load(PRED)
    R = {c.name[0]: c for c in ref[0]}
    P = {c.name: c for c in pred[0]}
    sup = gemmi.calculate_superposition(R["A"].get_polymer(), P["A"].get_polymer(),
                                        gemmi.PolymerType.PeptideL, gemmi.SupSelect.CaP)
    pred[0].transform_pos_and_adp(sup.transform)
    return R, {c.name: c for c in pred[0]}


def _rmsd(a, b):
    import math
    n = min(len(a), len(b))
    return math.sqrt(sum(a[i].dist(b[i]) ** 2 for i in range(n)) / n)


def test_all_five_chains_predicted():
    st = _load(PRED)
    assert [(c.name, len(list(c))) for c in st[0]] == [
        ("A", 275), ("B", 99), ("C", 9), ("D", 189), ("E", 240)]


def test_tcr_docking_is_within_two_angstrom():
    """The headline: the whole 812-residue recognition complex, TCR included."""
    R, P = _aligned()
    for cid in ("D", "E"):
        assert _rmsd(_atoms(R[cid]), _atoms(P[cid])) < 2.0


def test_peptide_stays_accurate_in_the_larger_complex():
    """Adding 429 residues of TCR must not degrade the pMHC core."""
    R, P = _aligned()
    assert _rmsd(_atoms(R["C"]), _atoms(P["C"])) < 1.0


def test_raw_asymmetric_unit_would_give_a_false_failure():
    """Regression guard for the trap. Against RAW coordinates the TCR appears
    ~72 A misplaced; against the ASSEMBLY it is ~1.4 A. If this test ever stops
    holding, someone has changed how the reference is built."""
    raw, pred = _load(RAW), _load(PRED)
    Rr = {c.name: c for c in raw[0]}
    sup = gemmi.calculate_superposition(Rr["A"].get_polymer(),
                                        {c.name: c for c in pred[0]}["A"].get_polymer(),
                                        gemmi.PolymerType.PeptideL, gemmi.SupSelect.CaP)
    pred[0].transform_pos_and_adp(sup.transform)
    Pp = {c.name: c for c in pred[0]}
    assert _rmsd(_atoms(Rr["D"]), _atoms(Pp["D"])) > 20.0


def test_tcr_interfaces_are_less_confident_than_the_pmhc_core():
    """The model knows recognition is the harder problem, and says so."""
    conf = json.loads((PRED.parent / f"confidence_{PRED.stem}.json").read_text())
    pc = conf["pair_chains_iptm"]
    pmhc = pc["0"]["2"]        # HLA <-> peptide
    tcr = min(pc["3"]["2"], pc["4"]["2"])   # TCR chains <-> peptide
    assert tcr < pmhc
