"""
Deterministic Decision Tree for Formulation Classification
Implements ADR-002: Classification logic lives in code, not LLM judgment
Categories: classical, proprietary, new drug, phytopharmaceutical, Ayurveda-Aahar, cosmetic
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class FormulationClass(Enum):
    """Formulation classification categories"""
    CLASSICAL = "classical"
    PROPRIETARY = "proprietary"
    NEW_DRUG = "new_drug"
    PHYTOPHARMACEUTICAL = "phytopharmaceutical"
    AYURVEDA_AAHAAR = "ayurveda_aahar"
    COSMETIC = "cosmetic"

class ClassificationState(BaseModel):
    """State during classification decision tree traversal"""
    current_step: str
    collected_slots: Dict[str, Any]
    is_complete: bool = False
    formulation_class: Optional[FormulationClass] = None
    escalation_reason: Optional[str] = None

class DecisionTreeClassifier:
    """
    Deterministic decision tree for formulation classification
    Per ADR-002: Classification logic is in code, not LLM judgment
    LLM only performs slot-filling (extracting answers to fixed questions)
    """
    
    def __init__(self):
        self.decision_tree = self._build_decision_tree()
    
    def _build_decision_tree(self) -> Dict[str, Any]:
        """
        Build the deterministic decision tree
        Each node represents a decision point with fixed questions
        """
        return {
            "start": {
                "question": "Is the formulation based on authoritative texts from the First Schedule of the Drugs and Cosmetics Act?",
                "slot_name": "first_schedule_source",
                "yes": "check_classical_authenticity",
                "no": "check_novelty"
            },
            "check_classical_authenticity": {
                "question": "Is the formulation exactly as described in the authoritative text without modifications?",
                "slot_name": "exact_text_match",
                "yes": "classical_determination",
                "no": "check_modification_extent"
            },
            "classical_determination": {
                "action": "classify",
                "class": FormulationClass.CLASSICAL
            },
            "check_modification_extent": {
                "question": "Are the modifications within traditional practice guidelines?",
                "slot_name": "traditional_modification",
                "yes": "classical_determination",
                "no": "check_licensing"
            },
            "check_licensing": {
                "question": "Is there a valid license for the proprietary medicine?",
                "slot_name": "valid_license",
                "yes": "proprietary_determination",
                "no": "check_unauthorized_use"
            },
            "proprietary_determination": {
                "action": "classify",
                "class": FormulationClass.PROPRIETARY
            },
            "check_unauthorized_use": {
                "question": "Is this being used for commercial purposes without authorization?",
                "slot_name": "commercial_unauthorized",
                "yes": "escalate_legal",
                "no": "check_research_use"
            },
            "escalate_legal": {
                "action": "escalate",
                "reason": "Potential unauthorized commercial use of classical formulation"
            },
            "check_research_use": {
                "question": "Is this for research or academic purposes?",
                "slot_name": "research_purpose",
                "yes": "research_determination",
                "no": "check_therapeutic_claim"
            },
            "research_determination": {
                "action": "classify",
                "class": FormulationClass.NEW_DRUG  # Research formulations often require new drug pathway
            },
            "check_novelty": {
                "question": "Is this a completely new formulation not found in any traditional text?",
                "slot_name": "completely_novel",
                "yes": "check_safety_evidence",
                "no": "check_partial_novelty"
            },
            "check_safety_evidence": {
                "question": "Is there comprehensive safety and efficacy evidence from clinical trials?",
                "slot_name": "clinical_evidence",
                "yes": "new_drug_determination",
                "no": "check_preclinical_evidence"
            },
            "new_drug_determination": {
                "action": "classify",
                "class": FormulationClass.NEW_DRUG
            },
            "check_preclinical_evidence": {
                "question": "Is there preclinical evidence supporting safety and efficacy?",
                "slot_name": "preclinical_evidence",
                "yes": "phytopharmaceutical_determination",
                "no": "escalate_insufficient_evidence"
            },
            "phytopharmaceutical_determination": {
                "action": "classify",
                "class": FormulationClass.PHYTOPHARMACEUTICAL
            },
            "escalate_insufficient_evidence": {
                "action": "escalate",
                "reason": "Insufficient evidence for classification"
            },
            "check_partial_novelty": {
                "question": "Is this a novel combination of classical ingredients?",
                "slot_name": "novel_combination",
                "yes": "check_licensing",  # Novel combinations may need proprietary pathway
                "no": "check_format"
            },
            "check_format": {
                "question": "What is the primary format of this product?",
                "slot_name": "product_format",
                "options": {
                    "food/nutraceutical": "check_health_claim",
                    "topical": "check_therapeutic_claim",
                    "oral": "check_therapeutic_claim"
                }
            },
            "check_health_claim": {
                "question": "Does the product make specific health claims?",
                "slot_name": "health_claims",
                "yes": "check_therapeutic_claim",
                "no": "ayurveda_aahar_determination"
            },
            "ayurveda_aahar_determination": {
                "action": "classify",
                "class": FormulationClass.AYURVEDA_AAHAAR
            },
            "check_therapeutic_claim": {
                "question": "Does the product make therapeutic claims?",
                "slot_name": "therapeutic_claims",
                "yes": "check_cosmetic_definition",
                "no": "cosmetic_determination"
            },
            "check_cosmetic_definition": {
                "question": "Is the product intended for cosmetic purposes only (cleansing, beautifying, promoting attractiveness)?",
                "slot_name": "cosmetic_purpose",
                "yes": "cosmetic_determination",
                "no": "check_therapeutic_intent"
            },
            "cosmetic_determination": {
                "action": "classify",
                "class": FormulationClass.COSMETIC
            },
            "check_therapeutic_intent": {
                "question": "Is the primary intent therapeutic treatment of disease or symptoms?",
                "slot_name": "therapeutic_intent",
                "yes": "check_safety_evidence",  # Back to new drug pathway
                "no": "escalate_ambiguous"
            },
            "escalate_ambiguous": {
                "action": "escalate",
                "reason": "Ambiguous classification requiring human review"
            }
        }
    
    def classify(self, filled_slots: Dict[str, Any]) -> ClassificationState:
        """
        Execute the decision tree with filled slots
        Returns the classification state
        """
        current_node = "start"
        state = ClassificationState(
            current_step=current_node,
            collected_slots=filled_slots
        )
        
        max_iterations = 50  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            node = self.decision_tree.get(current_node)
            if not node:
                logger.error(f"Decision tree node not found: {current_node}")
                state.formulation_class = None
                state.is_complete = True
                break
            
            iteration += 1
            
            # Update current_step to this node
            state.current_step = current_node
            
            if node.get("action") == "classify":
                state.formulation_class = node["class"]
                state.is_complete = True
                logger.info(f"Decision tree reached classification node: {current_node}, class={state.formulation_class}")
                break
            elif node.get("action") == "escalate":
                state.formulation_class = None
                state.is_complete = True
                state.escalation_reason = node.get("reason")
                logger.info(f"Decision tree reached escalation node: {current_node}, reason={state.escalation_reason}")
                break
            else:
                # Get the slot value and determine next node
                slot_name = node["slot_name"]
                slot_value = filled_slots.get(slot_name)
                
                if slot_value is None:
                    # Need to ask this question
                    break
                
                # Determine next node based on slot value
                if slot_value in [True, "yes", "Yes", "YES"]:
                    current_node = node.get("yes")
                elif slot_value in [False, "no", "No", "NO"]:
                    current_node = node.get("no")
                elif isinstance(node.get("options"), dict) and slot_value in node["options"]:
                    current_node = node["options"][slot_value]
                else:
                    # Unknown value, escalate
                    state.formulation_class = None
                    state.is_complete = True
                    state.escalation_reason = f"Unknown slot value: {slot_name}={slot_value}"
                    break
        
        return state
    
    def get_next_question(self, current_step: str) -> Optional[str]:
        """
        Get the next question to ask the user
        """
        node = self.decision_tree.get(current_step)
        if node and "question" in node:
            return node["question"]
        return None
    
    def is_complete(self, state: ClassificationState) -> bool:
        """
        Check if classification is complete
        """
        return state.is_complete

# Global decision tree instance
decision_tree = DecisionTreeClassifier()
