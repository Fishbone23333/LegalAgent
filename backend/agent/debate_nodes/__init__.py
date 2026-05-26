"""Debate Multi-Agent Nodes"""
from .challenger import challenger_node
from .defender import defender_node
from .judge import judge_node
from .negotiation import negotiation_node

__all__ = ["challenger_node", "defender_node", "judge_node", "negotiation_node"]
