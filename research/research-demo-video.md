# What actually makes a 2-minute technical demo video work

**Research date:** 2026-09-25 · **Audience:** whoever is cutting `video/narration.txt` and
`scripts/video_scenes.py` this week, for a hackathon submission.

Every claim below carries a URL. Each is tagged so you know how much weight it bears:

- **[MEASURED]** — an experiment, a controlled study, or aggregate telemetry. N and method stated.
- **[OFFICIAL]** — a platform or organiser rule. Not evidence about what works; a constraint you must meet.
- **[OPINION]** — an expert's prescription. Often good, but it is one person's taste, not a finding.
- **[SESSION]** — measured in this repo during this research, by script. Reproducible; see the snippet.

Where a widely-repeated number turned out to be untraceable or wrong, it is marked
**[UNRELIABLE]** and you should not put it in a slide.

---

<!-- SLOT:TLDR -->

---

## 0. The measured baseline: what this repo's video currently does

Before any advice, here is the current film measured by script, so later sections have something
concrete to argue with. Source: `video/narration.txt` and `scripts/video_scenes.py` as of
2026-09-25.

| Scene | Spoken words | Est. duration @150 wpm | Visual state changes | Sec per visual change |
|---|---|---|---|---|
| `meta` | 32 | 12.8 s | 7 | 1.83 s |
| `hook` | 47 | 18.8 s | 7 | 2.69 s |
| `question` | 44 | 17.6 s | 10 | 1.76 s |
| `problem` | 44 | 17.6 s | 6 | 2.93 s |
| `build` | 36 | 14.4 s | 5 | 2.88 s |
| `wow` | 39 | 15.6 s | 9 | 1.73 s |
| `nano` | 31 | 12.4 s | 9 | 1.38 s |
| `proof` | 28 | 11.2 s | 5 | 2.24 s |
| `close` | 13 | 5.2 s | 5 | 1.04 s |
| **Total** | **314** | **125.6 s** | **63** | **1.99 s** |

**[SESSION]** Three things fall out of this table, and they set the agenda for the rest of the
document:

1. **The visual changes every 2.0 seconds on average.** That is a good number — §3 shows it lands
   inside the range the pacing evidence supports. Pacing is not this video's problem.
2. **The first 12.8 seconds — 10% of the film — are about the tooling, not the product.** The
   `meta` scene runs before the hook. §2 is about why this is the single largest risk in the cut.
3. **There are only 9 scenes in 126 seconds, i.e. ~14 s per scene.** That is fine, because the
   *state* inside each scene changes every ~2 s. The distinction matters: for an explainer, the
   number to manage is the rate of visual change, not the rate of cuts (§3).

Reproduce the table with:

```bash
python3 - <<'PY'
import re, pathlib
narr = pathlib.Path("video/narration.txt").read_text()
src  = pathlib.Path("scripts/video_scenes.py").read_text()
parts = re.split(r'^def (\w+)\(t, dur\):', src, flags=re.M)
fns = {parts[i]: parts[i+1] for i in range(1, len(parts)-1, 2)}
for sid, _, body in re.findall(r'^@ (\S+) \| (.*?)$\n(.*?)(?=^@ |\Z)', narr, re.S|re.M):
    text = " ".join(l.strip() for l in body.strip().split("\n")
                    if l.strip() and not l.strip().startswith('#'))
    w = len(text.split()); b = fns.get(sid, "")
    beats = len(re.findall(r'window\(t,', b)) + 3*len(re.findall(r'stagger\(', b))
    print(f"{sid:10} {w:4} words  {w/150*60:5.1f}s  {beats:3} beats  {w/150*60/max(beats,1):.2f}s/beat")
PY
```

### 0.1 The one measurement that should change the cut

**[SESSION]** Counting every string literal of 6+ characters containing a space in each scene
renderer, and comparing it against how much text a viewer can actually read in that scene's
duration at Netflix's official 20 characters-per-second ceiling for English adult content (§5.4):

