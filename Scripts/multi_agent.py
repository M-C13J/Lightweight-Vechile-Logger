
# multi_agent.py
# Multi-agent state tracking: detect platoons, leader/follower switches, swarm proximity.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import math

# Simple state tracker for multiple agents to detect platoons and roles
@dataclass
class AgentState:
    agent_id: str
    role: str = "independent"  # "leader", "follower", "independent"
    last_pos: Optional[tuple] = None
    last_heading: Optional[float] = None

# Multi-agent manager to track all agents and detect events
class MultiAgentManager:
    # Initialize with proximity threshold (meters) and heading tolerance (degrees)
    def __init__(self, prox_threshold: float = 5.0, heading_tol_deg: float = 10.0):
        self.prox_threshold = prox_threshold
        self.heading_tol = math.radians(heading_tol_deg)
        self.agents: Dict[str, AgentState] = {}

    # Get or create agent state
    def _get(self, aid: str) -> AgentState:
        if aid not in self.agents:
            self.agents[aid] = AgentState(agent_id=aid)
        return self.agents[aid]

    # Compute heading from velocity vector
    @staticmethod
    def _heading(vx: float, vy: float) -> float:
        return math.atan2(vy, vx)

    # Compute 2D distance between two points
    @staticmethod
    def _dist(a: tuple, b: tuple) -> float:
        return math.hypot(a[0]-b[0], a[1]-b[1])

    # Update with a standardized record; returns detected multi-agent events (if any)
    def update(self, record: dict) -> List[dict]:
        """Update with a standardized record; returns detected multi-agent events (if any)."""
        aid = record.get('agent_id','?')
        pos = (record.get('position',{}).get('x',0.0), record.get('position',{}).get('y',0.0))
        vel = (record.get('velocity',{}).get('vx',0.0), record.get('velocity',{}).get('vy',0.0))
        head = self._heading(vel[0], vel[1])
        s = self._get(aid)
        s.last_pos, s.last_heading = pos, head

        events = []
        # crude platoon detection: if two+ agents are within prox_threshold and headings similar
        close = []
        for other_id, other in self.agents.items():
            if other_id == aid or other.last_pos is None or other.last_heading is None:
                continue
            if self._dist(pos, other.last_pos) <= self.prox_threshold and abs(head - other.last_heading) <= self.heading_tol:
                close.append(other_id)

        if close:
            # designate the one with higher speed as leader
            speed = math.hypot(*vel)
            leaders = [aid]
            for oid in close:
                o = self.agents[oid]
                ov = (0.0, 0.0)  # approximate; if velocity not known, assume 0
                os = math.hypot(*ov)
                if speed >= os:
                    s.role = "leader"
                    self.agents[oid].role = "follower"
                else:
                    s.role = "follower"
                    self.agents[oid].role = "leader"
                leaders.append(oid)
            events.append({
                "type": "platoon_detected",
                "participants": sorted(leaders),
                "timestamp_ns": record.get("timestamp_ns", 0),
            })
        return events
