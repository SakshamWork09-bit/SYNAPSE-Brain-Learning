# Experiential lessons: what each activity actually does

SYNAPSE 0.14.0 opens each region with one clear idea and a choice to experiment.
The three steps are **Meet the idea → Try it → What happened?**. Controls belong
to that experiment. Numerical tables and the large spiking-circuit inspector are
available through the microscope rather than occupying the first screen.

## The twelve experiences

| Region | Experience | What you can change | What is calculated |
| --- | --- | --- | --- |
| Prefrontal cortex | Keep a rule through distraction | Colour/shape rule, delay, distractors | A human delayed-match task; correctness uses the original hidden rule |
| Occipital lobe | Find an edge | Nine pixels, contrast, fixed noise strength | Two hand-set Sobel filter magnitudes |
| Cerebellum | Compensate for a shifted reach | Shift, learning rate; remove shift | Retained compensation and endpoint error over reaches |
| Temporal lobe | Recognise a changed shape | Both teaching drawings and a separate query | Actual 100-cell spiking encoder and learned voltage readout |
| Parietal lobe | Move an attention spotlight | Location, gain, width | Gaussian-weighted evidence over an unchanged 4×4 sensory scene |
| Hippocampus | Associate a cue with its place | Both cues, Window/Door associations, query | Actual 100-cell readout trained with fixed physical output meanings |
| Basal ganglia | Learn which action pays | Separate outcomes for Actions 1/2, learning rate | Chosen-action value updates and optional exploratory choices |
| Motor cortex | Combine directional populations | Command direction, drive, suppressed population | Eight rectified cosine responses and their vector sum |
| Thalamus | Adjust transmission of two channels | Each input, each gain, inhibitory offset | Two independently gated relay outputs |
| Amygdala | Associate a cue with a neutral event | Each cue's event strength, learning rate | Cue-value updates; probes leave values fixed; unpaired presentations reduce expectation |
| Hypothalamus | Keep an internal variable near a target | Outside condition, target, feedback gain/on-off | A bounded proportional/integral controller under outside disturbance |
| Brainstem | Generate a recurring pulse | Drive, temporary brake strength, recovery | An adapting threshold unit, reset events and a retained pulse history |

Each activity isolates a computation associated with the lesson, not an
anatomically complete region. Only the two indicated primary activities use the
100-cell network. The others are transparent conceptual models or a human task.
The small medical diagram locates the lesson and pulses after interaction. It
does not display measured activation, BOLD signals or inferred human spikes.

## Calculations and controls

**Rule task.** A seeded generator chooses a target card and correct response
side. The displayed rule is captured at the start. The cue disappears for the
chosen delay before response cards become available. Distractors are irrelevant
moving shapes; their count is not used to predetermine correctness. Changing a
setting prepares the next trial. A correct answer says only that the displayed
task rule was followed, not which human neurons fired.

**Visual filters.** Binary pixels become contrast-scaled intensities about 0.5,
plus a fixed spatial noise pattern, clipped to [0,1]. Dot products with vertical
and horizontal Sobel kernels are divided by 4 and their absolute values shown.
Uniform brightness without noise gives zero edge response. Filters are hand-set;
these weights do not learn, and there is no simulated retina or V1 circuitry.

**Reaching.** With shift `s` and retained compensation `c`, endpoint error is
`e = s − c`. The update is `c ← c + learning_rate × e`. The endpoint shown is
the last recorded reach; changing a setting alone does not invent a new reach.
Removing the shift preserves compensation, producing an opposite-sign error on
the next reach. A zero learning rate preserves the original error.

**Spatial selection.** The sixteen raw input strengths are fixed, including a
brighter distractor and a dimmer target. Each location is multiplied by
`1 + gain × exp(−distance² / (2 × width²))`. The strongest weighted location wins.
At gain zero, moving attention cannot change that winner. No sensory input is
deleted; this activity does not simulate a clinical syndrome.

**Action learning.** The chosen action alone updates:
`Q[a] ← Q[a] + rate × (outcome[a] − Q[a])`. Manual choices let the learner compare
actions. Automatic turns use 20% seeded exploration and otherwise choose the
larger current value, with random tie breaking. Outcomes are editable strengths,
not probabilities or dopamine measurements. The displayed prediction error is
the scalar difference in this update.

**Directional populations.** For command angle `θ`, the relative activity of
population `i` is `drive × max(0, cos(θ − preferred_angle[i]))`. A selected
population can be reduced to zero. The vector sum is divided by 2. With zero
drive there is no vector direction. Each element represents an idealised
population, not one literal motor neuron; the model includes no muscles.