| Scene | Duration | Readable chars @20 CPS | Chars present in source | Over budget |
|---|---|---|---|---|
| `meta` | 12.8 s | 256 | 945 | **3.7×** |
| `hook` | 18.8 s | 376 | 818 | **2.2×** |
| `question` | 17.6 s | 352 | 1579 | **4.5×** |
| `problem` | 17.6 s | 352 | 1208 | **3.4×** |
| `build` | 14.4 s | 288 | 875 | **3.0×** |
| `wow` | 15.6 s | 312 | 1874 | **6.0×** |
| `nano` | 12.4 s | 248 | 797 | **3.2×** |
| `proof` | 11.2 s | 224 | 603 | **2.7×** |
| `close` | 5.2 s | 104 | 846 | **8.1×** |

**Read this honestly — it is an upper bound, not a verdict.** The count does not model
simultaneity (staggered arrivals mean not all of it is on screen at once), and some of it is
deliberately unreadable texture — the candidate table in `wow` is *meant* to read as "a lot of
rows", not as words. A dashboard's rows are scenery, and scenery does not need a reading budget.

But the direction is not in doubt, and two scenes cannot be explained away by texture:

- **`close` at 8.1×** is a tagline card. There is no table to blame. 846 characters of type in
  5.2 seconds is the last thing a judge sees, and they will read approximately one eighth of it.
- **`question` at 4.5×** is a governance diagram with eight labelled steps. Labels on a diagram
  *are* meant to be read.

This is the coherence principle (§5.1) with a median effect size of **d = 0.86** pointing at it.
Cutting type is the cheapest edit in this document and the one with the best evidence behind it.

---

## 1. Structure: the beat layout, with second counts

### 1.1 Set expectations first: almost none of this is measured

The accelerator literature on pitch structure is **entirely prescriptive**. There is no A/B test
anywhere in it. What it does have is authority — these are the people who watch hundreds of these
per year — and striking convergence on a small number of beats. Treat it as informed taste that
happens to agree with itself.

One recurring "measured" source, DocSend's pitch-deck telemetry (VCs average 3 min 44 s per seed
deck; ~15 s per page; ~58% of decks viewed to completion), **could not be verified** — both
<https://www.docsend.com/pitch-deck-metrics/> and their blog returned 403. It also measures reading
a deck asynchronously, not watching a video. **[UNRELIABLE]** Do not cite it.

### 1.2 The only first-party source with real second counts

**[OPINION]** Nicole Glaros, then Chief Investment Officer at Techstars, "Master Your Pitch" —
<https://toolkit.techstars.com/master-your-pitch> and
<https://toolkit.techstars.com/master-your-pitch-worksheet>.

This is the single most applicable source in the whole corpus, for two reasons: it gives per-section
time budgets, and it is the only one that makes **the demo the largest block** rather than something
to be avoided. For an average 5-minute pitch:

| Section | Allocation | Share | Contains |
|---|---|---|---|
| The Intro | ~1 min | ~20% | Who you are, credibility, the problem, why they should care |
| **The Demo** | **2–3 min** | **~40–60%** | How the problem goes away; the top **two or three** features |
| The Biz Stuff | 1–1.5 min | ~20–30% | Market, model, differentiation, team, traction — "the risk section" |
| The Landing | ~30 s | ~10% | Restate the top benefits, call to action, ask |

Two further numbers from Glaros: spend **75% of your preparation time on the intro**, and the
worksheet's timeline marks a **15-second intro hook** and a **sub-15-second close**. Note an
internal inconsistency in the Techstars material — the intro is variously 15 s, "under 30 s", and
1 minute. Flagged, not reconciled.

### 1.3 YC's beat order, and the per-beat cadence that falls out of it

**[OPINION]** Geoff Ralston, "A Guide to Demo Day Presentations", YC blog, 25 July 2016 —
<https://www.ycombinator.com/blog/guide-to-demo-day-pitches/>. The only YC document giving an
explicit beat order. No second counts.

