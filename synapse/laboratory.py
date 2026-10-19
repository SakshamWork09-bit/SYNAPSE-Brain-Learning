"""Bounded UI operations. No Streamlit dependency; the engine owns all physics."""

from collections import deque
from dataclasses import dataclass
import csv
from io import StringIO, BytesIO
import json

import numpy as np

from .checkpoints import checkpoint_bytes, session_from_checkpoint_bytes
from .integrated import IntegratedSession, IntegratedConfig, MODES

MODE_LABELS = {'learning': 'Outcome feedback', 'learning_disabled': 'Learning disabled',
               'random_feedback': 'Uncorrelated feedback'}
GROUP_LABELS = ('Sensory A', 'Sensory B', 'Association A', 'Association B',
                'Inhibitory A', 'Inhibitory B', 'Action 0', 'Action 1')
GROUP_COLORS = ('#73cfca', '#43ada6', '#b4a5ee', '#8870c6', '#eeab72', '#cf8253', '#6aaef4', '#397dc8')


@dataclass(frozen=True)
class ActivityWindow:
    trial: int
    time_ms: np.ndarray
    voltage_mV: np.ndarray
    current_time_ms: np.ndarray
    synaptic_current_nA: np.ndarray
    spike_times_ms: np.ndarray
    spike_neurons: np.ndarray
    initial_weights_nA: np.ndarray
    final_weights_nA: np.ndarray
    arrival_times_ms: np.ndarray
    arrival_synapses: np.ndarray
    arrival_weights_nA: np.ndarray

    @classmethod
    def from_blocks(cls, trial, blocks, initial_weights, final_weights, transmissions):
        # Adjacent boundaries occur once. The final endpoint voltage is retained.
        return cls(trial,
                   np.concatenate([b.time_ms[:-1] for b in blocks] + [blocks[-1].time_ms[-1:]]),
                   np.vstack([b.voltage_mV[:-1] for b in blocks] + [blocks[-1].voltage_mV[-1:]]),
                   np.concatenate([b.time_ms[:-1] for b in blocks]),
                   np.vstack([b.synaptic_current_nA for b in blocks]),
                   np.concatenate([b.spike_times_ms for b in blocks]),
                   np.concatenate([b.spike_neurons for b in blocks]),
                   np.array(initial_weights,dtype=float,copy=True),
                   np.array(final_weights,dtype=float,copy=True),
                   np.array([e[0] for e in transmissions],dtype=float),
                   np.array([e[1] for e in transmissions],dtype=np.int64),
                   np.array([e[2] for e in transmissions],dtype=float))


class Laboratory:
    """One session, at most eight recent dense traces, and paused-by-default UI state."""
    def __init__(self, session=None):
        self.session = session if session is not None else IntegratedSession()
        if not isinstance(self.session, IntegratedSession):
            raise ValueError('laboratory requires an integrated session')
        self.windows = deque(maxlen=8)

    @property
    def remaining(self):
        return self.session.config.session_limit - self.session.trial_index

    def advance(self, count=1):
        if type(count) is not int or not 1 <= count <= 20:
            raise ValueError('advance one to twenty experiences at a time')
        count = min(count, self.remaining)
        for i in range(count):
            # Earlier batch windows would be evicted; never allocate them.
            capture = i >= count-8
            if capture:
                before=self.session.engine.weights.copy()
                with self.session.engine.record_transmissions() as transmissions:
                    row,blocks=self.session.step_trial(record=True)
                self.windows.append(ActivityWindow.from_blocks(row['trial'],blocks,before,
                                    self.session.engine.weights,transmissions))
            else:
                self.session.step_trial(record=False)
        return count

    def restore(self, data):
        replacement = session_from_checkpoint_bytes(data)
        # Engine validation checks physical state; also require the display history.
        try:
            for row in replacement.records:
                for name, shape in (('action_scores_mV',(2,)),('action_probabilities',(2,)),
                                    ('weight_preferences_nA',(4,))):
                    values=np.asarray(row[name],dtype=float)
                    if values.shape!=shape or not np.isfinite(values).all():
                        raise ValueError('invalid display history')
                if not np.isfinite(float(row['delivered_feedback'])) or not 0<=row['delivered_feedback']<=1:
                    raise ValueError('invalid delivered feedback')
                if row['phase']!=int(row['trial']>=replacement.config.reversal_trial):
                    raise ValueError('invalid environment phase')
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError('checkpoint history is incomplete or invalid') from exc
        self.session = replacement
        self.windows.clear()

    def checkpoint(self):
        return checkpoint_bytes(self.session)

    def experiences_csv(self):
        stream = StringIO(newline='')
        fields = ['experience', 'cue', 'phase', 'action', 'actual_reward', 'delivered_feedback',
                  'action_0_score_mV', 'action_1_score_mV', 'action_0_probability', 'action_1_probability',
                  'A_action0_nA', 'A_action1_nA', 'B_action0_nA', 'B_action1_nA', 'update_l2_nA']
        writer = csv.writer(stream)
        writer.writerow(fields)
        for row in self.session.records:
            writer.writerow([row['trial']+1, 'AB'[row['cue']], row['phase'], row['action'], row['reward'],
                             row['delivered_feedback'], *row['action_scores_mV'],
                             *row['action_probabilities'], *row['weight_preferences_nA'], row['update_l2_nA']])
        return stream.getvalue().encode('utf-8')

    def trace_bytes(self, trial):
        window = next((w for w in self.windows if w.trial == trial), None)
        if window is None:
            raise ValueError('this experience has no retained dense trace')
        stream = BytesIO()
        np.savez_compressed(stream, **{k:v for k,v in vars(window).items()},
                            neuron_indices=np.arange(50))
        return stream.getvalue()


def run_comparison(seed, config=None, experiences=200):
    """Independent sessions with matched seeded wiring/cues; never touches a live lab."""
    config = config if config is not None else IntegratedConfig()
    if type(experiences) is not int or not config.reversal_trial+20 <= experiences <= min(400,config.session_limit):
        raise ValueError('comparison needs twenty experiences after reversal, at most 400 total')
    results = {}
    for mode in MODES:
        lab = IntegratedSession(seed, mode=mode, config=config)
        for _ in range(experiences):
            lab.step_trial()
        results[mode] = lab.records
    assert all([r['cue'] for r in rows] == [r['cue'] for r in results['learning']] for rows in results.values())
    return results


def comparison_json(results, seed, reversal):
    return json.dumps({'seed':seed, 'reversal_after_experience':reversal,
                       'definition':'Online success; independent sessions, same wiring and cue stream per seed.',
                       'records':results}, indent=2, allow_nan=False).encode('utf-8')