**Relays.** Each output is `max(0, input × gain − inhibitory_offset)`. All five
controls have separate state. This demonstrates selective transmission, not
thalamic membrane currents, tonic/burst firing or the full reticular circuit.

**Cue learning.** A presented cue updates `V ← V + rate × (event_strength − V)`.
Only that cue changes. Probe-only trials apply no outcome and no weight update.
Unpaired trials use an outcome of zero. Neutral confetti illustrates an event;
this is not a fear-conditioning procedure or emotion simulation. Reduced value
is a property of the scalar rule, not proof of erasing biological memory.

**Internal balance.** The model uses arbitrary units, not degrees Celsius.
Outside drift is `0.08 × (outside − internal)`. With feedback on, a bounded
integral accumulates `0.03 × error` within [−6,6], and corrective output is
`gain × error + integral`, bounded within [−8,8]. Feedback off produces no
corrective output. Internal state is bounded within [0,100]. These are teaching
parameters, not clinical thermoregulation or endocrine physiology.

**Rhythm.** Each integration step is 0.1 arbitrary time units. Brake decays as
`brake × exp(−recovery × 0.1)`. State accumulates
`0.1 × (drive − 0.1 × state − inhibition × brake)`, bounded below at zero.
At threshold 1, it resets to zero and brake increases by 1.2. The display retains
the latest 120 integration rows and pulse times. This adapting unit is not a
respiratory network model, and its pulses are not breaths per minute.

## The two neural activities

The spiking model is the existing 100-cell engine described in
REGIONAL_COURSE_MODEL.md. Actual source spikes drive synaptic currents and
passive readout voltages. Teaching adjusts a bounded supervised readout between
presentations. A test receives only query pixels and weights, with no teacher,
expected class or destination place. The two responses are voltages above rest,
not probabilities. A voltage difference below 0.01 mV produces abstention.

Temporal and hippocampal activities each keep their own RegionModel, preventing
cross-lesson teaching interference. Teaching uses 32 epochs, with 1,024 feature
presentations. Counts compare sixteen reserved timing variants of familiar
examples with a matched disabled-update branch. They do not establish recognition
of arbitrary objects. Learning also differs from biological STDP; that distinct
mechanism remains available in the two-cell timing workbench.

The hippocampal analogy uses exactly two places. Output 0 always means Window;
output 1 always means Door. Reversing cue/place assignments reverses the actual
teachers used for training. It does not merely rename an unchanged answer.
Both cues remain independently editable, with a separate query board.

Draft changes preserve the last response and its captured query. A notice marks
the response as belonging to the earlier test. Frozen probes do not alter
weights. Failed teaching preserves the previous weights and response. Duplicate
requests and messages from an older restore epoch cannot repeat teaching.

## Depth, state and earlier workbenches

The collapsed biology panel retains cellular mechanisms, regional interactions
and primary/textbook source links. The retained shared 100-cell microscope still
supports patterns, sequences, interventions, matched controls, branching signal
playback and cell-level inspection. Its newly independent prototype editors use
**Apply these two examples**; applying a pair does not silently reset weights.
Recordings retain the pair and weights captured when calculated.

From 0.14.1, Cerebellum and Motor cortex open a shared **100-cell movement arena**
in this microscope slot, replacing their classification/sequence workbench.
Their primary reach-adaptation and direction-population activities above it are
unchanged. See MOVEMENT_MICROSCOPE.md for the movement circuit and its own checkpoint.
The remaining classification microscopes report literal input equality separately
from the independently calculated A/B preference; an A preference does not certify
that a custom sequence equals Example 1.

The earlier 50-cell memory, choice and arena tools retain their own profiles,
learning rules and checkpoint formats. The hippocampal timing tool uses two
cells. Neither a cell count nor a passing test makes an integrated human brain.

Activity bundles contain the twelve activity states and the two activity-specific
neural models. They are capped at 2 MiB and validated before replacement, including
pixel types, control bounds, model identities and recorded response weights.
Notebook notes, shared microscope weights and earlier workbench checkpoints have
separate downloads. All state is local to the running application session.

## Research anchors

Sources are linked within each lesson, with species and experiment type labelled.
New anchors include Cavanaugh, Bair & Movshon (2002), macaque V1 receptive-field
recordings: https://pubmed.ncbi.nlm.nih.gov/12424292/ ; Tseng et al. (2007), human
reaching/adaptation: https://pubmed.ncbi.nlm.nih.gov/17507504/ ; Georgopoulos et al.
(1986), primate motor population coding: https://pubmed.ncbi.nlm.nih.gov/3749885/ ;
Schultz, Dayan & Montague (1997), prediction errors and reward:
https://pubmed.ncbi.nlm.nih.gov/9054347/ . These sources motivate the computations;
the app's numerical teaching parameters are not fitted to those studies.
