"""Supervised STDP temporal-order experiment, with label-free neural inference.

This deliberately small task can be solved by recency. It does not establish
general sequence learning. Test labels are used only after predictions exist.
"""

from dataclasses import asdict, dataclass
import math
import numpy as np

from .lif import LIFParameters, step_count
from .network import Network, Synapse, simulate_network
from .plasticity import STDPParameters
from .plasticity_experiments import frozen_network

CONDITIONS = ('before', 'trained', 'learning_disabled', 'shuffled_teachers')
DEFAULT_SEEDS = (11, 29, 47, 83, 101)


@dataclass(frozen=True)
class LearningConfig:
    dt_ms: float = 0.1
    train_examples: int = 32
    test_examples: int = 24
    training_trial_ms: float = 150.0
    evaluation_ms: float = 120.0
    readout_ms: float = 90.0
    teacher_lag_ms: float = 5.0

    def __post_init__(self):
        if self.dt_ms not in (0.05, 0.1, 0.2):
            raise ValueError('supported learning time steps are 0.05, 0.1 and 0.2 ms')
        for name, low, high in (('train_examples', 8, 64), ('test_examples', 4, 100)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high or value % 2:
                raise ValueError(f'{name} must be an even integer in [{low}, {high}]')
        # Fix the protocol timing instead of silently accepting unsupported tasks.
        for name, value in (('training_trial_ms', 150.0), ('evaluation_ms', 120.0),
                            ('readout_ms', 90.0), ('teacher_lag_ms', 5.0)):
            if getattr(self, name) != value:
                raise ValueError(f'this protocol fixes {name} at {value}')


@dataclass(frozen=True)
class TemporalExample:
    example_id: str
    source_times_ms: tuple[float, float, float, float]
    label: int  # 0: A then B; 1: B then A. Not passed to neural inference.


def make_examples(rng, count, dt_ms, prefix, *, excluded=()):
    if type(count) is not int or count < 2 or count % 2:
        raise ValueError('example count must be positive, even, and at least two')
    labels = rng.permutation(np.repeat([0, 1], count // 2))
    seen = set(excluded)
    examples = []
    for i, label in enumerate(labels):
        for _ in range(1000):
            onset = rng.uniform(20, 30)
            gap = rng.uniform(24, 36)
            centres = (onset, onset + gap) if label == 0 else (onset + gap, onset)
            times = tuple(float(round((centre + rng.uniform(-0.6, 0.6)) / dt_ms) * dt_ms)
                          for centre in centres for _ in range(2))
            if times not in seen:
                seen.add(times)
                break
        else:
            raise ValueError('could not generate distinct timing examples')
        examples.append(TemporalExample(f'{prefix}_{i:03}', times, int(label)))
    return tuple(examples)


def initial_network(rng):
    weights = np.clip(rng.normal(0.1, 0.005, 8), 0.08, 0.12)
    edges = tuple(Synapse(source, target, float(weights[2 * source + target - 4]), 1.0)
                  for source in range(4) for target in (4, 5))
    return Network(6, edges)


def source_current(source_times_ms, config, *, teacher_label=None, duration_ms=None):
    """Build stimulus from four event times. No test label is needed or accepted.

    teacher_label is used only by the training protocol. At test it stays None.
    """
    times = np.asarray(source_times_ms, dtype=float)
    if times.shape != (4,) or not np.isfinite(times).all() or np.any(times < 0):
        raise ValueError('four finite nonnegative source times are required')
    duration = config.evaluation_ms if duration_ms is None else duration_ms
    steps = step_count(duration, config.dt_ms)
    drive = np.zeros((steps, 6))
    p = LIFParameters()
    amplitude = 2 * (p.threshold_mV - p.rest_mV) / (p.resistance_MOhm * -math.expm1(-config.dt_ms / p.tau_ms))

    def add_pulse(cell, start):
        tick = round(start / config.dt_ms)
        if not 0 <= tick < steps:
            raise ValueError('a stimulus is outside the experiment duration')
        drive[tick, cell] += amplitude

    for cell, time_ms in enumerate(times):
        add_pulse(cell, time_ms)
    if teacher_label is not None:
        if type(teacher_label) is not int or teacher_label not in (0, 1):
            raise ValueError('teacher label must be 0 or 1')
        early, late = sorted((float(times[:2].mean()), float(times[2:].mean())))
        # The assigned class output fires after the late group; the other after
        # the early group. Both outputs get one teaching pulse in every trial.
        for cell, start in ((4 + teacher_label, late), (5 - teacher_label, early)):
            add_pulse(cell, start + 1.0 + config.teacher_lag_ms)
    return drive


def train(network, examples, teacher_labels, config, *, learning_enabled=True):
    if len(examples) != len(teacher_labels) or len(examples) == 0:
        raise ValueError('one teacher label is required per training example')
    if any(not isinstance(label, (int, np.integer)) or isinstance(label, (bool, np.bool_))
           or label not in (0, 1) for label in teacher_labels):
        raise ValueError('training teacher labels must be integers 0 or 1')
    drive = np.vstack([source_current(example.source_times_ms, config, teacher_label=int(label),
                                     duration_ms=config.training_trial_ms)
                       for example, label in zip(examples, teacher_labels)])
    parameters = STDPParameters(w_min_nA=0.001, w_max_nA=0.25)
    result = simulate_network(network, duration_ms=len(examples) * config.training_trial_ms,
                              dt_ms=config.dt_ms, external_current_nA=drive,
                              plasticity=parameters, learning_enabled=learning_enabled)
    # No extra spontaneous spikes should confound this teaching protocol.
    if not np.array_equal(result.spike_counts, np.full(6, len(examples))):
        raise ValueError('training produced extra/missing spikes; protocol assumptions failed')
    return result


def neural_prediction(network, source_times_ms, config):
    """No labels, teaching currents, stored examples, or plasticity in inference."""
    drive = source_current(source_times_ms, config)
    a, b = np.asarray(source_times_ms[:2]), np.asarray(source_times_ms[2:])
    if not (a.max() < b.min() or b.max() < a.min()):
        raise ValueError('the two input groups must not overlap for this order task')
    if max(source_times_ms) + 1 >= config.readout_ms:
        raise ValueError('inputs must arrive before the fixed 90 ms readout')
    result = simulate_network(network, duration_ms=config.evaluation_ms, dt_ms=config.dt_ms,
                              external_current_nA=drive)
    if int(result.spike_counts[4:6].sum()) != 0:
        raise ValueError('this voltage-readout protocol requires subthreshold output cells')
    readout_tick = round(config.readout_ms / config.dt_ms)
    scores = result.voltage_mV[readout_tick, 4:6] - network.neuron.rest_mV
    margin = float(scores[0] - scores[1])
    prediction = 0 if abs(margin) <= 1e-10 else int(scores[1] > scores[0])
    return {'prediction': prediction, 'score_AB_mV': float(scores[0]), 'score_BA_mV': float(scores[1]),
            'margin_mV': margin}, result


def classification_metrics(labels, predictions):
    labels, predictions = np.asarray(labels), np.asarray(predictions)
    if labels.ndim != 1 or predictions.shape != labels.shape or len(labels) == 0:
        raise ValueError('labels and predictions must be equal nonempty vectors')
    if not np.isin(labels, [0, 1]).all() or not np.isin(predictions, [0, 1]).all():
        raise ValueError('classification uses labels 0 and 1')
    matrix = np.zeros((2, 2), dtype=int)
    for label, prediction in zip(labels, predictions):
        matrix[int(label), int(prediction)] += 1
    if np.any(matrix.sum(axis=1) == 0):
        raise ValueError('both classes are required for balanced accuracy')
    return {'accuracy': float(np.trace(matrix) / matrix.sum()),
            'balanced_accuracy': float(np.mean(np.diag(matrix) / matrix.sum(axis=1))),
            'confusion_matrix': matrix.tolist(), 'examples': int(matrix.sum())}


def evaluate(network, examples, config):
    rows = []
    for example in examples:
        prediction, _ = neural_prediction(network, example.source_times_ms, config)
        # Attach ground truth only AFTER computing the label-free prediction.
        rows.append({'example_id': example.example_id, **prediction, 'label': example.label})
    metrics = classification_metrics([x['label'] for x in rows], [x['prediction'] for x in rows])
    return rows, metrics


def run_seed(seed, config=None):
    config = config if config is not None else LearningConfig()
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('seed must be an integer in [0, 2**32)')
    children = np.random.SeedSequence(seed).spawn(4)
    init_rng, train_rng, test_rng, shuffle_rng = [np.random.default_rng(s) for s in children]
    network = initial_network(init_rng)
    training = make_examples(train_rng, config.train_examples, config.dt_ms, f's{seed}_train')
    test = make_examples(test_rng, config.test_examples, config.dt_ms, f's{seed}_test',
                         excluded=[x.source_times_ms for x in training])
    true_teachers = [x.label for x in training]
    shuffled_teachers = shuffle_rng.permutation(true_teachers).astype(int).tolist()
    trained = train(network, training, true_teachers, config)
    disabled = train(network, training, true_teachers, config, learning_enabled=False)
    shuffled = train(network, training, shuffled_teachers, config)
    networks = {'before': network, 'trained': frozen_network(network, trained.final_weights_nA),
                'learning_disabled': frozen_network(network, disabled.final_weights_nA),
                'shuffled_teachers': frozen_network(network, shuffled.final_weights_nA)}
    outcomes = {}
    for name, candidate in networks.items():
        predictions, metrics = evaluate(candidate, test, config)
        outcomes[name] = {'predictions': predictions, 'metrics': metrics,
                          'weights_nA': [s.weight_nA for s in candidate.synapses]}
    heuristic = [int(np.mean(x.source_times_ms[:2]) > np.mean(x.source_times_ms[2:])) for x in test]
    baseline = classification_metrics([x.label for x in test], heuristic)
    trial_end_indices = np.arange(1, len(training) + 1) * round(config.training_trial_ms / config.dt_ms)
    result = {'seed': seed, 'configuration': asdict(config), 'initial_network': asdict(network),
              'plasticity': asdict(STDPParameters(w_max_nA=0.25)),
              'training_examples': [asdict(x) for x in training], 'test_examples': [asdict(x) for x in test],
              'true_teachers': true_teachers, 'shuffled_teachers': shuffled_teachers,
              'conditions': outcomes, 'last_event_heuristic': baseline,
              'weights_after_each_training_trial_nA': trained.weight_history_nA[trial_end_indices].tolist(),
              'shuffled_weights_after_each_training_trial_nA': shuffled.weight_history_nA[trial_end_indices].tolist(),
              'initial_weights_nA': trained.initial_weights_nA.tolist(),
              'disabled_weights_unchanged': bool(np.array_equal(disabled.initial_weights_nA, disabled.final_weights_nA)),
              'training_spike_counts': trained.spike_counts.tolist()}
    return result


def model_payload(seed_result, condition='trained'):
    if condition not in CONDITIONS:
        raise ValueError('unsupported model condition')
    return {'format': 'synapse-temporal-order-v1', 'seed': seed_result['seed'],
            'condition': condition, 'configuration': seed_result['configuration'],
            'weights_nA': seed_result['conditions'][condition]['weights_nA'],
            'output_names': ['A then B', 'B then A'],
            'readout': 'LIF output voltages at 90 ms, argmax; no plasticity or teaching at inference'}


def load_model_payload(payload):
    if not isinstance(payload, dict) or payload.get('format') != 'synapse-temporal-order-v1':
        raise ValueError('unsupported SYNAPSE task model format')
    try:
        config = LearningConfig(**payload['configuration'])
        weights = np.asarray(payload['weights_nA'], dtype=float)
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError('model configuration or weights are invalid') from exc
    if weights.shape != (8,) or not np.isfinite(weights).all() or np.any(weights < 0.001) or np.any(weights > 0.25):
        raise ValueError('this model requires eight weights within [0.001, 0.25] nA')
    network = Network(6, tuple(Synapse(source, target, float(weights[2*source+target-4]))
                              for source in range(4) for target in (4, 5)))
    return network, config
