# Local visual laboratory contract

Launch streamlit_app.py through Streamlit. It uses synapse/laboratory.py for
bounded operations, synapse/lab_charts.py for read-only Plotly figures, and the
existing simulation modules for all neural dynamics. requirements-ui.txt adds
Streamlit and Plotly; CLI-only requirements stay separate.

## Version 0.10: Patterns & sequences

Each browser session holds separate pattern and sequence workbenches. Applying
edited examples explicitly resets that workbench's weights. Other workspaces
retain their own models. Teaching uses 16 distinct signals, each repeated twice
per epoch; 32 default epochs mean 1,024 presentations, not 1,024 novel examples.
Fixed spiking features are cached during a teaching batch because the readout
has no feedback into the encoder. The batch delta rule is supervised, not STDP.

Run frozen query records independent cold-start probes with current and initial
weights. The display retains their own model snapshots/fingerprints when further
teaching occurs. Input edits apply on the query button, not on slider movement.
An invalid query leaves the previous recording available. Response cells remain
subthreshold; the decoder reads their mean voltages. A margin below 0.01 mV
abstains. This is an explicit engineering threshold, not calibrated confidence.

Replay reveals response/scores only at the recorded readout time. Spikes,
voltages and transmitted packets are actual engine data. Every recording takes
six display seconds at 1×; controls never teach or simulate. Reduced motion
disables autoplay. Replay HTML/JSON/NPZ exports retain one frozen query.

Noise tests use 16 balanced cases at held-out timings, with zero/one/two pixel
flips or symbol substitutions. Counts measure agreement with the originating
template label. Equal-distance corruptions are marked ambiguous. Some changed
signals can become closer to the other prototype; even an unambiguous nearest
prototype can then disagree with the origin. Full JSON retains these measurements.
The baseline stores prototypes explicitly; neural inference does not receive them.

Matched controls train fresh independent models rather than continuing the live
one. All receive the same physical signal presentations. Disabled learning keeps
initial weights; conflicting teachers assign both labels to every exact signal.
These conflicting labels are not independent random outcomes. Results retain
their own seed/task/epoch configuration and are not relabeled after teaching.

Interference compares new-only teaching and interleaved rehearsal from clones of
the same source, with equal presentation budgets. It leaves active weights alone
until Use new-only weights or Use rehearsal weights is pressed. Restore earlier
snapshot explicitly replaces weights/history with the source snapshot; it is not
biological repair. Original examples remain retention references after applying
a candidate. Reversing labels for identical signals creates incompatible demands.

Memory workbench JSON includes the applied examples, model and optional snapshot.
Frozen model JSON excludes prototypes and can be loaded through MemoryModel.from_bytes.
Both have SHA-256 integrity checks (not signatures), bounded JSON sizes and no
pickle/code loading. Workbench restoration validates profile agreement before
replacing state. Query/evaluation recordings and pending interference candidates
are not in workbench saves; download their separate exports. Browser refresh can
clear unsaved state. The arena and two-choice checkpoint formats stay separate.

## Version 0.9: Movement arena

The arena owns a separate ArenaSession, seeded profile and checkpoint format.
The sidebar Save or restore still applies to the two-choice controller. Arena
checkpoint controls are inside Movement arena. Interventions still apply to the
two-choice controller. No weights or histories are silently transferred between
these different profiles. Both have 50 cells, but their groups and wiring differ.

Map editing is a form. Apply map and reset arena creates a fresh controller;
invalid or disconnected safe-cell maps leave the old one intact. A custom first
start/goal must be distinct safe cells. Later episodes use seeded curriculum
pairs. Map presets fill the editor without applying it. Evaluate the edited map
instead freezes the existing weights and tests the edited world independently.

Step move calculates one complete 100 ms move. Start moving calculates an
initial move, then approximately one per seven-second fragment refresh. A
monotonic elapsed-time guard prevents extra moves from incidental early reruns.
Pause and workspace changes stop execution. Browser scheduling is not real-time.
Train 20 episodes calculates a batch; only the latest dense move is retained.
Frozen greedy play disables both learning and exploration for live moves and
disables the training button. Other learning conditions still use exploration
during training. A session has a 5,000-move budget.

