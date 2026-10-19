"""Literal input comparison for the UI, kept outside neural inference.

This is a disclosed equality check against the captured example pair. It does
not determine or filter the spiking circuit's voltage-based class preference.
"""

from .memory_lab import Signal, Task


def compare_input(signal, task):
    if not isinstance(signal,Signal) or not isinstance(task,Task) or signal.kind!=task.kind:
        raise ValueError('Compare an input with a reference pair of the same kind.')
    match=next((i for i,p in enumerate(task.prototypes) if p==signal.content),None)
    content=''.join(map(str,signal.content))
    examples=[''.join(map(str,p)) for p in task.prototypes]
    if match is None:
        summary=f'{content} is neither Example 1 ({examples[0]}) nor Example 2 ({examples[1]}).'
    else:
        summary=f'{content} exactly matches Example {match+1} ({examples[match]}).'
    return {'kind':signal.kind,'matchedExample':match,'input':content,'examples':examples,
            'label':'Neither example' if match is None else f'Example {match+1}',
            'summary':summary,
            'basis':'Literal comparison only; not a neural novelty detector. The neural preference is calculated independently from voltages.'}
