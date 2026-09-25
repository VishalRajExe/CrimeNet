"""
CrimeNet AI - Human-in-the-Loop @feedback Agent
Interprets investigator ground-truth feedback, updates graph topology and metadata,
re-aligns RAG context, and logs an immutable audit entry.
"""

import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from ..extraction.ner_extractor import GraphNode, GraphEdge
from ..audit_ledger import ImmutableAuditLedger, default_audit_ledger

logger = logging.getLogger(__name__)


@dataclass
class FeedbackResult:
    status: str  # 'applied', 'rejected', 'ignored'
    action_type: str
    target_id: Optional[str]
    message: str
    audit_id: Optional[str] = None
    updated_node: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "status": self.status,
            "action": self.action_type,
            "targetId": self.target_id,
            "message": self.message,
            "auditId": self.audit_id,
        }
        if self.updated_node:
            d["updatedNode"] = self.updated_node
        return d


class FeedbackAgent:
    """Interprets @feedback commands from investigating officers."""

    def __init__(self, audit_ledger: Optional[ImmutableAuditLedger] = None):
        self.audit_ledger = audit_ledger or default_audit_ledger

    def process_feedback(
        self,
        feedback_text: str,
        nodes_dict: Dict[str, GraphNode],
        edges: List[GraphEdge],
        case_id: str = "DEFAULT",
        officer_badge: str = "INSP-4409"
    ) -> FeedbackResult:
        clean_text = feedback_text.strip()
        if not clean_text.lower().startswith("@feedback"):
            return FeedbackResult(
                status="ignored",
                action_type="NONE",
                target_id=None,
                message="Prompt is not a @feedback command."
            )

        instruction = clean_text[len("@feedback"):].strip()
        lower_inst = instruction.lower()

        # Find target node if an ID or label is mentioned
        target_node: Optional[GraphNode] = None
        for nid, node in nodes_dict.items():
            if nid.lower() in lower_inst or node.label.lower() in lower_inst:
                target_node = node
                break

        # 1. Action: Mark as Victim / Not a Suspect
        if any(w in lower_inst for w in ["not a suspect", "victim", "informant", "innocent", "complainant"]):
            if target_node:
                prev_state = {"type": target_node.type, "threat_level": target_node.threat_level, "score": target_node.threat_score}
                target_node.threat_level = "LOW"
                target_node.threat_score = 0.15
                target_node.metadata["investigator_note"] = "Human Ground Truth: Verified Victim/Informant"
                new_state = {"type": target_node.type, "threat_level": target_node.threat_level, "score": target_node.threat_score}

                entry = self.audit_ledger.record_action(
                    action="FEEDBACK_RECLASSIFY_VICTIM",
                    case_id=case_id,
                    officer_badge=officer_badge,
                    target_entity=target_node.id,
                    details={
                        "instruction": instruction,
                        "previous_state": prev_state,
                        "new_state": new_state,
                        "reason": "Investigator ground truth correction applied"
                    }
                )

                return FeedbackResult(
                    status="applied",
                    action_type="RECLASSIFY_VICTIM",
                    target_id=target_node.id,
                    message=f"Entity {target_node.label} reclassified as low-threat victim/informant based on human ground truth.",
                    audit_id=entry.audit_id,
                    updated_node=target_node.to_dict()
                )

        # 2. Action: Elevate Threat to Critical / Ringleader
        elif any(w in lower_inst for w in ["critical", "ringleader", "kingpin", "mastermind", "prime suspect"]):
            if target_node:
                prev_state = {"threat_level": target_node.threat_level, "score": target_node.threat_score}
                target_node.threat_level = "CRITICAL"
                target_node.threat_score = 0.98
                target_node.metadata["investigator_note"] = "Human Ground Truth: Confirmed Primary Ringleader"
                new_state = {"threat_level": target_node.threat_level, "score": target_node.threat_score}

                entry = self.audit_ledger.record_action(
                    action="FEEDBACK_ELEVATE_THREAT",
                    case_id=case_id,
                    officer_badge=officer_badge,
                    target_entity=target_node.id,
                    details={
                        "instruction": instruction,
                        "previous_state": prev_state,
                        "new_state": new_state
                    }
                )

                return FeedbackResult(
                    status="applied",
                    action_type="ELEVATE_THREAT",
                    target_id=target_node.id,
                    message=f"Threat level for {target_node.label} elevated to CRITICAL. Action logged to audit trail.",
                    audit_id=entry.audit_id,
                    updated_node=target_node.to_dict()
                )

        # 3. Action: Remove Edge / Relationship
        elif any(w in lower_inst for w in ["remove link", "remove edge", "delete connection", "no relation"]):
            # Remove matching edges if target node is found
            if target_node:
                removed_edges = [e for e in edges if e.source == target_node.id or e.target == target_node.id]
                for re_edge in removed_edges:
                    edges.remove(re_edge)

                entry = self.audit_ledger.record_action(
                    action="FEEDBACK_DISCONNECT_EDGES",
                    case_id=case_id,
                    officer_badge=officer_badge,
                    target_entity=target_node.id,
                    details={"removed_count": len(removed_edges), "instruction": instruction}
                )

                return FeedbackResult(
                    status="applied",
                    action_type="REMOVE_EDGES",
                    target_id=target_node.id,
                    message=f"Removed {len(removed_edges)} unverified edge(s) for {target_node.label}.",
                    audit_id=entry.audit_id
                )

        # Fallback / Generic note recording
        entry = self.audit_ledger.record_action(
            action="FEEDBACK_INVESTIGATOR_NOTE",
            case_id=case_id,
            officer_badge=officer_badge,
            target_entity=target_node.id if target_node else None,
            details={"instruction": instruction}
        )

        return FeedbackResult(
            status="applied",
            action_type="RECORD_NOTE",
            target_id=target_node.id if target_node else None,
            message="Investigator feedback noted and permanently recorded in immutable audit log.",
            audit_id=entry.audit_id
        )


# Global default instance
default_feedback_agent = FeedbackAgent()