The self-contained arena replay uses actual samples, spikes, processed arrivals
and before/after weights. Choice becomes visible at 20 ms; world movement,
feedback and weight changes at 35 ms. Before 35 ms the board shows the previous
position. It stops at 100 ms, six display seconds at 1×. Play, seek, speed and
neuron selection inspect a fixed recording; reduced-motion preferences disable
autoplay. No activity is invented for a restored session without dense traces.

Frozen evaluation pauses automatic moves and leaves neural state, world/RNG,
history and weights untouched. It starts fresh dynamics for every independent
journey and retains state between its moves. Results keep their own source seed,
weight hash, episode/move counts, map and evaluation seed when training continues.
All four controllers use identical cases. Neural evaluation is greedy with seeded
tie-breaking. The simple greedy baseline uses only permitted sensor directions
and unsafe indicators, with no route solver. Random movement samples all four
directions, so it can collide. Case counts can exceed unique reserved pairs on
small maps; each numeric result reports unique_pairs.

The path chart plots actual moves, walls, hazards and goal; collisions repeat
the same position. JSON retains every evaluated path/action, source weights and
measurements. Arena checkpoints use a SHA-256 integrity envelope and 10 MiB limit;
no pickle is loaded. Seeded circuit, engine state, transitions, sensor/readout
history, episode summaries, RNG and move boundaries are validated before restore.
Dense move replay is excluded; step once after restoring to record new activity.
Move history CSV, dense trace NPZ and standalone replay HTML are separate exports.

ARENA_MODEL.md defines sensors, learning, curriculum, resets and scientific limits.

## Version 0.8: Intervention lab

Changing workspaces pauses the continuing session. Run paired probe creates two
independent copies of its full neural state, including pending signals. It never
advances that session or consumes its environment/RNG history. Both branches use
the same initial state and frozen learned weights. There is no action decoder or
reward feedback during a probe. The original two-cue task is unchanged.

Connection controls give both branches the same current pulse. Only the
intervention copy scales selected transmissions and/or inhibitory transmissions.
Stimulus effect gives the intervention copy a pulse and the control no added
input, without connection controls. Existing endogenous activity may continue
in either branch. Current-state probes preserve that activity; Resting probes
start both copies with resting voltages, empty queues and cleared dynamic traces,
while retaining the source's learned weights and absolute clock.

Targets are a group or up to 20 custom neurons. Pulse amplitude ranges from
-1 to 1 nA; start and duration are explicit. Positive current depolarizes;
negative current hyperpolarizes. Probe windows are 100 or 200 ms. Gains from
0 to 2 select a pathway, one link or up to 50 custom links. Inhibitory gain also
ranges from 0 to 2. Overlapping gains multiply, up to an effective factor of 4.
Gain 0 blocks future arrivals, including pending arrivals when processed; it
does not erase previously delivered, decaying synaptic current. Learned weight
arrays are never edited. Gain 1 restores ordinary transmission on a new probe
from the same source, not biological recovery or within-probe relearning.

Settings apply only on Run paired probe. Results retain their own source hash,
clock, configuration and seed context. Importing a result reconstructs its
source and reruns the bounded experiment without replacing the live session.
The grouped display requires 50 cells. Only the latest paired result is held
in browser-session memory; download it before refreshing or restarting.

Choose control or intervention replay. Blocked links are dashed gray, manually
scaled links amber, and packets are actual processed transmissions. Manual
controls are labeled separately from learned changes. There are no action or
reward cards for these probes. The voltage overlay compares both branches on
one neuron's trace; per-cell counts and peaks show whole-window measurements.
Replay cards count events only up to the cursor. Numeric NPZ retains full
precision; displayed voltages are rounded as in normal playback.