1. **Introduction** — plainly what you do and why
2. **Problem** — include it, but *don't dwell*
3. **Product and customer**
4. **Opportunity** — bottom-up sizing (price × customers), never top-down
5. **Traction** — growth; pre-launch companies substitute story, credentials, vision
6. **Team** — only genuinely notable credentials
7. **Conclusion** — state your **3–4 key takeaways explicitly**; end with a bang

Ralston says the order is flexible, and notes YC sometimes advises putting impressive traction on
the **very first slide**.

**[OPINION]** Kevin Hale, "How to design a better pitch deck" —
<https://www.ycombinator.com/library/4T-how-to-design-a-better-pitch-deck>. Hale gives the
cadence numbers:

- **2 min 30 s** on stage (the constraint at the time he wrote it)
- **5–7 slides**, matching the 5–7 ideas YC partners identify with each company
- **One idea per slide.** A slide expressing two ideas is, by his etymology, *complex* — "plex"
  meaning fold or braid; simple means one fold.
- Three rules: **legible, simple, obvious.** Inverse failure modes: illegible, complicated, subtle.
- The obviousness test: show a frame to a stranger. If they do not immediately say your idea back
  to you, the frame has failed.

**The arithmetic that matters:** 5–7 beats in 150 s is **~21–30 s per beat**. Over 120 s it is
**~17–24 s per beat**. Both agree with each other and both agree with this repo's ~14 s scenes
(§0), which sit just inside the fast end.

### 1.4 YC's time limit is now 1 minute — and "YC says two minutes" is out of date

**[OFFICIAL]** The limit has been compressed repeatedly as batch sizes grew against a fixed-length
event. First-party statements:

| Era | Limit | Source |
|---|---|---|
| Hale's deck essay | 2 min 30 s | <https://www.ycombinator.com/library/4T-how-to-design-a-better-pitch-deck> |
| Hale's Startup School talk | 2 min (~200 companies, ~1,000 investors) | <https://www.ycombinator.com/library/6q-how-to-pitch-your-startup> |
| S20, Jul 2020 | **1 min** + one summary slide | <https://www.ycombinator.com/blog/yc-s20-virtual-demo-day/> |
| S21 / W22 / S22 | **1 min** | <https://www.ycombinator.com/blog/yc-s21-virtual-demo-day>, <https://www.ycombinator.com/blog/yc-w22-virtual-demo-day>, <https://www.ycombinator.com/blog/yc-s22-virtual-demo-day> |

So: **the current YC Demo Day format is one minute and one slide**, and has been since mid-2020.
The 2:30 and 2:00 figures are earlier eras of the same event, not competing advice. If you cite
this, say "YC's classic 2-minute structure", not "YC says two minutes".

Hale's stated rationale for brevity is worth keeping in mind because it generalises exactly to a
judging queue: investors are impatient and easily distracted; if they don't get the point
immediately they check email; nobody can concentrate across 100+ presentations *even as their job*.
Therefore every frame must be comprehensible at a glance, so it still lands when the viewer looks
up mid-distraction. And the goal is explicitly **not** to transmit the whole case — it is to earn
the follow-up.

### 1.5 The genuine conflict: open with *what you do*, or with the problem?

This is unresolved between high-trust sources, and you have to pick.

