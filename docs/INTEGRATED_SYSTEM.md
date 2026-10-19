# Milestone 5: one continuing 50-neuron controller

The priority changed after milestone 4: integrate a continuing adaptive circuit
before creating the Streamlit interface. This is that initial integrated core.
Earlier experiments remain available and keep their original protocols.

## Circuit

The profile contains exactly 50 computed LIF neurons and 690 directed connections.

| Cells | Count | Role |
| --- | ---: | --- |
| 0–4, 5–9 | 10 | Sensory groups for two cues |
| 10–19, 20–29 | 20 | Recurrently connected association populations |
| 30–34, 35–39 | 10 | Inhibitory feedback populations |
| 40–44, 45–49 | 10 | Two action populations |

Sensory groups project to their association population. Association cells have
local recurrent and weak cross-population connections, and drive inhibitory
feedback. They also project to both action populations. Action cells feed weak
signals back to association and inhibitory cells. All outgoing inhibitory-cell
weights are negative; excitatory-cell weights are positive.

Only the 200 association-to-action connections adapt. The other 490 are fixed.
These functional group names are engineering roles, not identified brain regions.
Every cell is simulated; activity measurements report actual firing, including
whether all 50 cells participated. Counting cells alone is not a validity metric.

The underlying LIF equations, exponential synaptic-current solution, units,
threshold approximation and delay conventions are documented in NETWORK_MODEL.md.
The new continuing engine reuses those integration coefficients. Tests compare
its calculations with the previous fixed engine and test chunk invariance.

## Continuing time and interaction

One experience takes 100 ms of simulation time:

1. 0–5 ms: a 0.8 nA current drives five sensory cells for the presented cue.
2. 5–25 ms: the circuit evolves with no further external current.
3. At 25 ms: read both action populations' mean calculated voltage.
4. 25–30 ms: current drives the already selected action population to execute it.
5. 30–35 ms: evolve, then receive the environment's scalar outcome.
6. Apply the reward-gated update and evolve for another 65 ms.

No neuron voltages, synaptic currents, refractory counters, delayed events or
pre/post traces are reset between experiences. Zero input during quiet periods
still permits ordinary leak, current decay and internal activity. Continuity does
not mean the network is forced to keep firing in the absence of input.

Action decoding is explicit. Let m0 and m1 be the action populations' mean
voltage above rest. With temperature T=0.7 mV and exploration epsilon=0.2:

    p(action 1) = epsilon/2 + (1-epsilon) * sigmoid((m1-m0)/T)

A saved random-generator state samples the action. The action-execution current
then follows that sampled choice; it is not an input specifying the correct action.
The circuit is an engineered neural controller, including a decoder and actuator
interface. Its action is influenced by real activity, with explicit exploration.

## Environment

Two cue values occur equally often within shuffled blocks of twenty experiences.
Initially the rewarded action equals the cue. After experience 100 in the default
run, both cue/action contingencies reverse. The controller receives only cue
currents before choosing, then reward 1 or 0 after executing its action.

The reward function is part of the environment and has no route into the action
decoder. A causality test uses identical sessions with different hidden reversal
times: they make identical choices at the first differing rule, then receive
opposite feedback and update differently. No desired-action teaching pulses are
provided in this task.

This is a two-choice online-conditioning experiment, not a rich virtual world.
It does not establish general intelligence, arbitrary concept learning or brain
fidelity. The circuitry and parameter choices are illustrative.

## Reward-gated eligibility rule

This is a separate, explicitly defined three-factor rule; it does not silently
reinterpret milestone 3's direct additive STDP as reinforcement learning.
For each eligible connection, maintain dimensionless pre/post traces x,y and
eligibility e. Between events:

    dx/dt = -x/20 ms
    dy/dt = -y/20 ms
    de/dt = -e/150 ms

At local presynaptic arrival: subtract 1.05*y from eligibility and increment x.
At a postsynaptic action-cell spike: add x to eligibility and increment y.
Simultaneous events use old traces before either increment, excluding new
zero-lag pairs. Each timestamp is processed once at the engine boundary.

At feedback, first decay the traces to the current absolute time, then:

    w <- clip(w + 0.015 nA * (reward - 0.5) * e, 0.002 nA, 0.06 nA)
    e <- 0