Experiment JSON contains configuration, validated source snapshot, initial state,
source SHA-256 and measurements. Reproduction validates the source hash before
simulation. It is an integrity check, not a signature. It loads no executable
code or pickle, and the import limit is 10 MiB. This format is distinct from the
full continuing-session checkpoint. NPZ includes both branches' traces, external
currents, raw before/after learned weights and manual gains. Neuron CSV compares
counts/peaks; offline HTML exports the selected branch with effective transmission
strengths and frozen manual controls. The CLI can reproduce the experiment JSON.

## Version 0.7: Observe experience is the default

The automatic canvas view in synapse/replay.py and ui_assets replays one captured
experience. All 690 directed connections appear without selection. Optional
focus, keyboard left/right neuron selection and hover add detail. Faint arrows
show direction; packets use actual processed arrival events.

Cards reveal cue input, the chosen action at 25 ms, and actual reward/delivered
feedback at 35 ms. They read a completed recording and never execute the model.
The agent is still the two-cue/two-button controller; a movement arena is planned.

Start computes one experience per roughly 8-second refresh in Observe mode,
allowing the default six-second replay to finish. Charts and details keeps the
earlier 0.8-second interval. Browser scheduling is not a real-time guarantee.
Pause the session before inspecting a slower or older replay.

Replay's Play, Pause, Replay from start, speed and cursor controls run in the
browser and never advance the circuit. It stops at the end instead of looping.
Disable Follow newest recording while paused to choose among eight retained
experiences. Checkpoints do not contain these dense windows.

An observer context records (arrival time, edge index, transmitted weight) when
ContinuingNetwork.settle actually processes an arrival, including the feedback
boundary. Context entry/exit does not settle the engine. Carry-in signals are
included if their arrivals are processed in the window. Packet emission is
arrival minus the configured delay. Arrivals outside the captured window are
not shown as delivered events. Recording is capped at 200,000 events per context
and is absent from checkpoint state.

Each window retains its own initial/final 690 weights. This protocol updates
only at 35 ms, so playback switches exactly there. Arrivals on that boundary
use old weights, matching the engine. Historical playback never borrows later
weights. Voltages are rounded to four decimals for display; NPZ retains values.

Flashes last 1.5 simulation ms as display highlights after instantaneous spikes.
Strength changes receive a separate 12 ms highlight; this is not continuous
learning between outcomes. Positions represent engineered roles. Curve geometry
does not affect delays. No new connections are created.

Download this interactive replay exports complete HTML with inline CSS, JS and
data. It runs offline, without network requests or training. The app embeds its
own generated HTML with st.iframe and automatic content height. Uploaded HTML
is never embedded. The chart descriptions below apply to Charts and details.

## Continuing system

One Laboratory object belongs to one Streamlit browser session. It holds one
IntegratedSession and up to eight dense ActivityWindow records. There is no
shared global neural object or cache of mutable sessions. A browser refresh can
start a new session; persistence requires downloading a checkpoint.

- Step 1 and Advance 20 pause automatic execution and advance one or up to
  twenty complete 100 ms experiences. A final batch stops at the session budget.
- Start enables a Streamlit fragment with an approximately 0.8-second refresh
  interval. Each invocation advances one experience. Pause stops at a completed
  experience boundary. Browser scheduling and simulation time are distinct.
- Switching workspaces pauses execution and retains the active object.
- New-session settings are in a form. Only Create new session applies them.
  This explicitly replaces the current in-memory session; save first to keep it.
- The active seed, feedback condition, step and reversal are shown separately.
- There is no neuron-count control yet: the validated integrated profile is 50.

The environment displays its current cue/action rule to the human observer.
The neural controller receives only cue input and later scalar feedback. UI
rendering never sends the displayed correct action to the circuit.

## Views and time scopes

- Recent success averages actual rewards over the last min(20, completed)
  experiences. It is online success with exploration, not held-out accuracy.
- The four strength curves use actual mean adaptive weights after each outcome.
  The reversal marker lies between experiences R and R+1.
