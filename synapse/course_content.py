"""Original course explanations, source links and a consistent learning sequence.

Text is deliberately separate from numerical engines. No anatomical label is
used to relabel an engineered model population as a real human brain region.
"""

SOURCES = {
    'anatomy': ('OpenStax · Central nervous system', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/13-2-the-central-nervous-system'),
    'cells': ('OpenStax · Nervous tissue', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/12-2-nervous-tissue'),
    'glia': ('Purves et al. · Neuroglial cells', 'https://www.ncbi.nlm.nih.gov/books/NBK10869/'),
    'rest': ('Purves et al. · Ionic basis of resting potential', 'https://www.ncbi.nlm.nih.gov/books/NBK10931/'),
    'forces': ('Purves et al. · Forces that create membrane potentials', 'https://www.ncbi.nlm.nih.gov/books/NBK11102/'),
    'spikes': ('OpenStax · The action potential', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/12-4-the-action-potential'),
    'hh': ('Hodgkin & Huxley (1952) · Membrane-current model', 'https://pubmed.ncbi.nlm.nih.gov/12991237/'),
    'synapses': ('OpenStax · Communication between neurons', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/12-5-communication-between-neurons'),
    'chemical': ('Purves et al. · Chemical synapses', 'https://www.ncbi.nlm.nih.gov/books/NBK11009/'),
    'processing': ('OpenStax · Central processing', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/14-2-central-processing'),
    'sensory': ('OpenStax · Sensory perception', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/14-1-sensory-perception'),
    'motor': ('OpenStax · Motor responses', 'https://openstax.org/books/anatomy-and-physiology-2e/pages/14-3-motor-responses'),
    'ltp': ('Purves et al. · Long-term synaptic potentiation', 'https://www.ncbi.nlm.nih.gov/books/NBK10878/'),
    'nmda': ('Biology of the NMDA Receptor · Activation mechanisms', 'https://www.ncbi.nlm.nih.gov/books/NBK5274/'),
    'molecular': ('Neural Plasticity and Memory · Molecular mechanisms', 'https://www.ncbi.nlm.nih.gov/books/NBK3913/'),
    'timing': ('Bi & Poo (1998) · Timing-dependent plasticity in rat cell cultures', 'https://pubmed.ncbi.nlm.nih.gov/9852584/'),
    'memory': ('Scoville & Milner (1957) · Human medial-temporal lesions and memory', 'https://pubmed.ncbi.nlm.nih.gov/13406589/'),
    'interference': ('Holton et al. (2026; online 2025) · Human/network transfer and interference', 'https://pubmed.ncbi.nlm.nih.gov/41168425/'),
    'reward': ('Pessiglione et al. (2006) · Human reward learning', 'https://pubmed.ncbi.nlm.nih.gov/16929307/'),
}

CHAPTERS = (
    {'id':'brain','number':'01','title':'Meet the human brain','nav':'01 · Brain and cells',
     'question':'How can one organ support so many different abilities?',
     'relatable':'Reading a message involves vision, language, memory and attention. These abilities involve interacting systems rather than a single “reading neuron.”',
     'goals':['Distinguish brain regions from model populations.','Explain why neurons need other cells.','Move between organ, cell and circuit scales.'],
     'sections':[
         ('A connected organ', 'The brain and spinal cord form the central nervous system. Peripheral nerves connect it with the body. The cerebral cortex is a folded outer sheet; deeper nuclei, connecting fibres, the cerebellum and brainstem also contribute. A region can participate in several functions, and a function can recruit several regions. The map below is an orientation guide, not a set of isolated mental compartments.', ['anatomy']),
         ('Look closer: a neuron', 'In a typical multipolar neuron, branched dendrites receive many contacts. The soma contains the nucleus and cellular machinery. The axon initial segment often initiates action potentials; an axon can then branch to reach multiple targets. Myelin wraps portions of some axons, with gaps called nodes of Ranvier. Real neuron shapes and input locations vary.', ['cells']),
         ('The cells around the signals', 'Astrocytes help regulate the local chemical environment. Oligodendrocytes make myelin in the central nervous system; Schwann cells do this in peripheral nerves. Microglia provide immune surveillance and respond to tissue changes. These cells participate in maintaining functioning tissue; a diagram containing only neurons leaves out essential biology.', ['glia','cells'])],
     'deep':('Why location alone is not an explanation', 'Knowing where activity occurs is different from knowing how that activity produces a function. Connections, cell properties, timing and bodily context matter too. Grey matter is rich in cell bodies, dendrites and synapses; white matter contains many myelinated axons. Neither is a separate “thinking material.” Our network columns group engineered roles so we can inspect a model; they are not frontal, temporal or other anatomical areas.', ['anatomy','processing']),
     'takeaway':'Brain regions contain interacting cellular circuits. The circuit view helps investigate a principle at a different scale from an anatomical map.',
     'reflection':'Choose one region and one cell structure. How do their scales and roles differ?',
     'sources':['anatomy','cells','glia','processing']},
    {'id':'signals','number':'02','title':'How a neuron sends a signal','nav':'02 · Electrical signals',
     'question':'What actually changes when a neuron fires?',
     'relatable':'A stronger input need not create a taller spike. Investigate whether it changes how often this simplified neuron fires instead.',
     'goals':['Explain voltage across a membrane.','Distinguish ion-channel dynamics from a threshold model.','Compare a measured response with an illustration.'],
     'sections':[
         ('A voltage across a membrane', 'Membrane potential is the electrical potential inside a cell relative to outside. Unequal ion concentrations and selective membrane permeability help produce it. At rest, potassium permeability is especially important in many neurons. The sodium–potassium pump maintains concentration gradients over time; it is not a switch that directly draws each spike’s falling phase.', ['rest']),
         ('An action potential unfolds', 'For a typical axonal spike, voltage-dependent sodium channels support rapid depolarisation. Sodium-channel inactivation and increased potassium conductance help repolarise the membrane. A period of increased potassium conductance can produce an after-hyperpolarisation. During absolute refractoriness another spike cannot be initiated normally; during relative refractoriness a stronger input may be needed. Exact voltages and waveforms differ between cells.', ['spikes','hh']),
         ('Propagation and coding', 'Local current can depolarise neighbouring membrane and recruit more voltage-dependent channels. In myelinated axons, spikes are regenerated at nodes, while current spreads beneath the insulated segments. This is saltatory conduction. Neural information can depend on spike timing, rate and populations, rather than spike height alone. The model experiment below focuses on rate and threshold.', ['spikes'])],
     'deep':('What the numerical neuron keeps', 'The leaky integrate-and-fire model combines current integration, passive decay, a threshold, reset and an absolute refractory clamp. It omits sodium/potassium gating and does not calculate a biological spike waveform. Hodgkin and Huxley instead built a conductance-based description from squid-axon experiments. That influential preparation is not a direct measurement of every human neuron. Our illustrative waveform and our LIF trace therefore answer different questions.', ['hh']),
     'takeaway':'An action potential is a changing electrical state of membrane. Our threshold model preserves selected effects while omitting the underlying channel kinetics.',
     'reflection':'What changed when you increased the input: spike count, model threshold, or a biological waveform?',
     'sources':['rest','forces','spikes','hh']},
    {'id':'synapses','number':'03','title':'How neurons communicate','nav':'03 · Synapses',
     'question':'Does receiving a signal always make the next neuron fire?',
     'relatable':'Many messages can arrive without producing an immediate response. A receiving neuron integrates effects over time and across inputs.',
     'goals':['Follow a chemical synapse step by step.','Distinguish an incoming signal from an outgoing spike.','Explain excitation, inhibition and receptor dependence.'],
     'sections':[
         ('From electrical event to chemical message', 'At a chemical synapse, an arriving action potential can open presynaptic voltage-gated calcium channels. Calcium entry promotes vesicle fusion and transmitter release. Transmitter crosses the cleft and binds receptors on the receiving membrane. Receptor effects and transmitter clearance shape the response; the cleft is not an electrical wire joining the two cells.', ['chemical']),
         ('Receiving is not the same as firing', 'A postsynaptic potential is a graded voltage response. Inputs close together in time can interact through temporal summation; inputs at different locations can interact through spatial summation. Their size, timing and location matter. The axon’s output depends on how these effects interact with the cell’s current state.', ['synapses']),
         ('Excitation and inhibition depend on mechanism', 'A receptor’s ion selectivity and the relevant reversal potential influence its effect. Excitatory inputs tend to promote spiking; inhibitory inputs can reduce it by hyperpolarising or by shunting other currents. A chemical name alone is insufficient without its receptor and cellular context. Our signed-current example demonstrates depolarisation versus hyperpolarisation, not conductance-based shunting.', ['synapses'])],
     'deep':('Fast and slower effects', 'Ionotropic receptors directly gate channels. Metabotropic receptors act through intracellular signalling and can change excitability or other processes over a different timescale. Electrical synapses use gap junctions to allow direct current flow. The chemical animation shows one pathway; it is not an account of every synapse. In the numerical experiment, release and receptor details are replaced by a delayed, exponentially decaying current.', ['chemical','synapses']),
     'takeaway':'A transmitted event can produce a subthreshold response. Biological synapses influence the chance and timing of output in ways that depend on the receiving cell.',
     'reflection':'Why does a visible incoming signal not guarantee a new spike in B?',
     'sources':['chemical','synapses']},
    {'id':'networks','number':'04','title':'From one connection to a network','nav':'04 · Branching networks',
     'question':'How does one input affect several pathways?',
     'relatable':'A sight or sound can lead to several possible responses. Follow a signal as its effects spread through a small, inspectable circuit.',
     'goals':['Follow convergence, divergence and recurrence.','Compare matched conditions.','Separate a model role from an anatomical region.'],
     'sections':[
         ('Patterns of connections matter', 'Divergence sends influence toward several targets; convergence brings several inputs toward a target. Recurrent connections create feedback paths. Excitatory and inhibitory circuits can shape which responses occur and when. Their effects depend on timing and current state, so a wiring diagram alone cannot predict all activity.', ['processing','synapses']),
         ('The whole circuit is visible', 'The view below has 50 calculated neurons and 690 directed connections. Sensory, association, inhibition and action are roles assigned in this engineered circuit. Launching a pulse calculates spikes and arrivals; a dot follows an arrival recorded by the engine. An inactive connection remains drawn, because wiring and current activity are different things.', []),
         ('Ask a causal question', 'Change one pathway’s transmission while keeping the starting state and external pulse matched. Compare the resulting activity. A blocked pathway may reduce downstream activity; it need not silence every neuron if alternative routes or existing currents remain. Restore transmission and rerun to test reversibility. This is a temporary experimental control, not a simulation of clinical injury or recovery.', [])],
     'deep':('Read a recording rather than a story', 'A flash marks a computed spike, not an individual thought. Travelling markers represent delayed transmissions, not literal particles moving across the entire circuit. Voltage, spike counts and arrival times provide different observations. Animation speed changes the display only. In this chapter learning is frozen, so a response difference comes from the chosen transmission setting rather than trained weights.', []),
     'takeaway':'A network transforms an input through its connections and evolving state. A controlled comparison helps identify the effect of one chosen change.',
     'reflection':'Which downstream population changed when you blocked the pathway? Which input stayed identical?',
     'sources':['processing','synapses']},
    {'id':'learning','number':'05','title':'Learning, memory and changing connections','nav':'05 · Learning and memory',
     'question':'How can experience change a future response?',
     'relatable':'Learning a new button mapping can interfere with an old mapping. First study a change at one connection, then compare competing associations.',
     'goals':['Distinguish transient activity from retained changes.','Connect plasticity experiments with their biological preparation.','Interpret interference without equating a model with a whole brain.'],
     'sections':[
         ('Activity now and a change that lasts', 'A brief current can decay while a change in synaptic efficacy remains. Long-term potentiation and depression describe persistent increases and decreases in synaptic effectiveness under specified conditions. At some hippocampal glutamatergic synapses, calcium-dependent signalling and changes in receptor function contribute. This is one family of mechanisms; memory also involves circuits, molecular processes and multiple timescales.', ['ltp']),
         ('What timing experiments support', 'Bi and Poo paired activity in cultured rat hippocampal neurons. Relative timing, initial strength and cell type affected the observed modifications. The lesson below implements a declared additive timing rule inspired by such work. Its exact amplitudes, bounds and simultaneous-event convention are model choices, not universal facts about human learning.', ['timing']),
         ('Memory has multiple systems', 'Scoville and Milner’s human lesion report helped establish the importance of medial-temporal structures for forming certain new memories. It does not imply that all memories sit in one location or one weight. Our two-class association model stores trained readout weights; a hippocampal mechanism is not implemented by renaming those weights “memory.”', ['memory'])],
     'deep':('Interference, rehearsal and what counts as learning', 'Holton and colleagues compared sequential rule learning in people and neural networks, finding related transfer/interference patterns under their task conditions. Shared behaviour does not establish identical biological mechanisms. In our association experiment, new-only teaching and interleaved old/new teaching have matched budgets. Count both old responses retained and new responses learned. Rehearsal may fail, and externally supplied examples do not simulate sleep or spontaneous replay.', ['interference']),
     'takeaway':'A measured retained change can alter a later response. Explaining human memory requires more than observing weights change in a small model.',
     'reflection':'Which evidence shows a retained effect rather than activity caused only by the teaching pulse?',
     'sources':['ltp','nmda','molecular','timing','memory','interference']},
    {'id':'behaviour','number':'06','title':'From sensation to action and feedback','nav':'06 · Brain and behaviour',
     'question':'How can consequences influence the next choice?',
     'relatable':'Imagine choosing between two unfamiliar buttons and discovering which one works. Sensory input, an action and its later consequence are distinct events.',
     'goals':['Separate observation, choice, execution and feedback.','Read counts in context rather than treating them as intelligence scores.','Connect a feedback model with bounded biological evidence.'],
     'sections':[
         ('Sensing requires transformation', 'Sensory receptors convert particular physical or chemical events into neural signals. Further processing uses pathways and networks rather than a direct copy of the world. Perception depends on how signals are organised and interpreted; our two artificial cues are engineered inputs, not a model of retinal or auditory transduction.', ['sensory']),
         ('An action recruits interacting systems', 'Voluntary movement involves cortical pathways and lower motor neurons, with contributions from systems including the basal nuclei and cerebellum. Sensory feedback can influence control. A schematic “input → choice → movement” is a useful starting point, but biological motor control includes parallel pathways and loops rather than a single straight chain.', ['motor']),
         ('Feedback and future choices', 'Pessiglione and colleagues used a human choice task, brain imaging and pharmacological manipulation to investigate dopamine-dependent reward prediction errors. Their findings connect dopamine function with learning under those conditions. The scalar feedback in this app is an engineering signal; it is neither a dopamine concentration nor a complete dopamine prediction-error model.', ['reward'])],
     'deep':('Follow causality in the branching view', 'In the calculation below, a cue drives input cells. The decoder reads neural voltages before the outcome is available. A selected action is then executed, and feedback arrives later to change eligible links. Exploration can also affect the choice. A short run of correct choices is not a general intelligence score; online success, frozen evaluation and a control answer different questions.', []),
     'takeaway':'Observation, activity, action and consequence are separate parts of a learning loop. Biological explanations must specify which mechanism each experiment actually tests.',
     'reflection':'Was the outcome available when the action was chosen? What would make a fair learning comparison?',
     'sources':['sensory','motor','reward']},
)

CHAPTER_BY_ID = {c['id']: c for c in CHAPTERS}
NAV_LABELS = ['Learning journey'] + [c['nav'] for c in CHAPTERS] + ['Glossary', 'My learning notebook']

REGIONS = [
    {'id':'frontal','name':'Frontal cortex','detail':'Contributes to planning, control and movement. Its functions depend on connections with other areas.'},
    {'id':'parietal','name':'Parietal cortex','detail':'Participates in bodily sensation and spatial processing.'},
    {'id':'occipital','name':'Occipital cortex','detail':'Contains important visual-processing areas; vision also involves other regions.'},
    {'id':'temporal','name':'Temporal cortex','detail':'Participates in auditory processing and aspects of memory and recognition.'},
    {'id':'cerebellum','name':'Cerebellum','detail':'Contributes to coordination, timing and learning of movement, among other functions.'},
    {'id':'brainstem','name':'Brainstem','detail':'Connects brain and spinal pathways and contains nuclei involved in vital functions and arousal.'},
    {'id':'hippocampus','name':'Hippocampus · deeper structure','detail':'Important for forming certain new memories. Shown separately in a simplified medial cutaway.'},
    {'id':'thalamus','name':'Thalamus · deeper structure','detail':'Participates in multiple relay and processing circuits. Shown separately in a simplified medial cutaway.'},
]

GLOSSARY = {
    'Action potential': ('A regenerative electrical event in excitable membrane. Our LIF model records a threshold crossing rather than calculating its waveform.', 'spikes'),
    'Axon': ('A neuronal process that carries output toward targets and can branch.', 'cells'),
    'Dendrite': ('A neuronal process that receives many inputs; dendrites can also actively process signals.', 'cells'),
    'Membrane potential': ('Voltage inside the cell relative to outside, expressed here in millivolts.', 'rest'),
    'Ion channel': ('A membrane protein that permits particular ions to move according to its gating and electrochemical conditions.', 'spikes'),
    'Myelin': ('Insulating membrane around portions of axons, made by particular glial cells.', 'cells'),
    'Synapse': ('A specialised contact through which a cell influences a target.', 'chemical'),
    'Neurotransmitter': ('A chemical messenger released at chemical synapses that acts through receptors.', 'chemical'),
    'Receptor': ('A protein that responds to a ligand and can directly or indirectly affect cell activity.', 'synapses'),
    'Excitation': ('An influence tending to promote neuronal spiking in its cellular context.', 'synapses'),
    'Inhibition': ('An influence tending to reduce neuronal spiking; it need not always hyperpolarise the cell.', 'synapses'),
    'Plasticity': ('A change in neural properties or connections; its mechanism and timescale must be specified.', 'ltp'),
    'LTP / LTD': ('Long-term potentiation/depression: persistent increases/decreases in synaptic efficacy under defined experimental conditions.', 'ltp'),
    'STDP': ('Spike-timing-dependent plasticity: changes associated with relative event timing, with rules that depend on the biological preparation.', 'timing'),
    'Hippocampus': ('A medial-temporal structure important for aspects of forming new memories; it is not the only memory-related structure.', 'memory'),
    'Frozen evaluation': ('A model test in which learning updates are disabled so the response of a fixed model can be measured.', None),
    'Connection strength / weight': ('In our current-based model, the size of a synaptic current jump in nanoamperes. It is not a literal count of receptors.', None),
    'Recurrent circuit': ('A circuit with feedback paths; persistence of activity alone does not demonstrate a learned memory.', 'processing'),
}


def source_markdown(keys):
    return ' · '.join(f'[{SOURCES[k][0]}]({SOURCES[k][1]})' for k in dict.fromkeys(keys))
