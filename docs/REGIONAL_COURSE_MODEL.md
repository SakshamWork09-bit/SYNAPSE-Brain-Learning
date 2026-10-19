# Regional biology course and the 100-cell model

This document records the original 0.13.0 classification microscope. In 0.14.1,
Cerebellum and Motor cortex use a separate 100-cell movement controller in their
microscope toggle (see MOVEMENT_MICROSCOPE.md); other classification microscopes
retain the architecture below. Current primary activities are described in
EXPERIENTIAL_LEARNING.md. The curriculum table below is historical.

This document separates anatomy, biological explanation,
engineering mechanism, measured evidence and claims that remain untested.

## Ordered curriculum

| Section | Structure | Focused manipulation / observation |
| --- | --- | --- |
| 01 | Prefrontal cortex | Move readout later; inspect fading history |
| 02 | Occipital lobe | Encode pixels and vary input strength |
| 03 | Cerebellum | Change spacing with the same symbol order |
| 04 | Temporal lobe | Teach categories; query an edited drawing without its teacher |
| 05 | Parietal lobe | Change spatial evidence; distinguish missing input from selection |
| 06 | Hippocampus | Compare retained readout change with a disabled control; optional STDP microscope |
| 07 | Basal ganglia | Perturb inhibitory transmission; follow the signs in biological pathways |
| 08 | Motor cortex | Inspect a decoder response; optional embedded movement environment |
| 09 | Thalamus | Perturb selected relay links with unchanged source input |
| 10 | Amygdala | Contrast neutral class association with affective conditioning |
| 11 | Hypothalamus | Alter an explicit context input; identify missing physiological feedback |
| 12 | Brainstem | Combine all routes and distinguish state regulation from an artificial input |

Each page contains a source-backed explanation of location, cellular mechanisms,
connected systems, an embedded experiment, limits and a reflection. Cell
foundations provides membrane, synapse and plasticity experiments. This covers
major structures at an introductory-to-mechanistic level; it does not claim to
exhaust every nucleus, region, cell type or molecular pathway.

## Architecture and units

All 100 cells use the existing exact-subthreshold LIF engine: rest/reset −65 mV,
threshold −50 mV, membrane time constant 20 ms, resistance 100 MΩ, refractory
2 ms. Synaptic current decays with a 5 ms time constant. Step: 0.5 ms. Spike
threshold events are quantized to endpoints. Synapse weights are signed current
jumps in nA, not receptor conductances.

| Cell IDs | Role | Count |
| --- | --- | ---: |
| 0–17 | Nine pixel OFF/ON pairs | 18 |
| 18–20 | A/B/C symbol input | 3 |
| 21–68 | Sixteen delay taps per symbol | 48 |
| 69–80 | Input convergence with weak fixed recurrent links | 12 |
| 81–86 | Inhibitory output to convergence/context cells | 6 |
| 87–94 | Four passive voltage readouts per class | 8 |
| 95–98 | Explicit context input, weak fixed recurrence | 4 |
| 99 | Fixed readout cue | 1 |

The standard topology has **796 connections**: 664 physical readout links and
132 fixed encoder/context links. Eighty-three source features each connect to
four targets in each of two classes. Per-class copies share weights; there are
166 class-specific readout values, constrained by 83 independent signed differences.
Having eight readout cells does not introduce eight independent learned features.

A symbol reaches sixteen taps after delays 1, 6, …, 76 ms. Visual/symbol sources
also reach convergence cells after 2 ms. Convergence cells drive inhibitory cells
and weak neighboring feedback; inhibitory outputs have negative signs. This
extends the earlier 50-cell profile with more history taps, convergent pathways,
inhibition and context inputs. It is not merely a relabeling of a 50-cell payload.

**These groups are engineering roles, not anatomical brain regions.** Cells share
parameters; there are no Purkinje cells, striatal projection neurons, cortical
layers, hippocampal subfields, receptor kinetics, vascular responses or hormones.

## Inputs, query and causality

A pattern pulse activates exactly one of each OFF/ON pair. A sequence drives
three symbol channels in a specified order. Source pulses last 5 ms. Default
input is 0.8 nA; four context cells receive a 0.4 nA pulse at input onset; the
readout cue receives 0.8 nA ten milliseconds before decoding. Context below spike
threshold can change local voltage without transmitting spikes to the readout.

Pattern readout is 40 ms; sequence readout is 50 ms after its last symbol onset.
An optional extra delay adds 0–60 ms. The recording continues 20 ms after readout.
A query begins in a fresh dynamical state, with its captured learned weights.
It compares the mean passive A and B voltages above rest at the readout time.
A magnitude below 0.01 mV abstains. This threshold is an engineering decision.
No expected label, stored prototype or teacher is passed to `probe`.

