"""
Formulation Classifier
Main entry point for formulation classification using decision tree + LLM slot-filling
Implements ADR-002: Deterministic decision tree with LLM-driven slot filling
"""

from typing import Dict, Any, Optional
import logging

from .decision_tree import decision_tree, ClassificationState, FormulationClass
from .slot_filler import slot_filler
from ..security.input_guard import input_guard

logger = logging.getLogger(__name__)

class FormulationClassifier:
    """
    Main formulation classifier
    Per ADR-002: Uses deterministic decision tree with LLM slot-filling
    """
    
    def __init__(self):
        self.decision_tree = decision_tree
        self.slot_filler = slot_filler
        self.input_guard = input_guard
    
    async def classify(self, user_input: str, session_context: Dict[str, Any], existing_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classify a formulation description
        Supports multi-turn classification with session state
        
        Args:
            user_input: Current user message
            session_context: Session context (jurisdiction, etc.)
            existing_state: Previous classification state to resume from (for multi-turn)
        
        Returns classification result with formulation class or clarifying question
        """
        # Sanitize input first
        sanitization_result = self.input_guard.sanitize_input(user_input, context="classifier")
        
        if sanitization_result.is_suspicious:
            logger.warning(f"Suspicious input detected: {sanitization_result.flags}")
            return {
                "formulation_class": None,
                "status": "suspicious_input",
                "flags": sanitization_result.flags,
                "requires_escalation": True
            }
        
        # Resume from existing state or start fresh
        if existing_state:
            current_state = ClassificationState(
                current_step=existing_state.get("current_step", "start"),
                collected_slots=existing_state.get("collected_slots", {}),
                is_complete=False
            )
            logger.info(f"Resuming classification from step: {current_state.current_step}")
        else:
            current_state = ClassificationState(
                current_step="start",
                collected_slots={},
                is_complete=False
            )
            logger.info("Starting fresh classification")
        
        # Single iteration per call (multi-turn)
        # Get next question from decision tree
        question = self.decision_tree.get_next_question(current_state.current_step)
        
        if question is None:
            # Decision tree reached a terminal state
            current_state = self.decision_tree.classify(current_state.collected_slots)
            
            if current_state.is_complete:
                if current_state.formulation_class:
                    return {
                        "formulation_class": current_state.formulation_class.value,
                        "status": "classified",
                        "collected_slots": current_state.collected_slots,
                        "requires_escalation": False
                    }
                else:
                    # Escalation case
                    return {
                        "formulation_class": None,
                        "status": "escalated",
                        "escalation_reason": getattr(current_state, "escalation_reason", "Unknown"),
                        "collected_slots": current_state.collected_slots,
                        "requires_escalation": True
                    }
            else:
                # Incomplete but no more questions
                return {
                    "formulation_class": None,
                    "status": "incomplete",
                    "current_step": current_state.current_step,
                    "collected_slots": current_state.collected_slots,
                    "requires_escalation": True
                }
        
        # Try to extract slot from current user_input
        node = self.decision_tree.decision_tree[current_state.current_step]
        slot_name = node["slot_name"]
        options = node.get("options")
        
        if options:
            option_list = list(options.keys())
        else:
            option_list = None
        
        slot_value = await self.slot_filler.extract_slot(
            sanitization_result.sanitized_input,
            question,
            slot_name,
            option_list
        )
        
        if slot_value is not None:
            # Slot was explicitly stated - add to collected slots and continue
            current_state.collected_slots[slot_name] = slot_value
            current_state = self.decision_tree.classify(current_state.collected_slots)
            
            # Check if classification is now complete
            if current_state.is_complete:
                if current_state.formulation_class:
                    return {
                        "formulation_class": current_state.formulation_class.value,
                        "status": "classified",
                        "collected_slots": current_state.collected_slots,
                        "requires_escalation": False
                    }
                else:
                    return {
                        "formulation_class": None,
                        "status": "escalated",
                        "escalation_reason": getattr(current_state, "escalation_reason", "Unknown"),
                        "collected_slots": current_state.collected_slots,
                        "requires_escalation": True
                    }
            else:
                # Need more information - get next question
                next_question = self.decision_tree.get_next_question(current_state.current_step)
                return {
                    "formulation_class": None,
                    "status": "needs_clarification",
                    "current_step": current_state.current_step,
                    "clarifying_question": next_question,
                    "collected_slots": current_state.collected_slots,
                    "requires_escalation": False
                }
        else:
            # Slot not explicitly stated - ask user
            return {
                "formulation_class": None,
                "status": "needs_clarification",
                "current_step": current_state.current_step,
                "clarifying_question": question,
                "collected_slots": current_state.collected_slots,
                "requires_escalation": False
            }
    
    def ask_clarifying_question(self, current_state: Dict[str, Any]) -> Optional[str]:
        """
        Ask a clarifying question based on current classification state
        """
        current_step = current_state.get("current_step", "start")
        return self.decision_tree.get_next_question(current_step)
    
    def is_complete(self, current_state: Dict[str, Any]) -> bool:
        """
        Check if classification is complete
        """
        return current_state.get("status") in ["classified", "escalated"]

# Global formulation classifier instance
formulation_classifier = FormulationClassifier()