- A retained window includes all 50 voltages at 501 sample boundaries (default
  dt 0.2 ms), 500 synaptic-current interval samples, and all emitted spike events.
  Finer dt doubles the interval count. Adjacent block boundaries occur once.
- Follow latest experience updates the displayed trace as the session advances.
  Disable it to select one of the eight retained experiences. Older dense traces
  are evicted; aggregate experience history is not evicted.
- The playback cursor selects a recorded voltage sample. White graph overlays
  mark actual spikes within 0.5 ms of the cursor; they are display highlights.
  Neuron voltage is a LIF state with reset, not a biological spike waveform.
- Node sizes reflect whole-window spike counts, or cumulative counts when no
  window exists. Hover labels state that scope.
- The graph and weight matrix use CURRENT connections, even when inspecting an
  older voltage window. Historical mean strengths are in the learning curve.
- The network view shows incident edges of the selected neuron, rather than
  overlaying 690 edges. Positive edges are teal; inhibitory edges are orange.
  The connection table explicitly identifies source, target, strength, delay
  and whether that connection adapts. Positions indicate engineered groups,
  not anatomical brain locations.

## Comparisons and separate labs

The matched continuing comparison runs fresh sessions in three modes with the
same seed/configuration, initial wiring and cue stream. It does not reset,
advance, or train the active session. The default is 200 experiences per mode;
later reversal settings extend this to reversal+100 (up to 300 in the UI).
An imported checkpoint with a later reversal can require up to 500; the UI
caps the comparison at 400 experiences and retains at least 20 after reversal.
Imported reversals later than 380 disable this comparison with an explanation.
Comparison session budgets are 1,000, independent of a shorter imported budget.
All reported percentages are actual environment outcomes. Uncorrelated feedback
is independent Bernoulli(0.5), not shuffled actual reward counts. One seed does
not quantify between-seed uncertainty; run_integrated.py provides the earlier
three-seed comparison.

Structure lab runs the six existing 12-cell protocols from resting initial
states. Selecting a preset does not silently replace the last result: Run circuit
calculates it, and the displayed result is labeled with its own protocol name.
The connection table and input recipe make the manipulation explicit.

Learning lab calls PairSTDP for every displayed pair-window point. Its temporal
tab calls learning.run_seed with the established 32-example teaching and
24-example held-out protocol. All four neural conditions and the last-event
heuristic are shown. Custom A/B queries call neural_prediction with frozen
weights and no expected answer. Equal-time input groups are rejected clearly.
These labs use separate circuits and leave the continuing session unchanged.

## Exports and restoration

Prepare downloads pauses the circuit and creates immutable checkpoint/CSV
bytes labeled with completed experience count. Download clicks use Streamlit's
frontend-only download behavior and cannot advance the session. Downloads go
where the browser is configured to save files, not implicitly into outputs.

Checkpoint JSON uses the existing v1 envelope: a SHA-256 payload integrity check,
10 MiB limit, seeded-profile validation and complete engine/environment/RNG state.
It is not a security signature. No pickle or executable user code is loaded.
UI restoration validates the display history before replacing the active object.
Milestone 5 envelopes are supported. Dense trace windows are deliberately excluded.

Experience CSV records cue, action, actual reward, delivered feedback, decoder
scores/probabilities, four mean adaptive strengths and update norm. A per-window
NPZ contains sample times, all voltages/currents, events and neuron indices;
load it with np.load(..., allow_pickle=False). Comparison JSON contains the
independent sessions' full experience records. Temporal model JSON uses the
earlier frozen temporal-order model format.

The local launcher binds localhost. Hosting, authentication, multi-user deployment,
arbitrary code execution and custom network editing are outside this milestone.

Implementation references: Streamlit's official fragment start/stop tutorial,
st.download_button documentation and AppTest API:
https://docs.streamlit.io/develop/tutorials/execution-flow/start-and-stop-fragment-auto-reruns
https://docs.streamlit.io/develop/api-reference/widgets/st.download_button
https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest
