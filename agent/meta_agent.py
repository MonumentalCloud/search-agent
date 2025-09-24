"""
Meta Agent - Dynamically generates custom workflows based on query analysis
"""
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel

from configs.load import get_default_llm

logger = logging.getLogger(__name__)


class MetaAgent:
    """Meta agent that analyzes queries and generates dynamic workflows"""
    
    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.llm = llm or get_default_llm()
    
    def analyze_query_complexity(self, query: str, conversation_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze query to determine complexity and required workflow components.
        
        Args:
            query: The user's query
            conversation_context: Advanced conversation context from ConversationMemory
            
        Returns:
            Dict with workflow configuration including:
            - workflow_type: "simple_search" | "complex_filtering" | "computation_required" | "monitoring_workflow"
            - required_components: List of components needed
            - python_code: Optional Python code for complex computations
            - workflow_steps: List of workflow steps to execute
            - workflow_schema: Visual representation of the workflow
            - agent_summary: Brief description of the generated agent structure
            - context_awareness: Information about how context influenced the analysis
        """
        # Build context-aware prompt
        context_info = ""
        context_awareness = {
            "has_context": False,
            "is_follow_up": False,
            "entity_references": [],
            "intent_continuity": False,
            "conversation_topic": None
        }
        
        if conversation_context:
            context_awareness["has_context"] = True
            context_analysis = conversation_context.get("context_analysis", {})
            conversation_history = conversation_context.get("conversation_history", [])
            
            # Update context awareness with intelligent analysis
            context_awareness.update({
                "is_follow_up": context_analysis.get("is_follow_up", False),
                "conversation_topic": context_analysis.get("conversation_topic"),
                "context_relevance": context_analysis.get("context_relevance", "low"),
                "suggested_workflow_type": context_analysis.get("suggested_workflow_type", "simple_search")
            })
            
            # Build context information for the prompt using intelligent analysis
            context_info = f"""
            
            CONVERSATION CONTEXT:
            - Is this a follow-up query? {context_analysis.get("is_follow_up", False)}
            - Current conversation topic: {context_analysis.get("conversation_topic", 'None')}
            - Context relevance: {context_analysis.get("context_relevance", 'low')}
            - Suggested workflow type: {context_analysis.get("suggested_workflow_type", 'simple_search')}
            - Relevant entities: {', '.join(context_analysis.get("relevant_entities", [])[:5])}
            - Query intent: {context_analysis.get("query_intent", 'unknown')}
            
            CONTEXT SUMMARY:
            {context_analysis.get("context_summary", "No context summary available.")}
            
            CONTEXT ANALYSIS REASONING:
            {context_analysis.get("reasoning", "No reasoning provided.")}
            
            IMPORTANT CONTEXT CONSIDERATIONS:
            - If this is a follow-up query, consider the previous conversation context when determining workflow complexity
            - If context relevance is high, the workflow should leverage previous conversation insights
            - If there's a suggested workflow type, consider it as a strong hint for the appropriate workflow
            - Consider whether this query is asking for clarification, more details, or building on previous information"""

        prompt = f"""You are a meta agent that analyzes search queries and determines the optimal workflow.

Query: "{query}"{context_info}

Analyze this query and determine:
1. Is this a simple search or does it require complex filtering/computation?
2. What specific processing steps are needed?
3. Does it need Python runtime for computations (date parsing, calculations, etc.)?
4. How does the conversation context influence the workflow choice?

Return ONLY valid JSON (no markdown, no newlines in string values):
{{
    "workflow_type": "simple_search|complex_filtering|computation_required|monitoring_workflow",
    "complexity_score": 1-10,
    "required_components": ["semantic_search", "date_parsing", "day_of_week_filtering", "aggregation"],
    "python_code": "Optional Python code for complex computations (use \\n for newlines). The data will have fields: meeting_date, doc_id, attendees, body, metadata.",
    "workflow_steps": [
        {{"step": "semantic_search", "description": "Get all meeting documents"}},
        {{"step": "extract_dates", "description": "Extract all dates from results"}},
        {{"step": "filter_tuesdays", "description": "Filter for Tuesday meetings"}},
        {{"step": "format_results", "description": "Format and return results"}}
    ],
    "workflow_schema": "Visual representation of workflow connections (single line)",
    "agent_summary": "Brief description of the generated agent structure and its purpose",
    "reasoning": "Why this workflow is needed and how context influenced the decision",
    "context_influence": "How conversation context affected the workflow choice"
}}

Examples:
- "안녕" -> simple_search, no computation needed
- "2025년 8월 11일 회의록" -> simple_search, basic date filtering  
- "화요일에 열린 모든 회의" -> complex_filtering, soft filtering can handle day-of-week matching
- "tuesday meetings" -> complex_filtering, soft filtering can handle day-of-week matching
- "meetings on tuesday" -> complex_filtering, soft filtering can handle day-of-week matching
- "tell me more about that meeting" -> complex_filtering, context-aware follow-up query
- "what about the attendees?" -> simple_search, follow-up about previously discussed meeting
- "지난 달에 열린 회의 중 참석자가 5명 이상인 것" -> computation_required, needs complex aggregation logic
- "monitor the search quality and adapt if needed" -> monitoring_workflow, needs continuous quality assessment
- "ensure the results are comprehensive and accurate" -> monitoring_workflow, needs validation and self-correction

            IMPORTANT: 
            - For simple day-of-week queries (like "tuesday meetings"), use workflow_type: "complex_filtering" - the soft filtering system can handle this
            - Only use workflow_type: "computation_required" for complex calculations that need custom Python code
            - Use workflow_type: "monitoring_workflow" when the user explicitly requests quality monitoring, validation, or adaptive behavior
            - For follow-up queries with high context relevance, strongly consider the suggested_workflow_type from context analysis
            - If context_analysis suggests a workflow type, it's usually correct - use it unless there's a strong reason not to
            - For clarification queries ("what does that mean?", "explain that"), use simple_search or complex_filtering based on context
            - The data structure has fields: meeting_date, doc_id, attendees, body, metadata
            - Use meeting_date field for date operations, not 'date'
            - Always handle empty or invalid dates gracefully (check if meeting_date exists and is not empty)
            - Return the original meeting data structure, don't modify the fields"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # Remove any control characters that might cause JSON parsing issues
            import re
            content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content.strip())
            
            # Try to find JSON object boundaries
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
                result = json.loads(json_content)
                
                # Add context awareness information
                result["context_awareness"] = context_awareness
                
                logger.info(f"Meta agent analysis: {result}")
                return result
            else:
                raise ValueError("No valid JSON found in response")
            
        except Exception as e:
            logger.error(f"Meta agent analysis failed: {e}")
            # No fallback - let it fail clearly
            raise Exception(f"Meta agent analysis failed: {e}")
    
    def generate_python_code(self, query: str, workflow_config: Dict[str, Any]) -> str:
        """
        Generate Python code for complex computations based on the workflow.
        """
        if workflow_config.get("workflow_type") != "computation_required":
            return ""
        
        prompt = f"""
        Generate Python code to process search results for this query: "{query}"
        
        Workflow requirements: {workflow_config.get('required_components', [])}
        
        The code should:
        1. Take a list of search results (each with metadata including dates)
        2. Process them according to the query requirements
        3. Return filtered/processed results
        
        Available data structure for each result:
        - result['metadata']['meeting_date']: ISO date string
        - result['metadata']['attendees']: JSON string of attendee list
        - result['body']: Document content
        - result['doc_id']: Document ID
        
        Return only the Python function code, no explanations.
        Function signature: def process_results(results: List[Dict]) -> List[Dict]:
        """
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract code block if present
            if "```python" in content:
                content = content.split("```python")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Python code generation failed: {e}")
            return ""
    
    def _generate_fallback_schema(self) -> str:
        """Generate a fallback schema for simple search."""
        return """
Query → Listener → Context Enhancer → Planner → 
Candidate Search → Facet Discovery → Facet Planner → 
Narrowed Search → Rerank/Diversify → Validator → Answerer → Memory Updater
        """.strip()
    
    def generate_workflow_schema(self, workflow_config: Dict[str, Any]) -> str:
        """Generate a visual schema for the workflow."""
        workflow_type = workflow_config.get("workflow_type", "simple_search")
        workflow_steps = workflow_config.get("workflow_steps", [])
        
        if workflow_type == "simple_search":
            return self._generate_simple_search_schema()
        elif workflow_type == "complex_filtering":
            return self._generate_complex_filtering_schema(workflow_steps)
        elif workflow_type == "computation_required":
            return self._generate_computation_schema(workflow_steps)
        elif workflow_type == "monitoring_workflow":
            return self._generate_monitoring_schema(workflow_steps)
        else:
            return self._generate_fallback_schema()
    
    def _generate_simple_search_schema(self) -> str:
        """Generate schema for simple search workflow."""
        return """
Query → Meta Agent → Simple Search Pipeline
    ↓
Listener → Context Enhancer → Planner → 
Candidate Search → Facet Discovery → Facet Planner → 
Narrowed Search → Rerank/Diversify → Validator → Answerer
        """.strip()
    
    def _generate_complex_filtering_schema(self, steps: List[Dict]) -> str:
        """Generate schema for complex filtering workflow."""
        schema = "Query → Meta Agent → Complex Filtering Pipeline\n    ↓\n"
        
        for i, step in enumerate(steps):
            step_name = step.get("step", "unknown")
            if i == 0:
                schema += f"{step_name}"
            else:
                schema += f" → {step_name}"
        
        schema += " → Answerer"
        return schema
    
    def _generate_computation_schema(self, steps: List[Dict]) -> str:
        """Generate schema for computation-heavy workflow."""
        schema = "Query → Meta Agent → Computation Pipeline\n    ↓\n"
        
        for i, step in enumerate(steps):
            step_name = step.get("step", "unknown")
            if i == 0:
                schema += f"{step_name}"
            else:
                schema += f" → {step_name}"
        
        schema += "\n    ↓\nPython Runtime ← Generated Code"
        return schema
    
    def _generate_monitoring_schema(self, steps: List[Dict]) -> str:
        """Generate schema for monitoring workflow."""
        schema = "Query → Meta Agent → Monitoring Pipeline\n    ↓\n"
        
        for i, step in enumerate(steps):
            step_name = step.get("step", "unknown")
            if i == 0:
                schema += f"{step_name}"
            else:
                schema += f" → {step_name}"
        
        schema += "\n    ↓\nQuality Monitor → Self-Assessment → Adaptive Response"
        return schema


