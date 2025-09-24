"""
Quality Monitor - Monitors and assesses the quality of search results and answers
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from agent.types import Answer
from configs.load import get_default_llm
from langchain_core.language_models import BaseLanguageModel

logger = logging.getLogger(__name__)

class QualityMonitor:
    """Monitors and assesses the quality of search results and answers"""
    
    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.llm = llm or get_default_llm()
    
    def assess_search_quality(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess the quality of search results.
        
        Args:
            query: The original user query
            search_results: List of search results to assess
            
        Returns:
            Dictionary with quality assessment metrics
        """
        if not search_results:
            return {
                "quality_score": 0.0,
                "coverage_score": 0.0,
                "relevance_score": 0.0,
                "diversity_score": 0.0,
                "issues": ["No search results found"],
                "recommendations": ["Expand search parameters", "Try different query terms"],
                "confidence": 0.0
            }
        
        # Calculate basic metrics
        total_results = len(search_results)
        results_with_metadata = sum(1 for r in search_results if r.get('metadata', {}))
        results_with_dates = sum(1 for r in search_results if r.get('metadata', {}).get('meeting_date'))
        
        # Calculate coverage score (how many results have useful metadata)
        coverage_score = results_with_metadata / total_results if total_results > 0 else 0
        
        # Calculate diversity score (how many unique documents/sources)
        unique_docs = len(set(r.get('doc_id', '') for r in search_results if r.get('doc_id')))
        diversity_score = unique_docs / min(total_results, 10)  # Normalize to max 10 unique docs
        
        # Use LLM to assess relevance
        relevance_score = self._assess_relevance_with_llm(query, search_results)
        
        # Calculate overall quality score
        quality_score = (coverage_score * 0.3 + relevance_score * 0.5 + diversity_score * 0.2)
        
        # Identify issues and generate recommendations
        issues = []
        recommendations = []
        
        if coverage_score < 0.5:
            issues.append("Low metadata coverage in search results")
            recommendations.append("Improve metadata extraction during ingestion")
        
        if diversity_score < 0.3:
            issues.append("Limited document diversity in results")
            recommendations.append("Expand search to include more document sources")
        
        if relevance_score < 0.6:
            issues.append("Search results may not be highly relevant to query")
            recommendations.append("Refine search query or adjust search parameters")
        
        if total_results < 5:
            issues.append("Limited number of search results")
            recommendations.append("Increase search result limit or broaden search criteria")
        
        return {
            "quality_score": quality_score,
            "coverage_score": coverage_score,
            "relevance_score": relevance_score,
            "diversity_score": diversity_score,
            "total_results": total_results,
            "results_with_metadata": results_with_metadata,
            "results_with_dates": results_with_dates,
            "unique_documents": unique_docs,
            "issues": issues,
            "recommendations": recommendations,
            "confidence": quality_score,
            "assessment_timestamp": datetime.now().isoformat()
        }
    
    def assess_answer_quality(self, query: str, answer: Answer, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess the quality of the generated answer.
        
        Args:
            query: The original user query
            answer: The generated answer
            search_results: The search results used to generate the answer
            
        Returns:
            Dictionary with answer quality assessment
        """
        answer_text = answer.get("text", "")
        citations = answer.get("citations", [])
        
        if not answer_text:
            return {
                "quality_score": 0.0,
                "completeness_score": 0.0,
                "accuracy_score": 0.0,
                "citation_score": 0.0,
                "coherence_score": 0.0,
                "issues": ["No answer text generated"],
                "recommendations": ["Generate a response", "Check search results"],
                "confidence": 0.0
            }
        
        # Calculate citation score
        citation_score = len(citations) / min(len(search_results), 5) if search_results else 0
        
        # Use LLM to assess completeness and accuracy
        completeness_score = self._assess_completeness_with_llm(query, answer_text)
        accuracy_score = self._assess_accuracy_with_llm(query, answer_text, search_results)
        coherence_score = self._assess_coherence_with_llm(answer_text)
        
        # Calculate overall quality score
        quality_score = (completeness_score * 0.3 + accuracy_score * 0.3 + 
                        citation_score * 0.2 + coherence_score * 0.2)
        
        # Identify issues and generate recommendations
        issues = []
        recommendations = []
        
        if completeness_score < 0.6:
            issues.append("Answer may be incomplete")
            recommendations.append("Include more details from search results")
        
        if accuracy_score < 0.7:
            issues.append("Answer accuracy may be questionable")
            recommendations.append("Verify information against source documents")
        
        if citation_score < 0.3:
            issues.append("Limited citations provided")
            recommendations.append("Include more specific citations")
        
        if coherence_score < 0.6:
            issues.append("Answer may lack coherence")
            recommendations.append("Improve answer structure and flow")
        
        return {
            "quality_score": quality_score,
            "completeness_score": completeness_score,
            "accuracy_score": accuracy_score,
            "citation_score": citation_score,
            "coherence_score": coherence_score,
            "answer_length": len(answer_text),
            "citation_count": len(citations),
            "issues": issues,
            "recommendations": recommendations,
            "confidence": quality_score,
            "assessment_timestamp": datetime.now().isoformat()
        }
    
    def _assess_relevance_with_llm(self, query: str, search_results: List[Dict[str, Any]]) -> float:
        """Use LLM to assess relevance of search results."""
        try:
            # Sample a few results for assessment
            sample_results = search_results[:3]
            results_text = "\n".join([
                f"Result {i+1}: {r.get('body', '')[:200]}..." 
                for i, r in enumerate(sample_results)
            ])
            
            prompt = f"""
            Assess the relevance of these search results to the query: "{query}"
            
            Search Results:
            {results_text}
            
            Rate the relevance on a scale of 0.0 to 1.0, where:
            - 1.0 = Highly relevant and directly addresses the query
            - 0.5 = Moderately relevant with some useful information
            - 0.0 = Not relevant or unrelated to the query
            
            Return only a number between 0.0 and 1.0.
            """
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract number from response
            import re
            numbers = re.findall(r'0\.\d+|1\.0', content)
            if numbers:
                return float(numbers[0])
            else:
                return 0.5  # Default moderate relevance
                
        except Exception as e:
            logger.error(f"Error assessing relevance with LLM: {e}")
            return 0.5  # Default moderate relevance
    
    def _assess_completeness_with_llm(self, query: str, answer_text: str) -> float:
        """Use LLM to assess completeness of the answer."""
        try:
            prompt = f"""
            Assess how completely this answer addresses the query: "{query}"
            
            Answer: {answer_text[:500]}...
            
            Rate the completeness on a scale of 0.0 to 1.0, where:
            - 1.0 = Fully addresses all aspects of the query
            - 0.5 = Partially addresses the query
            - 0.0 = Does not address the query at all
            
            Return only a number between 0.0 and 1.0.
            """
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import re
            numbers = re.findall(r'0\.\d+|1\.0', content)
            if numbers:
                return float(numbers[0])
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error assessing completeness with LLM: {e}")
            return 0.5
    
    def _assess_accuracy_with_llm(self, query: str, answer_text: str, search_results: List[Dict[str, Any]]) -> float:
        """Use LLM to assess accuracy of the answer."""
        try:
            # Sample search results for context
            sample_results = search_results[:2]
            context_text = "\n".join([
                f"Source {i+1}: {r.get('body', '')[:200]}..." 
                for i, r in enumerate(sample_results)
            ])
            
            prompt = f"""
            Assess the accuracy of this answer based on the provided sources.
            
            Query: "{query}"
            Answer: {answer_text[:400]}...
            
            Sources:
            {context_text}
            
            Rate the accuracy on a scale of 0.0 to 1.0, where:
            - 1.0 = Highly accurate and well-supported by sources
            - 0.5 = Moderately accurate with some support
            - 0.0 = Inaccurate or not supported by sources
            
            Return only a number between 0.0 and 1.0.
            """
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import re
            numbers = re.findall(r'0\.\d+|1\.0', content)
            if numbers:
                return float(numbers[0])
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error assessing accuracy with LLM: {e}")
            return 0.5
    
    def _assess_coherence_with_llm(self, answer_text: str) -> float:
        """Use LLM to assess coherence of the answer."""
        try:
            prompt = f"""
            Assess the coherence and readability of this answer.
            
            Answer: {answer_text[:400]}...
            
            Rate the coherence on a scale of 0.0 to 1.0, where:
            - 1.0 = Very coherent, well-structured, and easy to read
            - 0.5 = Moderately coherent with some structure issues
            - 0.0 = Incoherent, poorly structured, or hard to read
            
            Return only a number between 0.0 and 1.0.
            """
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import re
            numbers = re.findall(r'0\.\d+|1\.0', content)
            if numbers:
                return float(numbers[0])
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error assessing coherence with LLM: {e}")
            return 0.5


def monitor_search_quality(query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Monitor the quality of search results."""
    monitor = QualityMonitor()
    return monitor.assess_search_quality(query, search_results)


def monitor_answer_quality(query: str, answer: Answer, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Monitor the quality of generated answers."""
    monitor = QualityMonitor()
    return monitor.assess_answer_quality(query, answer, search_results)