Eligibility is consumed once per outcome. Pre/post traces and neuronal states
remain intact. Repeated feedback at the same time tick is rejected. Reward 0.5
is neutral. The fixed 0.5 reference is not a learned value function, critic or
claim of an unbiased policy-gradient estimator. Weight bounds are numerical
constraints rather than a biological homeostatic mechanism.

This rule is inspired by the reward/eligibility family of models, but is not an
exact reproduction of the cited papers or a dopamine simulation. Its isolated
credit update, sign, decay, bounds and no-eligibility control are tested directly.

## Controls and measurement

The default evaluation uses seeds 7, 19 and 43, with 200 experiences for each of:

- Outcome feedback with learning enabled.
- The same profile and cue sequence with weight updates disabled.
- Learning with independent Bernoulli(0.5) feedback, unrelated to actual success.

Cue generation, topology initialization, policy exploration and uncorrelated
feedback use separate random streams. For a given seed, the cue stream and
initial network match across conditions. Choices can diverge as internal states
and weights diverge. Actual environment success is scored in every condition,
including the uncorrelated-feedback control. That control is not a permutation
matched to the observed reward counts; its definition is reported explicitly.

Reported windows are the first twenty experiences, the final twenty before
reversal, the first twenty afterward, and the final twenty of the session.
These are online success rates while learning/exploration continue, not held-out
supervised accuracies. Means and sample SD are across independent seeds. Three
seeds limit statistical inference; bands are not confidence intervals.

Architecture and parameters were checked with development seed 501 before the
fixed evaluation list. No per-seed tuning was performed on the reported runs.

## Checkpoint and resume contract

The neural kernel can checkpoint at arbitrary step boundaries. Its state includes:

- Absolute time tick, boundary-settled flag and previous endpoint spikes.
- All 50 voltages, synaptic currents, refractory counters and cumulative counts.
- All weights and pending delayed synaptic arrivals, including in-flight signals.
- Eligible connection indices, pre/post traces, eligibility and their timestamps.
- Last consumed feedback tick and the static model configuration.

The experiment session additionally preserves experience index, cue buffer,
environment configuration, history and all three live random-generator states.
Session-file checkpoints are made only between complete experiences. No partially
executed environment transaction is represented as complete.

Checkpoint files are JSON, capped at 10 MiB, with a SHA-256 integrity envelope.
Loading validates formats, dimensions, signs, weight bounds, pending events,
time/boundary consistency and the seeded circuit profile. No pickle is used.
Writes are buffered, atomic and verified. The checksum detects accidental
changes; it is not an authenticity signature from a trusted third party.

The default run saves a mid-session checkpoint at reversal and a final checkpoint.
It restores the midpoint and repeats the remainder, then compares complete final
state with uninterrupted execution. Tests separately restore in-flight events,
settled boundaries, consumed feedback and future RNG-dependent choices.

Exactness is checked in the same runtime. Cross-version or cross-platform bitwise
reproducibility is not guaranteed; use locally generated checkpoints with the
same software environment when testing exact continuation.

## Limits and files

The continuing kernel retains only current state unless recording is requested.
Each recording block is limited to 2,000,000 entries per array; pending arrivals
to 200,000; block spikes to 200,000; total time to 10,000,000 ticks. The shared
Network definition still caps generic networks at 200 neurons. This profile is
50 cells; support for 500–1,000 remains future profiling/engineering work.

The CLI accepts one to five seeds and 80–400 demo experiences in multiples of
twenty. Sessions can continue up to 1,000 experiences via resume. Time steps are
0.2 ms by default or 0.1 ms. Sparse sampled recording windows are stored with
their absolute times; gaps between them must not be interpolated as observed data.

## Primary references

- Florian (2007), Reinforcement learning through modulation of spike-timing-
  dependent synaptic plasticity: https://pubmed.ncbi.nlm.nih.gov/17444757/
- Izhikevich (2007), Solving the distal reward problem through linkage of STDP
  and dopamine signaling: https://pubmed.ncbi.nlm.nih.gov/17220510/
- Brian 2's related reference example (not run as a cross-simulator validation):
  https://brian2.readthedocs.io/en/stable/examples/frompapers.Izhikevich_2007.html