Readout voltage is independently verified on every query as the sum of exact
exponential-current PSP kernels triggered by actual recorded source spikes:

`feature(age) = 100/3 × (exp(−age/20) − exp(−age/5))`, for age > 0 after the
1 ms readout-link delay. This identity applies because these readout cells remain
subthreshold and have no output feedback. A query is rejected if that passive
assumption fails. Activity and transmissions come from the existing engine;
no timestamps are fabricated by the animation.

Relay gain affects source-to-delay/convergence links. Gain zero removes those
links, while identical source drive, direct visual-to-readout links and the
readout-cue route remain. Symbol cells have no direct readout bypass. A blocked
sequence query can retain cue-driven output voltage without retaining evidence
about the sequence; surviving voltage alone does not establish information flow.
Inhibitory gain affects only the six inhibitory sources' outputs. Gain and input
controls are explicit interventions, not learned or measured biological states.

## Teaching and matched controls

Default classes: L/T drawings, or ABBA/BABA sequences with the same counts and
last two symbols. Sixteen training timing variants are each presented twice per
epoch. The fixed encoder's actual spike-derived features are calculated once
and reused; a normalized batch delta rule fits a target voltage difference of
+0.8 mV for class A and −0.8 mV for class B. It is supervised learning between
presentations, not local STDP, dopamine or an online biological training process.

Each of 83 beta parameters defines positive class strengths:
`w_A = 0.0065 + beta/2`, `w_B = 0.0065 − beta/2` nA. Strengths are bounded to
0.001–0.012 nA. Bounded normalized updates use actual features and supplied
teachers; no literal input→answer table is saved in inference. Controls use
identical starting weights, inputs and presentation counts, with updates disabled
or balanced conflicting labels. Cached encoder reuse is identical in each branch.

Evaluation uses sixteen reserved timing variants of the two familiar prototypes.
It is not a new-object or new-sequence-grammar benchmark. Custom queries permit
inspection without an expected answer or a promised classification. Changing task
teaching may interfere with prior associations in the shared model.

The new model has a 16,384-presentation limit. Validated JSON saves/restores seed,
beta, presentation count and history. It contains no executable object payload.
The UI commits a restored model only after complete validation. Dense recordings
keep their captured weights and are not silently recomputed by later teaching.

## Anatomical interpretation and playback

The distributed medical plates are Servier Medical Art under CC BY 4.0. The
complete public-domain neuron diagram is by LadyofHats. Exact source URLs,
licenses, changes and hashes are in `ui_assets/anatomy/SOURCES.json`. PNG originals
are unchanged; labels and halos are an HTML/SVG overlay. The cortical/sagittal
plates face right; the medial-temporal cutaway faces left. Coronal markers locate
an approximate basal-ganglia region without claiming nucleus segmentation.

One playback clock drives task stage, source signal, recorded spike/transmission
markers, voltage inspector and anatomical interpretation. The stage interpretation
is selected from sourced biology, not computed from simulated group activity.
It makes no claim about actual recruitment, intensity, hemispheric dominance or
real human timing. A single displayed hemisphere does not establish lateralization.
For neutral classification, amygdala/hypothalamic/brainstem connections are explicitly
abstract lesson connections, not evidence of emotion, homeostasis or arousal.

Gold/teal halos relate to the current explanation; purple indicates a manual
anatomical selection. Halos are approximate sites, not boundaries. The cell
inspector shows recorded state at or before its cursor, never a future sample.
A completed response is disclosed inside the playback only at readout. Replay
changes no circuit state and starts paused, including under reduced-motion
preferences. Sources are ordinary links with safe external-link attributes.

Earlier pattern, sequence, arena and choice/probe renderers have a smaller
synchronized anatomy panel using their own recording clocks. They retain their
50-cell profiles. Motor cortex embeds the earlier environment experiment;
Hippocampus embeds a separate two-cell pair-STDP mechanism. These counts and
rules are stated at the point of use instead of presenting incompatible profiles
as one anatomical brain.

## Notes, continuity and review

Notebook v1 still stores only self-marked explored IDs and plain text notes.
Its known IDs now include twelve regions plus the earlier six course chapters;
256 KiB and 10,000-character note limits are retained. Models have separate
validated checkpoints. Existing earlier workbench/checkpoint formats are unchanged.

Automated numerical and app checks establish programmed behavior, not biological
validity or educational benefit. A complete Windows browser review, expert
neuroscience review and learner evaluation remain outstanding. See the executed
validation report for what was actually checked.
