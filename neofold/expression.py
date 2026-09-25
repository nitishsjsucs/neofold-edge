"""Normal-tissue expression as an OFF-TUMOUR SAFETY flag.

THE OBVIOUS FILTER IS BACKWARDS, so we do not build it. A "require the gene
to be expressed" gate (say TPM >= 1 in GTEx) would delete NY-ESO-1, whose
median normal-tissue expression is about 0.065 TPM. Silence in normal tissue
is the defining property of a cancer-testis antigen, not a defect. Tumour
expression is what such a gate is really reaching for, and GTEx is a
NORMAL-TISSUE atlas -- it cannot supply it.

WHAT IT IS GOOD FOR is the other direction. If the gene a candidate comes
from is highly expressed in healthy tissue, then a T-cell raised against that
peptide has somewhere to do damage. This is not hypothetical: in the MAGE-A3
TCR trials, an engineered receptor cross-reacted with a peptide from titin,
which is abundantly expressed in cardiac muscle, and patients died of cardiac
toxicity.

SO: high normal expression is a WARNING, never a qualification, and low
normal expression is never a disqualification. The flag annotates; it does
not gate.

WHAT THIS CANNOT ESTABLISH. GTEx medians are a population average across
donors, not this patient. They are bulk tissue, so a gene expressed in a rare
cell type is diluted. And expression of the gene is not presentation of the
peptide.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

# Tissues where an off-target T-cell response is least survivable. The MAGE-A3
# fatalities were cardiac, which is why heart leads this list.
CRITICAL_TISSUES = [
    "Heart_Left_Ventricle", "Heart_Atrial_Appendage",
    "Brain_Cortex", "Brain_Cerebellum",
    "Lung", "Liver", "Kidney_Cortex", "Nerve_Tibial",
]

# TPM bands. These are reporting conventions, not decision rules: TESLA used
# >33 TPM for TUMOUR abundance, which is a different question entirely.
HIGH_TPM = 50.0
MODERATE_TPM = 10.0


@dataclass
class ExpressionFlag:
    gene: str
    found: bool
    max_tpm: float | None = None
    max_tissue: str | None = None
    critical_tpm: float | None = None
    critical_tissue: str | None = None

    @property
    def risk(self) -> str:
        if not self.found:
            return "unknown"
        if self.critical_tpm is not None and self.critical_tpm >= HIGH_TPM:
            return "elevated"
        if self.critical_tpm is not None and self.critical_tpm >= MODERATE_TPM:
            return "moderate"
        return "low"

    @property
    def note(self) -> str:
        if not self.found:
            return "gene not found in the GTEx atlas; no off-tumour assessment"
        if self.risk == "elevated":
            return (f"{self.gene} is highly expressed in normal {self.critical_tissue} "
                    f"({self.critical_tpm:.0f} TPM). A T-cell response against this "
                    f"peptide would have healthy tissue to act on. This is the failure "
                    f"mode that caused cardiac deaths in the MAGE-A3 TCR trials.")
        if self.risk == "moderate":
            return (f"{self.gene} shows moderate expression in normal "
                    f"{self.critical_tissue} ({self.critical_tpm:.0f} TPM); worth a look "
                    f"before committing laboratory time.")
        return (f"{self.gene} is not highly expressed in the critical normal tissues "
                f"checked (peak {self.max_tpm:.1f} TPM in {self.max_tissue}). "
                f"Low normal expression is NOT evidence the candidate is good — "
                f"it only removes one specific safety concern.")

    def as_dict(self) -> dict:
        return {"gene": self.gene, "found": self.found, "risk": self.risk,
                "max_tpm": self.max_tpm, "max_tissue": self.max_tissue,
                "critical_tpm": self.critical_tpm,
                "critical_tissue": self.critical_tissue, "note": self.note,
                "is_gate": False}


class NormalExpression:
    """GTEx median TPM by gene symbol, reduced to what the flag needs."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._table: dict[str, dict] | None = None

    def _load(self) -> dict[str, dict]:
        if self._table is not None:
            return self._table
        if self.path.suffix == ".json":
            self._table = json.loads(self.path.read_text())
            return self._table

        table: dict[str, dict] = {}
        with gzip.open(self.path, "rt") as fh:
            fh.readline()                      # "#1.2"
            fh.readline()                      # dimensions
            header = fh.readline().rstrip("\n").split("\t")
            tissues = header[2:]
            crit_idx = [(i, t) for i, t in enumerate(tissues) if t in CRITICAL_TISSUES]
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                symbol = parts[1]
                try:
                    vals = [float(v) for v in parts[2:]]
                except ValueError:
                    continue
                if not vals:
                    continue
                mx = max(range(len(vals)), key=lambda i: vals[i])
                crit = max(crit_idx, key=lambda p: vals[p[0]]) if crit_idx else None
                row = {"max_tpm": round(vals[mx], 2), "max_tissue": tissues[mx]}
                if crit:
                    row["critical_tpm"] = round(vals[crit[0]], 2)
                    row["critical_tissue"] = crit[1]
                # Keep the highest-expressing entry when a symbol repeats.
                prev = table.get(symbol)
                if prev is None or row["max_tpm"] > prev["max_tpm"]:
                    table[symbol] = row
        self._table = table
        return table

    def compact(self, genes: list[str]) -> dict[str, dict]:
        """A small vendorable subset, so the demo need not ship 8.8 MB."""
        t = self._load()
        return {g: t[g] for g in genes if g in t}

    def check(self, gene: str) -> ExpressionFlag:
        row = self._load().get(gene)
        if row is None:
            return ExpressionFlag(gene=gene, found=False)
        return ExpressionFlag(gene=gene, found=True, max_tpm=row["max_tpm"],
                              max_tissue=row["max_tissue"],
                              critical_tpm=row.get("critical_tpm"),
                              critical_tissue=row.get("critical_tissue"))