class PythonRuntime:
    """Python runtime for executing generated code safely"""
    
    def __init__(self):
        self.allowed_modules = [
            'datetime', 'json', 're', 'calendar', 'collections'
        ]
        self.global_env = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float,
                'list': list, 'dict': dict, 'enumerate': enumerate,
                'zip': zip, 'map': map, 'filter': filter
            }
        }
    
    def execute_code(self, code: str, results: List[Dict]) -> List[Dict]:
        """
        Safely execute Python code on search results.
        """
        if not code.strip():
            return results
        
        try:
            # Add allowed modules to environment
            for module_name in self.allowed_modules:
                try:
                    module = __import__(module_name)
                    self.global_env[module_name] = module
                except ImportError:
                    pass
            
            # Execute the code
            exec(code, self.global_env)
            
            # Call the process_results function
            if 'process_results' in self.global_env:
                processed_results = self.global_env['process_results'](results)
                logger.info(f"Python runtime processed {len(results)} -> {len(processed_results)} results")
                return processed_results
            else:
                logger.warning("process_results function not found in generated code")
                return results
                
        except Exception as e:
            logger.error(f"Python runtime execution failed: {e}")
            return results


def create_adaptive_workflow(query: str, meta_agent: MetaAgent) -> Dict[str, Any]:
    """
    Create an adaptive workflow based on query analysis.
    """
    # Analyze the query
    workflow_config = meta_agent.analyze_query_complexity(query)
    
    # Generate Python code if needed
    if workflow_config.get("workflow_type") == "computation_required":
        python_code = meta_agent.generate_python_code(query, workflow_config)
        workflow_config["python_code"] = python_code
    
    return workflow_config
