"""
Embedding Regression Gate
Per ADR-006: CI-enforced gate for embedding/reranker changes

This gate must pass in CI before any change to the embedding/reranking pipeline is merged.
The override flag exists for emergencies only and is itself audited.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RegressionTestResult:
    """Result of regression test"""
    test_name: str
    passed: bool
    baseline_metric: float
    candidate_metric: float
    delta: float
    tolerance: float
    details: Dict


@dataclass
class GateResult:
    """Overall gate result"""
    passed: bool
    override_used: bool
    override_reason: Optional[str]
    test_results: List[RegressionTestResult]
    summary: Dict


class EmbeddingRegressionGate:
    """
    Regression gate for embedding and reranker model changes
    
    Per ADR-006: Fails CI if accuracy regresses beyond defined tolerance
    Requires explicit override flag for emergency bypass (audited)
    
    Evaluation metrics:
    - Citation correctness rate (cited section actually supports answer)
    - Retrieval precision@k for statute sections
    - Near-miss retrieval rate (wrong but adjacent section - critical failure mode)
    """

    def __init__(
        self,
        baseline_path: Optional[str] = None,
        tolerance: float = 0.05,
        override_flag: Optional[str] = None
    ):
        """
        Initialize regression gate
        
        Args:
            baseline_path: Path to baseline metrics file
            tolerance: Maximum allowed regression (e.g., 0.05 = 5%)
            override_flag: Override flag for emergency bypass (audited)
        """
        self.baseline_path = baseline_path or os.getenv(
            "BASELINE_METRICS_PATH",
            "tests/eval/baseline_metrics.json"
        )
        self.tolerance = tolerance
        self.override_flag = override_flag or os.getenv("EMBEDDING_REGRESSION_OVERRIDE")
        
        logger.info(
            f"EmbeddingRegressionGate initialized: "
            f"baseline={self.baseline_path}, tolerance={tolerance}"
        )

    def load_baseline(self) -> Dict:
        """
        Load baseline metrics from file
        
        Returns:
            Baseline metrics dictionary
        """
        baseline_file = Path(self.baseline_path)
        
        if not baseline_file.exists():
            logger.error(f"Baseline file not found: {self.baseline_path}")
            raise FileNotFoundError(f"Baseline metrics file not found: {self.baseline_path}")
        
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)
        
        logger.info(f"Loaded baseline metrics from {self.baseline_path}")
        return baseline

    def evaluate_candidate(self, candidate_model: str, test_queries: List[Dict]) -> Dict:
        """
        Evaluate candidate model on test set
        
        Args:
            candidate_model: Candidate model identifier
            test_queries: List of test queries with expected results
            
        Returns:
            Candidate metrics dictionary
        """
        logger.info(f"Evaluating candidate model: {candidate_model}")
        
        # This would typically call the actual embedding/retrieval pipeline
        # For now, we simulate the evaluation
        # In production, this would:
        # 1. Generate embeddings with candidate model
        # 2. Retrieve results for each test query
        # 3. Evaluate citation correctness, precision@k, near-miss rate
        
        candidate_metrics = {
            'citation_correctness_rate': self._evaluate_citation_correctness(test_queries),
            'precision_at_5': self._evaluate_precision_at_k(test_queries, k=5),
            'precision_at_10': self._evaluate_precision_at_k(test_queries, k=10),
            'near_miss_rate': self._evaluate_near_miss_rate(test_queries),
            'mean_reciprocal_rank': self._evaluate_mrr(test_queries)
        }
        
        logger.info(f"Candidate metrics: {candidate_metrics}")
        return candidate_metrics

    def _evaluate_citation_correctness(self, test_queries: List[Dict]) -> float:
        """
        Evaluate citation correctness rate
        
        Args:
            test_queries: Test queries with expected citations
            
        Returns:
            Citation correctness rate (0-1)
        """
        # In production, this would:
        # 1. Generate answer with citations
        # 2. Check if cited section actually supports the answer
        # 3. Calculate correctness rate
        
        # Placeholder implementation
        correct = sum(1 for q in test_queries if q.get('citation_correct', False))
        total = len(test_queries)
        return correct / total if total > 0 else 0.0

    def _evaluate_precision_at_k(self, test_queries: List[Dict], k: int) -> float:
        """
        Evaluate precision@k for statute sections
        
        Args:
            test_queries: Test queries with expected results
            k: Number of results to consider
            
        Returns:
            Precision@k (0-1)
        """
        # In production, this would:
        # 1. Retrieve top-k results for each query
        # 2. Check how many are in the expected set
        # 3. Calculate precision
        
        # Placeholder implementation
        total_precision = 0.0
        for query in test_queries:
            relevant_retrieved = sum(
                1 for r in query.get('retrieved', [])[:k]
                if r.get('relevant', False)
            )
            total_precision += relevant_retrieved / k
        
        return total_precision / len(test_queries) if test_queries else 0.0

    def _evaluate_near_miss_rate(self, test_queries: List[Dict]) -> float:
        """
        Evaluate near-miss retrieval rate
        
        Near-miss: wrong but adjacent section (critical failure mode)
        
        Args:
            test_queries: Test queries with retrieved results
            
        Returns:
            Near-miss rate (0-1, lower is better)
        """
        # In production, this would:
        # 1. Check if retrieved sections are adjacent to correct section
        # 2. Count near-misses
        
        # Placeholder implementation
        near_misses = sum(1 for q in test_queries if q.get('near_miss', False))
        return near_misses / len(test_queries) if test_queries else 0.0

    def _evaluate_mrr(self, test_queries: List[Dict]) -> float:
        """
        Evaluate Mean Reciprocal Rank
        
        Args:
            test_queries: Test queries with ranked results
            
        Returns:
            MRR (0-1)
        """
        # In production, this would:
        # 1. Find rank of first relevant result
        # 2. Calculate reciprocal (1/rank)
        # 3. Average across all queries
        
        # Placeholder implementation
        reciprocal_ranks = []
        for query in test_queries:
            retrieved = query.get('retrieved', [])
            first_relevant_idx = next(
                (i for i, r in enumerate(retrieved) if r.get('relevant', False)),
                None
            )
            if first_relevant_idx is not None:
                reciprocal_ranks.append(1.0 / (first_relevant_idx + 1))
        
        return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

    def compare_metrics(
        self,
        baseline: Dict,
        candidate: Dict
    ) -> List[RegressionTestResult]:
        """
        Compare candidate metrics against baseline
        
        Args:
            baseline: Baseline metrics
            candidate: Candidate metrics
            
        Returns:
            List of regression test results
        """
        results = []
        
        metrics_to_check = [
            'citation_correctness_rate',
            'precision_at_5',
            'precision_at_10',
            'mean_reciprocal_rank'
        ]
        
        for metric in metrics_to_check:
            baseline_value = baseline.get(metric, 0.0)
            candidate_value = candidate.get(metric, 0.0)
            
            # Calculate delta (candidate - baseline)
            delta = candidate_value - baseline_value
            
            # Check if regression exceeds tolerance
            # Regression = candidate is worse than baseline
            passed = delta >= -self.tolerance
            
            result = RegressionTestResult(
                test_name=metric,
                passed=passed,
                baseline_metric=baseline_value,
                candidate_metric=candidate_value,
                delta=delta,
                tolerance=self.tolerance,
                details={
                    'regression': delta < 0,
                    'regression_amount': abs(delta) if delta < 0 else 0.0
                }
            )
            
            results.append(result)
        
        # For near-miss rate, we want it to NOT increase
        near_miss_baseline = baseline.get('near_miss_rate', 0.0)
        near_miss_candidate = candidate.get('near_miss_rate', 0.0)
        near_miss_delta = near_miss_candidate - near_miss_baseline
        
        near_miss_passed = near_miss_delta <= self.tolerance
        
        results.append(RegressionTestResult(
            test_name='near_miss_rate',
            passed=near_miss_passed,
            baseline_metric=near_miss_baseline,
            candidate_metric=near_miss_candidate,
            delta=near_miss_delta,
            tolerance=self.tolerance,
            details={
                'regression': near_miss_delta > 0,
                'regression_amount': near_miss_delta if near_miss_delta > 0 else 0.0
            }
        ))
        
        return results

    def run_gate(
        self,
        candidate_model: str,
        test_queries: List[Dict]
    ) -> GateResult:
        """
        Run the full regression gate
        
        Args:
            candidate_model: Candidate model identifier
            test_queries: Test queries with expected results
            
        Returns:
            Gate result with pass/fail decision
        """
        logger.info("Running embedding regression gate")
        
        # Load baseline
        baseline = self.load_baseline()
        
        # Evaluate candidate
        candidate = self.evaluate_candidate(candidate_model, test_queries)
        
        # Compare metrics
        test_results = self.compare_metrics(baseline, candidate)
        
        # Check if all tests passed
        all_passed = all(result.passed for result in test_results)
        
        # Check for override
        override_used = False
        override_reason = None
        
        if not all_passed and self.override_flag:
            logger.warning(
                f"REGRESSION DETECTED BUT OVERRIDE ACTIVE: {self.override_flag}"
            )
            override_used = True
            override_reason = self.override_flag
            all_passed = True  # Override passes the gate
        elif not all_passed:
            logger.error("REGRESSION DETECTED - GATE FAILED")
        
        # Summary
        summary = {
            'total_tests': len(test_results),
            'passed_tests': sum(1 for r in test_results if r.passed),
            'failed_tests': sum(1 for r in test_results if not r.passed),
            'baseline_model': baseline.get('model_name', 'unknown'),
            'candidate_model': candidate_model,
            'tolerance': self.tolerance
        }
        
        result = GateResult(
            passed=all_passed,
            override_used=override_used,
            override_reason=override_reason,
            test_results=test_results,
            summary=summary
        )
        
        logger.info(f"Gate result: passed={all_passed}, override={override_used}")
        return result

    def save_candidate_as_baseline(
        self,
        candidate_model: str,
        candidate_metrics: Dict
    ):
        """
        Save candidate metrics as new baseline (for approved model upgrades)
        
        Args:
            candidate_model: Candidate model identifier
            candidate_metrics: Candidate metrics to save
        """
        baseline_data = {
            'model_name': candidate_model,
            'metrics': candidate_metrics,
            'saved_at': str(Path(__file__).stat().st_mtime)
        }
        
        with open(self.baseline_path, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        logger.info(f"Saved new baseline: {candidate_model}")

    def generate_report(self, gate_result: GateResult) -> str:
        """
        Generate human-readable report
        
        Args:
            gate_result: Gate result
            
        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "EMBEDDING REGRESSION GATE REPORT",
            "=" * 60,
            "",
            f"Overall Result: {'PASSED' if gate_result.passed else 'FAILED'}",
            f"Override Used: {'YES' if gate_result.override_used else 'NO'}",
            f"Override Reason: {gate_result.override_reason or 'N/A'}",
            "",
            "-" * 60,
            "SUMMARY",
            "-" * 60,
            f"Total Tests: {gate_result.summary['total_tests']}",
            f"Passed: {gate_result.summary['passed_tests']}",
            f"Failed: {gate_result.summary['failed_tests']}",
            f"Baseline Model: {gate_result.summary['baseline_model']}",
            f"Candidate Model: {gate_result.summary['candidate_model']}",
            f"Tolerance: {gate_result.summary['tolerance']}",
            "",
            "-" * 60,
            "TEST RESULTS",
            "-" * 60,
        ]
        
        for result in gate_result.test_results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"\n{result.test_name}: {status}")
            lines.append(f"  Baseline: {result.baseline_metric:.4f}")
            lines.append(f"  Candidate: {result.candidate_metric:.4f}")
            lines.append(f"  Delta: {result.delta:+.4f}")
            lines.append(f"  Tolerance: {result.tolerance:.4f}")
            
            if result.details.get('regression'):
                lines.append(f"  REGRESSION: {result.details['regression_amount']:.4f}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


def main():
    """Main entry point for running the gate"""
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Parse arguments
    candidate_model = sys.argv[1] if len(sys.argv) > 1 else "candidate_model"
    test_data_path = sys.argv[2] if len(sys.argv) > 2 else "tests/eval/test_queries.json"
    
    # Load test data
    try:
        with open(test_data_path, 'r') as f:
            test_queries = json.load(f)
    except FileNotFoundError:
        logger.error(f"Test data file not found: {test_data_path}")
        sys.exit(1)
    
    # Run gate
    gate = EmbeddingRegressionGate()
    result = gate.run_gate(candidate_model, test_queries)
    
    # Print report
    print(gate.generate_report(result))
    
    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
