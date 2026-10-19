# The 100-cell movement microscope

SYNAPSE 0.14.1 embeds the existing world-and-firing arena layout in both
Cerebellum and Motor cortex. A separate movement profile runs actual 100-cell
LIF simulation, rather than adding unused dots or relabelling the 50-cell view.

| Engineering group | Cells | Count | Input/output role |
| --- | --- | --- | --- |
| Eight sensor populations | N00–N47 | 48, six per population | Four goal-direction signs and four adjacent-danger flags |
| Four action populations | N48–N87 | 40, ten per action | Up, Right, Down and Left receiving responses |
| Inhibitory population | N88–N99 | 12 | Negative feedback onto action populations |

All 100 cells belong to a functional group and have connections. A particular
move need not make all cells spike. There are 1,920 adaptive sensor-to-action
links, 480 action-to-inhibitory links and 480 inhibitory-to-action links: 2,880
total. These groups are engineering roles, not anatomical brain subdivisions.

## Scaling the earlier circuit

Population sizes double from the earlier profile's 3 sensor, 5 action and
6 inhibitory cells to 6, 10 and 12. Synaptic strengths and adaptive weight bounds
are halved to account for doubled presynaptic population sizes. The feedback
learning rate per connection is also halved. Initial random sensor/action
strengths are sampled by the same seeded rule and then scaled.

This keeps population input sizes comparable without claiming identical
individual trajectories. The old 50-cell profile retains its original weights,
cell IDs, selected links, seeded behaviour and checkpoint format. Its dynamics
are checked by the existing regression suite.

## One move and its recording

1. At 0–5 ms, the eight declared binary observations drive their sensor cells.
2. At 20 ms, the four mean action-population voltages are read. Ordinary play
   samples a softmax policy mixed with 20% exploration. Frozen play selects a
   maximal neural score, using seeded tie breaking.
3. At 20–25 ms, the chosen action population receives execution current.
4. At 35 ms, the selected grid action changes the world and produces feedback.
   Only eligible sensor/action links may update, unless learning is disabled.
5. The engine continues to 100 ms. Playback reads that recorded voltage, spike,
   arrival, weight and world data. It cannot move or teach the live session.

The animation reveals choice at 20 ms and movement/feedback at 35 ms. A displayed
selected probability is a model policy probability, not confidence that a route
is correct. No route planner chooses neural actions. Sensors provide goal signs
and nearby danger; there is no learned vision, world map or general navigation.

## Regional interpretation

Motor cortex uses the arena to connect action-population activity with direction
and consequences. Cerebellum uses the same loop to inspect action and feedback,
with a lesson-specific explanation at the feedback stage. The primary reaching
activity above it remains the controlled adaptation/aftereffect experiment.

The arena updates from scalar environmental consequences. It does not calculate
cerebellar sensory prediction errors, climbing fibres, Purkinje/deep-nuclear
circuits, biological dopamine or muscles. Source links and approximate anatomical
halos explain relevant biological partners; they do not measure the learner's
brain activity or identify simulated cells with those regions.

## State and compatibility

The two lessons share one movement session under an independent namespace.
Their map edits, frozen evaluation, weights, histories and checkpoint controls
do not replace the earlier 50-cell arena, two-choice lab or classification model.
Navigation and closing the microscope pause live movement.

The 100-cell checkpoint declares its cell profile and preserves complete engine,
world and random-generator state. Restore reconstructs and checks the seeded
profile, selected synapses, parameter bounds, history and checksum. Dense replay
is excluded; the next recorded move repopulates playback. A 50-cell checkpoint
cannot replace a 100-cell lesson controller. The earlier sidebar accepts the
original 50-cell checkpoints as before.

## Sequence reporting in other microscopes

The classification engine remains a two-output readout. An arbitrary sequence
can produce a larger A voltage while differing from both reference examples.
The UI and replay therefore show **Literal input check** separately from
**Neural class preference**. Literal comparison is ordinary equality against the
captured pair, never an input to the neural decoder or a learned novelty detector.
The query itself receives no teacher, expected response or reference prototype.