**YC says lead with what you do.** Paul Graham, "How to Apply Successfully" —
<https://www.ycombinator.com/howtoapply> — tells applicants to give it "in the first sentence, in
the simplest possible terms", and warns against dressing the idea up to sound more exciting.
Michael Seibel (<https://www.ycombinator.com/library/4b-how-to-pitch-your-company>) is blunter:
open with company name + what it does; there is **no need to set up the problem first**. Hale says
lead with **what**, not why or how, and that the opening must deliver three nouns: what you are
making, what the problem is, who the customer is.

**Everyone else leads with the problem.** Sequoia's "Writing a Business Plan"
(<https://sequoiacap.com/article/writing-a-business-plan>) goes purpose → problem → solution.
500 Global (<https://500.co/content/this-pitch-deck-will-rock-your-500-global-application>) puts
Problem at slide 2 of 10. Techstars folds "illuminate the problem" into the intro. Antler
(<https://www.antler.co/blog/pre-seed-pitch-deck>) leads with it outright, with the useful rule that
a problem must name **a person, a moment, and a cost**.

**My read for a hackathon demo video: take YC's ordering, but you have an unusual advantage.**
NeoFold Edge's problem *is* a story with a person, a moment and a cost — Rosie. The current script
already leads with it and it is the strongest 20 seconds in the film. The reconciliation is not to
choose: **say what the thing is in one sentence, then tell the Rosie story.** Right now the film
tells the story and never delivers the one-liner until `build` at ~1:00. A judge who stops at 45
seconds has watched a dog-cancer documentary and does not know what you built.

### 1.6 Hale is against screenshots, diagrams and screencasts — and this matters to you

**[OPINION]** From the same Hale essay, the don't list is aggressive and lands directly on choices
this repo has made: no animations, no transitions, **no diagrams** (he calls them mazes for ideas,
and invokes Hick's Law — each added element raises decision time logarithmically), **no
screenshots** (interface text is too small, interfaces do too many things, and they take longer
than a glance), and he says think twice about screencasts and video too. Ralston's don't list
independently includes "include videos", "use complex graphs" and "use cumulative graphs", and
caps slides at **~7 words**.

**Do not over-apply this.** Hale and Ralston are describing what to *embed in a live stage pitch to
distracted investors*, which is a different artifact from a standalone narrated demo film. Techstars,
talking about the demo itself, allocates it 40–60% of the runtime. The category difference is real.

But the **legibility** objection survives translation completely, and it is the same objection the
§0.1 measurement makes from a different direction: a frame that cannot be read at a glance is not
doing work. Hale's constructive version of the rule is the useful one:

- **Write the conclusion onto the chart as an explicit caption**, so the graph barely needs reading.
- **Replace raw UI with a short list of the steps it performs.**
- Large type, bold, high contrast, important text at the *top* of the frame.

### 1.7 YC separates "founders talking" from "the demo" — deliberately

**[OFFICIAL]** <https://www.ycombinator.com/video/>. YC's application video is **1 minute**,
nothing but founders talking, all founders present, and it is **explicitly not the place for a demo
or promotional video** — there is a separate application field for the product demo. They also say
don't recite a script; work from bullets, because they are assessing how founders communicate.

The structural lesson: YC's own product design says a founder-credibility artifact and a
product-demo artifact are different films with different jobs. If your two minutes is trying to be
both, that is a real tension, not a stylistic one. (Separately, YC advises including a demo *even if
unpolished* — <https://www.ycombinator.com/library/J8-yc-application-tips-include-a-demo> — because
the gap between nothing and something is large.)

### 1.8 A concrete 2-minute budget

Derived by weighting Techstars (the only source with second counts, and the only one that centres
the demo) against Hale's per-beat cadence and YC's opening-line rules. **This is a synthesis, not a
quotation from any single source.**

| Window | Length | Beat | Sourced constraint |
|---|---|---|---|
| **0:00–0:10** | 10 s | **One-liner.** What it is, who it's for, what problem. Hale's three nouns. No origin story, no tooling, no logo animation. | Graham, Seibel, Hale, Ralston |
| **0:10–0:30** | 20 s | **Problem made concrete** — a person, a moment, a cost. Don't dwell. | Antler; Ralston's "don't dwell" |
| **0:30–1:30** | 60 s | **The demo — half the runtime.** Two or three capabilities maximum. Every frame captioned with its own takeaway. | Techstars 40–60%; Glaros's top-2-or-3; Hale's legibility rules |
| **1:30–1:50** | 20 s | **Proof** — the one number or the unique insight. Bottom-up, no cumulative graphs. | Ralston, Seibel, First Round |
| **1:50–2:00** | 10 s | **Landing.** 3–4 takeaways restated, one explicit ask. End on a bang. | Ralston, Glaros |

**The hard budget nobody tells you about:** at a normal narration pace of 140–150 wpm, two minutes
is **280–300 words of script**. That is the real constraint, and it is brutally small. This repo's
script is **314 words** (§0) — already slightly over, before any of the additions below. Every new
sentence has to evict an old one.

Glaros's 75%-of-prep-on-the-intro rule means most of your remaining effort belongs in the first
10–15 seconds. Which brings us to the next section.



---

<!-- SLOT:FIRST10 -->

---

<!-- SLOT:PACING -->

---

<!-- SLOT:SOFTWARE -->

---

## 5. Numbers and data on screen

This is the best-evidenced section in the document, because information visualisation has run
actual controlled experiments on exactly this question. The headline is counter-intuitive and
worth stating up front:

> **Animation is measurably *better* than static for presentation, and measurably *worse* for
> analysis. A demo video is pure presentation. Animate — but animate one thing at a time.**

### 5.1 The five principles that govern text and graphics together

**[MEASURED]** Mayer & Fiorella, "Principles for Reducing Extraneous Processing in Multimedia
Learning", ch. 12 of *The Cambridge Handbook of Multimedia Learning* —
<https://doi.org/10.1017/CBO9781139547369.015> (accessible copy:
<https://edtechuvic.ca/wp-content/uploads/sites/11/2022/09/principles-for-reducing-extraneous-processing-in-multimedia-learning-coherence-signaling-redundancy-spatial-contiguity-and-temporal-contiguity-principles.pdf>).

These are meta-analytic medians over named experiments, tabulated in the chapter itself:

| Principle | What it says | Tests supporting | Median effect size |
|---|---|---|---|
| **Spatial contiguity** | Put words *near* the part of the graphic they describe | 22 of 22 | **d = 1.10** |
| **Temporal contiguity** | Narration and its animation play *simultaneously*, not in sequence | 9 of 9 | **d = 1.22** |
| **Coherence** | Exclude extraneous material | 23 of 23 | **d = 0.86** |
| **Redundancy** | Graphics + narration beats graphics + narration + on-screen text | 16 of 16 | **d = 0.86** |
| **Signaling** | Add cues that highlight the structure of the essential material | 24 of 28 | **d = 0.41** |

For calibration, the chapter follows Cohen (1988): d = 0.2 small, 0.5 medium, 0.8 large. Four of
these five are at or above "large". This is not a soft literature.

Four things follow directly, in descending order of evidential weight:

1. **Temporal contiguity (d = 1.22) is the strongest result here, and it is a scheduling rule.**
   The animation of a thing must run *while* the narration says it, not before and not after. This
   repo already gets this right by construction — `make_video.py` times each scene's visuals to
   the measured length of its narration clip — which is worth knowing you got for free.
2. **Spatial contiguity (d = 1.10) says stop using captions under diagrams.** A label belongs
   *on* the element. A legend off to the side, or a line of type beneath the figure, forces the
   viewer to visually span between the words and the thing, and that span is what costs them.
3. **Coherence (d = 0.86) is the argument for the §0.1 edit.** "Extraneous" includes material
   that is interesting, true, and yours. The chapter's own experiments strip out *seductive
   details* — engaging but inessential additions — and learning goes up.
4. **Redundancy (d = 0.86) has a boundary condition you should exploit, not fear.**

### 5.2 The redundancy nuance: keywords on the graphic are *good*

The naive reading of the redundancy principle — "never put text on screen" — is wrong, and the
chapter says so explicitly. The principle as measured concerns the specific case where "the
narration (the spoken words) and the on-screen text (the printed words) are identical". In all 16
such tests the non-redundant group won, median d = 0.86.

**[MEASURED]** But Mayer & Johnson (2008), reported in the same chapter, tested a narrated
presentation against the same presentation *plus a key word or phrase printed next to the
corresponding part of the graphic*. The redundant group **won** on retention — d = 0.47 (lightning)
and d = 0.70 (car brakes) — with no penalty on transfer (d = 0.04, d = 0.15). The chapter's
explanation is that a few words "may not be enough to distract the learner from the graphic and
may even signal where to look".

So the operative rule is a shape rule, not a quantity rule:

- **Verbatim sentences duplicating the voiceover: delete them.** d = 0.86 against.
- **Short keyword labels sitting on the element being discussed: keep them.** d = 0.47–0.70 for.

**[SESSION]** Checked against this repo by n-gram overlap between each scene's on-screen string
literals and its spoken line. The result is better than expected — the film is **already almost
clean**:

| Scene | Longest verbatim run shared with narration |
|---|---|
| `meta` | **6 words** — "we thought it'd be funny" |
| `close` | 4 words — "a cancer research lab" |
| all others | **none ≥ 4 words** |

Seven of nine scenes say something different in type than in voice. That is the harder discipline
and it is already done. `close` is a tagline card and falls squarely inside the Mayer & Johnson
exception — leave it. `meta` is discussed in §2.

### 5.3 Animate for presentation; never make the viewer compare moving things

**[MEASURED]** Robertson, Fernandez, Fisher, Lee & Stasko, "Effectiveness of Animation in Trend
Visualization", IEEE TVCG 2008 —
<https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tvcg2008-trendvis.pdf>.
Won the IEEE InfoVis 10-year Test of Time award in 2018. Three visualisations (animated bubble
chart à la Gapminder, static "traces" overlaid, static small multiples) × 2 dataset sizes × 2 uses
(Presentation vs Analysis), repeated measures, 36 participants.

Mean task completion times, reported in seconds in the paper:

| Context | Animation | Small multiples | Traces |
|---|---|---|---|
| **Presentation** | **15.80 s** (fastest) | 25.30 s | 27.80 s |
| **Analysis** | **83.10 s** (slowest) | 45.69 s | 55.01 s |

In Presentation, animation beat small multiples and traces at p < .001 each. In Analysis it lost to
both at p < .001. Accuracy ran the other way: a significant main effect of visualisation
(F₂,₆₈ = 4.18, p = .029) with small multiples significantly *more accurate*.

Subjective ratings (7-point, 0–6) tell you why animation is tempting and where it bites:

| Statement | Animation | Small multiples | Traces |
|---|---|---|---|
| "I enjoyed using this visualization" | **4.3** | 3.7 | 3.5 |
| "I found this visualization exciting" | **4.3** | 3.1 | 3.0 |
| "I lost track of some data points as they moved" | **4.8 overall** | — | — |
| "The animation went too fast for me" | 3.0 | — | — |
| "The animation went too slow for me" | 1.4 | — | — |

Read those last three together. Nobody thought it was too slow. Plenty lost track of what was
moving. Participants called it "fun", "exciting", one said "emotionally touching" — and also
complained the dots "flew everywhere".

The paper's own recommendation for presenters is the sentence to tape to your monitor:

> Presenters "should strongly consider ensuring that their data tells a clean story" — confounded
> by too many points, by points that reverse, or by points that do not move in synchrony.

And a hard ceiling worth knowing: **"All three techniques fail to scale beyond about 200 data
points."** If your animated view has more than ~200 moving marks, no amount of craft rescues it.

**Applied to a demo video.** A demo video is the Presentation condition, exactly. So: animate,
because it is faster and more engaging and that is measured. But the failure mode is *tracking* —
the viewer losing the one thing that mattered among the things that moved. Therefore animate one
subject per beat, keep its motion monotonic, and never require the viewer to compare two moving
things. If you need a comparison held in the eye, freeze it into small multiples or a static
side-by-side and let the voice do the pointing.

### 5.4 How long a number must stay on screen, and how fast a transition should run

Two independent sources give usable numbers.

**[OFFICIAL]** Netflix Timed Text Style Guide — the English guide
(<https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-Timed-Text-Style-Guide>)
and the Subtitle Timing Guidelines
(<https://partnerhelp.netflixstudios.com/hc/en-us/articles/360051554394-Timed-Text-Style-Guide-Subtitle-Timing-Guidelines>):

- Reading speed ceiling: **20 characters per second** for adult content, **17 CPS** for children's.
- **42 characters per line, maximum 2 lines** per subtitle event.
- Minimum duration: **20 frames (4/5 second)**. Nothing legible flashes shorter than this.
- Minimum gap between events: **2 frames**.
- On cuts: "Subtitles may cross shot changes when the dialogue they represent also crosses the
  shot change" — but they may not cross *scene* changes.

These are not findings about persuasion; they are the operational thresholds a professional
subtitling pipeline enforces so that ordinary viewers can keep up. Used as a budget for on-screen
type — as in §0.1 — they are the most defensible numbers in this document.

**[UNRELIABLE-ish]** The BBC Subtitle Guidelines' widely-quoted **160–180 words per minute** is
consistent across many secondary sources but I could not reach the primary document:
`bbc.co.uk` blocks this user agent and `bbc.github.io/subtitle-guidelines/` returned 404. Treat
160–180 wpm as a plausible convergent figure, not a verified citation, and prefer Netflix's CPS
number, which I read from the source.

**[MEASURED]** Heer & Robertson, "Animated Transitions in Statistical Data Graphics", IEEE
InfoVis 2007 — <https://idl.cs.washington.edu/files/2007-AnimatedTransitions-InfoVis.pdf>. Two
controlled experiments, 24 participants balanced across age, comparing static transitions,
direct animation, and *staged* animation.

Findings that convert directly into keyframes:

- **Animated transitions significantly beat static transitions** for both object tracking and
  change estimation; both animated conditions were preferred to static at **p < 0.001**.
- **Time each stage at about one second.** The paper's explicit revision after Experiment 2:
  participants "preferred slower animations", so the authors "recommend timing each stage around
  a full second, rather than around a half-second each". A general guideline of "transition times
  around 1 second" is given earlier, with the note that transitions with minimal movement can go
  faster.
- **Simple staging wins; complex staging backfires.** Splitting a transition into two clean stages
  (e.g. rescale the axis, *then* change the values) lowered error and was significantly preferred.
  Heavily staged animation, where nothing ever changes position and value at once, *increased*
  error. The paper explicitly discourages complex multi-stage animation.
- **Use slow-in slow-out.** Their "maximize predictability" principle: if the endpoint of a moving
  thing is guessable from the first fraction of its path, cognitive load drops and tracking
  improves. Acceleration curves buy you that.
- **More elements, more error.** "Increasing the number of elements noticeably increased error."
- Their design principles worth naming, all from §3.2 of the paper: *group similar transitions*
  (Gestalt common fate — things doing the same thing read as one thing), *minimize occlusion*,
  *use simple transitions* (translation and expand/contract are easier to read than rotation),
  and **"Make transitions as long as needed, but no longer."**

**[SESSION]** Checked against `scripts/video_scenes.py`: the `hook` counter already does most of
this right. `counter(75, p, comma=False)` runs over a 1.8 s window with an `out_back` ease and a
6% scale overshoot, and it lands *last* in the scene, after the setup text. One subject, one
monotonic motion, slow-out easing, ~1–2 s. That is the Heer & Robertson prescription almost to the
letter. The `problem` scene's "1,890 dots dimming to the fifty that matter" is also well-formed:
dimming is a *filter* transition, the surviving marks never move, and nothing has to be tracked.

Note one tension with the evidence, though: 1,890 dots is far past the ~200-mark ceiling Robertson
et al. found. That is fine here *because* the dots are not being tracked individually — the point
is the ratio, conveyed by an area of dimming. Keep it that way. The moment you ask the viewer to
follow a particular dot, the ceiling applies and you lose.

### 5.5 What aids comprehension vs what is decoration

Assembled from the three sources above.

**Earns its place:**

- **An animated counter on a single headline number**, ~1–2 s, easing out, landing on the beat the
  voice says it. Heer & Robertson: animation beats static for change estimation. Mayer:
  temporal contiguity, d = 1.22.
- **Progressive reveal / dimming to show a ratio** (1,890 → 50). This is filtering, the cheapest
  transition to read, and no tracking is demanded.
- **Keyword labels sitting on the element.** Mayer & Johnson, d = 0.47–0.70.
- **A static side-by-side when the viewer must actually compare two values** (e.g. predicted 2.5 Å
  vs measured 2.7 Å). Small multiples were the *more accurate* condition. Do not animate a
  comparison you want believed.
- **One highlight cue per beat.** Signaling, d = 0.41 — the weakest of the five, so do not
  over-invest, but it is positive.

**Decoration — costs attention, returns nothing:**

- **Two or more things moving at once.** "I lost track of some data points as they moved": 4.8/6,
  the highest-rated complaint in the study.
- **Rotation, and anything on a curved or unpredictable path.** Translation and expand/contract
  are measurably easier to parse.
- **Charts whose axes and values change in the same motion.** Stage them: axis first, then values.
- **More than ~200 moving marks**, if any individual mark matters.
- **Verbatim narration as on-screen type.** d = 0.86 against.
- **Type nobody can read in the time available.** See §0.1; budget at 20 CPS.

### 5.6 The voice and the music — relevant, because this film synthesises both

**[MEASURED]** Mayer's **voice principle** holds that people learn better from a human voice than
a machine voice, reported as supported in 3 of 3 experiments with a median **d = 0.78**
(<https://www.cambridge.org/core/books/abs/multimedia-learning/personalization-voice-and-image-principles/97F9B31362E6491806A4718FECCADE3D>).
On its face that is bad news for a Piper-narrated film.

**It does not apply to modern neural TTS, and this has been tested directly.** Dinçer (2022), "The
voice effect in multimedia instruction revisited: Does it still exist?", *Journal of Pedagogical
Research* 6(3) — <https://files.eric.ed.gov/fulltext/EJ1341358.pdf> (DOI 10.33902/JPR.202214591).
Pretest–posttest design, three groups (human voice / traditional machine voice / **modern** machine
voice), 50 participants, F(2,47):

| Comparison | Result |
|---|---|
| Human voice vs *traditional* machine voice | Human better, m = 60.56, **p = .00, d = 0.90** |
| Modern machine voice vs *traditional* machine voice | Modern better, m = 54.12, **p = .013, d = 0.75** |
| **Human vs modern machine voice** | **No significant difference, p = .200** |
| Human vs modern, self-reported mental effort | **No difference, p = .964** |

Mayer & DaPra (2012) independently found no significant difference between a recorded human voice
and a modern TTS voice, as cited in the same paper.

**The actionable reading:** the penalty is for *sounding robotic*, not for *being synthetic*. A
modern neural voice costs you nothing measurable in either learning outcome or cognitive load. So
the tooling joke in this film is not a sacrifice — Piper at `en_US-norman-medium` with
`LENGTH_SCALE = 1.10` is inside the "modern" category, and the slower read pushes further in the
right direction. Keep it. What would hurt is a voice with audible artefacts, wrong stress on
technical terms, or mangled numbers — which is exactly why `narration.txt` spelling numbers the way
they should be spoken ("two and a half angstroms") is load-bearing and not a stylistic quirk.

**[SECONDARY — unverified]** On background music: a 2023 systematic review and meta-analysis
(de la Mora Velasco, Chen, Hirumi & Bai, *Psychology of Music*,
<https://journals.sagepub.com/doi/abs/10.1177/03057356231153070>) is reported to pool 71 effect
sizes from 47 studies and find a **small positive** mean effect of background music, **d ≈ 0.314**,
with classical music faring better than other genres — a result the authors frame as inconsistent
with the cognitive-load prediction that music should hurt. **I could not read this paper:** SAGE
returned 403. The figures come from search summaries. Do not quote the number; the safe conclusion
is only that the evidence does not support *removing* a restrained score, and that music is not the
thing to spend your remaining hours on.

---

<!-- SLOT:FAILURE -->

---

<!-- SLOT:HACKATHON -->

---

<!-- SLOT:REWRITE -->

---

<!-- SLOT:SOURCES -->

---

<!-- SLOT:LIMITS -->
