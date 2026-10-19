"""SYNAPSE's interface-independent simulation engine."""

__version__ = "0.14.1"

from .lif import LIFParameters, SimulationResult, simulate
from .network import Network, NetworkResult, Synapse, simulate_network
from .plasticity import STDPParameters, PairSTDP

__all__ = ["LIFParameters", "SimulationResult", "simulate", "__version__",
           "Network", "NetworkResult", "Synapse", "simulate_network", "STDPParameters", "PairSTDP"]
