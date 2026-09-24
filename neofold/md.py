"""Short molecular-dynamics stability check on a predicted peptide-MHC complex.

WHAT THIS CAN AND CANNOT SAY
----------------------------
This runs on the order of a nanosecond of implicit-solvent dynamics. Measured
peptide-MHC complex half-lives are in HOURS, so this samples roughly 10^-13 of
the relevant timescale. The largest published study on this question (2,883
HLA-A2 peptides, 200 ns each) improved discrimination only from AUC 0.80
(sequence alone) to 0.81 -- and discarded its first 30 ns as equilibration,
which is far longer than anything we run here.

So the only defensible reading is as a NEGATIVE FILTER:

    defensible: "the physics immediately rejects this pose"
    NOT defensible: any claim about stability, affinity, or immunogenicity

A peptide that stays put has not been shown to bind. A peptide that flies out
of the groove in a few hundred picoseconds is worth a second look at the pose.

The run is TIME-budgeted rather than nanosecond-budgeted: it measures its own
throughput first, then picks a step count that fits the budget. That way it
cannot overrun a live demo on slower hardware.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

# Physical settings. Implicit solvent is the only option that fits the budget:
# explicit TIP3P would need NPT density equilibration that alone exceeds it.
TEMPERATURE_K = 310          # body temperature
FRICTION_PER_PS = 2.0
TIMESTEP_FS = 4.0            # safe with hydrogen mass repartitioning + constrained H bonds
HYDROGEN_MASS_AMU = 4.0
# Implicit solvent in OpenMM supports only NoCutoff / CutoffNonPeriodic /
# CutoffPeriodic. NoCutoff makes generalised Born O(N^2), which is what makes
# naive implicit-solvent runs so slow; a cutoff puts it on a neighbour list.
CUTOFF_NM = 1.8
RESTRAINT_KCAL = 5.0         # equilibration restraint on heavy atoms
EQUILIBRATION_PS = 10.0

CONTACT_CUTOFF_NM = 0.45     # heavy-atom contact definition


@dataclass
class MDResult:
    name: str
    atoms: int
    ns_per_day: float
    production_ns: float
    wall_s: float
    peptide_rmsd_a: list[float] = field(default_factory=list)
    contact_fraction: list[float] = field(default_factory=list)
    frame_times_ps: list[float] = field(default_factory=list)
    final_rmsd_a: float = 0.0
    contact_persistence: float = 0.0
    verdict: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "atoms": self.atoms,
            "ns_per_day": round(self.ns_per_day, 1),
            "production_ns": round(self.production_ns, 4),
            "wall_s": round(self.wall_s, 1),
            "final_peptide_rmsd_a": round(self.final_rmsd_a, 2),
            "max_peptide_rmsd_a": round(max(self.peptide_rmsd_a or [0]), 2),
            "contact_persistence": round(self.contact_persistence, 3),
            "frame_times_ps": [round(t, 1) for t in self.frame_times_ps],
            "peptide_rmsd_a": [round(v, 2) for v in self.peptide_rmsd_a],
            "contact_fraction": [round(v, 3) for v in self.contact_fraction],
            "verdict": self.verdict,
            "interpretation": (
                "A short implicit-solvent run can only reject an implausible pose. "
                "Retained contacts are NOT evidence of binding, stability or "
                "immunogenicity -- this samples ~10^-13 of the measured complex "
                "lifetime."
            ),
        }


def _verdict(final_rmsd: float, persistence: float) -> str:
    """Deliberately conservative wording: the pass case claims nothing."""
    if final_rmsd > 5.0 or persistence < 0.3:
        return ("REJECTED by dynamics: the peptide left its predicted pose within "
                "the simulated window")
    if final_rmsd > 3.0 or persistence < 0.6:
        return ("UNSTABLE in this short run: the pose drifted materially; worth "
                "re-examining before spending more compute")
    return ("not rejected: the pose held over the simulated window. This is the "
            "absence of a red flag, not evidence of binding")


def run_md(
    cif_path: str | Path,
    out_dir: str | Path,
    peptide_chain: str = "C",
    budget_s: float = 120.0,
    frames: int = 60,
    platform_name: str = "CUDA",
) -> MDResult:
    """Minimise, briefly equilibrate, then run production within `budget_s`."""
    import numpy as np
    from openmm import (CustomExternalForce, LangevinMiddleIntegrator, Platform,
                        unit)
    from openmm.app import (CutoffNonPeriodic, ForceField, HBonds, PDBFile,
                            Simulation)
    from pdbfixer import PDBFixer

    cif_path, out_dir = Path(cif_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    # Boltz writes no hydrogens and no terminal caps; PDBFixer adds them.
    fixer = PDBFixer(filename=str(cif_path))
    fixer.findMissingResidues()
    fixer.missingResidues = {}          # don't model unresolved loops
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(7.4)
    prepared = out_dir / "prepared.pdb"
    with open(prepared, "w") as fh:
        PDBFile.writeFile(fixer.topology, fixer.positions, fh)

    forcefield = ForceField("amber14-all.xml", "implicit/obc2.xml")
    system = forcefield.createSystem(
        fixer.topology,
        nonbondedMethod=CutoffNonPeriodic,
        nonbondedCutoff=CUTOFF_NM * unit.nanometer,
        constraints=HBonds,
        hydrogenMass=HYDROGEN_MASS_AMU * unit.amu,
    )

    topology = fixer.topology
    atoms = list(topology.atoms())
    peptide_idx = [a.index for a in atoms if a.residue.chain.id == peptide_chain]
    mhc_idx = [a.index for a in atoms if a.residue.chain.id != peptide_chain]
    peptide_heavy = [i for i in peptide_idx if atoms[i].element.symbol != "H"]
    mhc_heavy = [i for i in mhc_idx if atoms[i].element.symbol != "H"]
    if not peptide_heavy:
        raise ValueError(f"no atoms found for peptide chain {peptide_chain!r}")

    integrator = LangevinMiddleIntegrator(
        TEMPERATURE_K * unit.kelvin,
        FRICTION_PER_PS / unit.picosecond,
        TIMESTEP_FS * unit.femtoseconds,
    )
    try:
        platform = Platform.getPlatformByName(platform_name)
    except Exception:
        platform = Platform.getPlatformByName("CPU")
    sim = Simulation(topology, system, integrator, platform)
    sim.context.setPositions(fixer.positions)

    sim.minimizeEnergy(maxIterations=500)

    # Restrained equilibration: let solvent-free side chains relax without
    # letting the whole complex drift before we start measuring.
    restraint = CustomExternalForce("k*periodicdistance(x,y,z,x0,y0,z0)^2")
    restraint.addGlobalParameter(
        "k", RESTRAINT_KCAL * unit.kilocalories_per_mole / unit.angstrom**2)
    for p in ("x0", "y0", "z0"):
        restraint.addPerParticleParameter(p)
    start_pos = sim.context.getState(getPositions=True).getPositions()
    for i in peptide_heavy + mhc_heavy:
        restraint.addParticle(i, start_pos[i].value_in_unit(unit.nanometers))
    restraint_force = system.addForce(restraint)
    sim.context.reinitialize(preserveState=True)
    sim.context.setVelocitiesToTemperature(TEMPERATURE_K * unit.kelvin)
    sim.step(int(EQUILIBRATION_PS * 1000 / TIMESTEP_FS))
    system.removeForce(restraint_force)
    sim.context.reinitialize(preserveState=True)

    # Throughput probe, so the production length fits the time budget.
    probe_steps = 2000
    t0 = time.perf_counter()
    sim.step(probe_steps)
    probe_s = time.perf_counter() - t0
    steps_per_s = probe_steps / max(probe_s, 1e-6)
    ns_per_day = steps_per_s * TIMESTEP_FS * 1e-6 * 86400

    remaining = max(budget_s - (time.perf_counter() - t_start), 10.0)
    total_steps = max(frames * 50, int(steps_per_s * remaining))
    steps_per_frame = max(1, total_steps // frames)

    ref = sim.context.getState(getPositions=True).getPositions(asNumpy=True)
    ref_ang = ref.value_in_unit(unit.angstrom)
    ref_pep = ref_ang[peptide_heavy]
    # Subsample the MHC for the alignment: 5k+ atoms per frame is needless work
    # and the fit is already over-determined.
    align_idx = mhc_heavy[::4]
    ref_mhc_pts = ref_ang[align_idx]
    ref_contacts = _contacts(ref.value_in_unit(unit.nanometer),
                             peptide_heavy, mhc_heavy)

    rmsds, fractions, times = [], [], []
    for f in range(frames):
        sim.step(steps_per_frame)
        state = sim.context.getState(getPositions=True)
        pos = state.getPositions(asNumpy=True)
        pos_ang = pos.value_in_unit(unit.angstrom)
        rmsds.append(_kabsch_rmsd(ref_mhc_pts, pos_ang[align_idx],
                                  ref_pep, pos_ang[peptide_heavy]))
        cur = _contacts(pos.value_in_unit(unit.nanometer), peptide_heavy, mhc_heavy)
        fractions.append(len(cur & ref_contacts) / max(len(ref_contacts), 1))
        times.append((f + 1) * steps_per_frame * TIMESTEP_FS / 1000.0)

    wall = time.perf_counter() - t_start
    result = MDResult(
        name=cif_path.stem,
        atoms=system.getNumParticles(),
        ns_per_day=ns_per_day,
        production_ns=times[-1] / 1000.0 if times else 0.0,
        wall_s=wall,
        peptide_rmsd_a=rmsds,
        contact_fraction=fractions,
        frame_times_ps=times,
        final_rmsd_a=rmsds[-1] if rmsds else 0.0,
        contact_persistence=sum(fractions) / len(fractions) if fractions else 0.0,
    )
    result.verdict = _verdict(result.final_rmsd_a, result.contact_persistence)
    (out_dir / "md_result.json").write_text(json.dumps(result.as_dict(), indent=2))
    return result


def _kabsch_rmsd(ref_mhc, cur_mhc, ref_pep, cur_pep) -> float:
    """Peptide RMSD after superposing the frame's MHC onto the reference MHC.

    Without this the number is dominated by the whole complex tumbling in
    solvent: a perfectly bound peptide drifts to ~7 A of apparent RMSD purely
    from rigid-body rotation. We only care whether the peptide moved RELATIVE
    to the groove, which is the same convention used for the crystal-structure
    comparison in validate.py.
    """
    import numpy as np
    ref_c, cur_c = ref_mhc.mean(axis=0), cur_mhc.mean(axis=0)
    P, Q = cur_mhc - cur_c, ref_mhc - ref_c
    V, _, Wt = np.linalg.svd(P.T @ Q)
    d = np.sign(np.linalg.det(V @ Wt))
    D = np.diag([1.0, 1.0, d])
    R = V @ D @ Wt
    aligned = (cur_pep - cur_c) @ R + ref_c
    return float(np.sqrt(((aligned - ref_pep) ** 2).sum(axis=1).mean()))


def _contacts(pos_nm, peptide_idx, mhc_idx) -> set[tuple[int, int]]:
    """Heavy-atom peptide-MHC contact pairs within the cutoff."""
    import numpy as np
    p = np.asarray(pos_nm)[peptide_idx]
    m = np.asarray(pos_nm)[mhc_idx]
    out = set()
    # Chunked to keep peak memory sane on a 6k-atom system.
    for start in range(0, len(m), 4000):
        block = m[start:start + 4000]
        d = np.linalg.norm(p[:, None, :] - block[None, :, :], axis=-1)
        pi, mi = np.where(d < CONTACT_CUTOFF_NM)
        out.update((int(peptide_idx[a]), int(mhc_idx[start + b]))
                   for a, b in zip(pi, mi))
    return out
