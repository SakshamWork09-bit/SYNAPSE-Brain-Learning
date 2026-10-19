"""Controlled circuit protocols; fixed input recipes, never fixed output traces."""

from dataclasses import dataclass
import numpy as np

from .lif import step_count
from .network import Network, Synapse
from .stimuli import pulse_current


@dataclass(frozen=True)
class CircuitExperiment:
    name: str
    title: str
    description: str
    network: Network
    input_nA: np.ndarray
    stimulus_recipe: tuple[dict, ...]
    duration_ms: float = 200.0
    inspect_neuron: int = 5


def circuit_experiments(dt_ms=0.1):
    duration, n = 200.0, 12
    steps = step_count(duration, dt_ms)
    source_recipe = {"neuron": 0, "baseline_nA": 0.0, "pulses": [(20.0, 25.0, 0.8)]}
    inhibitor_recipe = {"neuron": 10, "baseline_nA": 0.0, "pulses": [(15.0, 150.0, 0.5)]}
    basic_input = np.zeros((steps, n))
    basic_input[:, 0] = pulse_current(duration_ms=duration, dt_ms=dt_ms, pulses=source_recipe["pulses"])
    inhibition_input = basic_input.copy()
    inhibition_input[:, 10] = pulse_current(duration_ms=duration, dt_ms=dt_ms, pulses=inhibitor_recipe["pulses"])
    basic_input.flags.writeable = False
    inhibition_input.flags.writeable = False
    chain = tuple(Synapse(i, i + 1, 1.3, 1.0) for i in range(9))
    branch_pairs = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (2, 6), (6, 7), (7, 8), (8, 9))
    branching = tuple(Synapse(a, b, 1.3, 1.0) for a, b in branch_pairs)
    common = {"n_neurons": n, "inhibitory_neurons": (10,)}
    return (
        CircuitExperiment("chain", "Signal propagation",
                          "A brief input reaches N0; the only path to N9 is through the chain.",
                          Network(**common, synapses=chain), basic_input, (source_recipe,)),
        CircuitExperiment("cut_chain", "One connection removed",
                          "Same cells and input as chain; only the N4 -> N5 connection is removed.",
                          Network(**common, synapses=tuple(s for s in chain if s.source != 4)), basic_input, (source_recipe,)),
        CircuitExperiment("branch", "A signal splits into two paths",
                          "N2 connects to N3 and N6; downstream activity is calculated on both paths.",
                          Network(**common, synapses=branching), basic_input, (source_recipe,)),
        CircuitExperiment("inhibition_control", "Inhibitor driven, connection absent",
                          "N10 receives a separate input but has no outgoing connection to the chain.",
                          Network(**common, synapses=chain), inhibition_input, (source_recipe, inhibitor_recipe)),
        CircuitExperiment("inhibited_chain", "Inhibitory connection added",
                          "Identical to inhibition_control except for a negative N10 -> N5 connection.",
                          Network(**common, synapses=chain + (Synapse(10, 5, -0.3, 1.0),)),
                          inhibition_input, (source_recipe, inhibitor_recipe)),
        CircuitExperiment("recurrent_loop", "The pathway returns to its source",
                          "Identical to chain except that N9 now connects back to N0. Persistent activity is not learned memory.",
                          Network(**common, synapses=chain + (Synapse(9, 0, 1.3, 1.0),)), basic_input, (source_recipe,)),
    )
