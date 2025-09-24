import logging
from typing import Dict, Any, List, Optional

from langchain_core.language_models import BaseLanguageModel
from agent.types import Answer
from configs.load import setup_root_logger, get_default_llm

# Ensure logger exists
_logger = setup_root_logger()


def run_graph(query: str, time_hint: str | None, lang: str | None, trace_id: str, 
             session_id: str | None = None, llm: Optional[BaseLanguageModel] = None) -> Dict[str, Any]:
    class _TraceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            setattr(record, "trace_id", trace_id)
            return True

    tf = _TraceFilter()
    _logger.addFilter(tf)
    try:
        _logger.info("graph_start", extra={"trace_id": trace_id, "query": query, "time_hint": time_hint, "lang": lang, "session_id": session_id})

        # Lazy imports to keep module import time low
        from agent.nodes.listener import listen
        from agent.nodes.context_enhancer import enhance_with_context
        from agent.nodes.planner import plan
        from agent.nodes.candidate_search_chroma import first_pass_search as candidate_search # Use Chroma-based search
        from agent.nodes.facet_discovery import discover_facets
        from agent.nodes.facet_planner import pick_facet_branches
        from agent.nodes.narrowed_search import run_branches
        from agent.nodes.rerank_diversify import rerank_and_diversify
        from agent.nodes.validator import validate
        from agent.nodes.answerer import compose_answer
        from agent.nodes.observer import record_observation, notify_observers
        from agent.nodes.memory_updater import update_memory

        # Use session_id from trace_id if not provided
        if not session_id:
            session_id = trace_id
        
        # Notify observer that listener is starting
        notify_observers("listener", "in_progress", {"query": query})
        normalized = listen(query=query)
        _logger.info("listener_complete", extra={"trace_id": trace_id, "normalized": normalized})
        notify_observers("listener", "completed", {"normalized": normalized})
        
        # Enhance query with conversation context if session_id is provided
        notify_observers("context_enhancer", "in_progress", {"query": normalized, "session_id": session_id})
        context = enhance_with_context(query=normalized, session_id=session_id)
        enhanced_query = context["enhanced_query"]
        _logger.info("context_enhancer_complete", extra={"trace_id": trace_id, "has_context": context["has_context"]})
        notify_observers("context_enhancer", "completed", {"has_context": context["has_context"]})
        
        # Notify observer that planner is starting
        notify_observers("planner", "in_progress", {"query": enhanced_query})
        plan_out = plan(enhanced_query, lang=lang, time_hint=time_hint, llm=llm)
        _logger.info("planner_complete", extra={"trace_id": trace_id, "plan": plan_out})
        notify_observers("planner", "completed", plan_out)
        
        # Check if this is a non-search query that should be handled directly
        intent = plan_out.get("intent", "information_request")
        if intent in ["greeting", "conversation", "small_talk"]:
            # Handle non-search queries directly
            _logger.info("handling_non_search_query", extra={"trace_id": trace_id, "intent": intent})
            
            # Generate appropriate response without searching
            if intent == "greeting":
                response_text = "안녕하세요! 회의록 검색 시스템에 오신 것을 환영합니다. 어떤 회의록을 찾고 계신가요?"
            else:
                response_text = "무엇을 도와드릴까요?"
            
            answer = {
                "text": response_text,
                "citations": [],
                "has_context": False
            }
            
            # Store the assistant's response in conversation memory
            from memory.conversation_memory import conversation_memory
            conversation_memory.add_assistant_message(
                session_id=session_id,
                message=answer.get("text", ""),
                citations=answer.get("citations", [])
            )
            
            return {
                "text": answer.get("text", ""), 
                "citations": answer.get("citations", []),
                "session_id": session_id,
                "has_context": answer.get("has_context", False),
                "trace_id": trace_id,
                "intent": intent
            }
        
        # Notify observer that candidate search is starting
        notify_observers("candidate_search", "in_progress", {"query": enhanced_query, "alpha": plan_out.get("alpha", 0.5)})
        cands = candidate_search(query=enhanced_query, alpha=plan_out.get("alpha", 0.5)) # Call the synchronous function
        _logger.info("candidate_search_complete", extra={"trace_id": trace_id, "candidates_count": len(cands)})
        notify_observers("candidate_search", "completed", {"count": len(cands), "first": cands[0].get("chunk_id", "No ID") if cands and isinstance(cands[0], dict) else "None"})
        print(f"DEBUG: Candidate search returned {len(cands)} results")
        if cands:
            print(f"DEBUG: First candidate: {cands[0].get('chunk_id', 'No ID') if isinstance(cands[0], dict) else 'Not dict'}")
        
        # Notify observer that facet discovery is starting
        notify_observers("facet_discovery", "in_progress", {"candidates_count": len(cands)})
        facet_stats = discover_facets(cands)
        _logger.info("facet_discovery_complete", extra={"trace_id": trace_id, "facet_stats": facet_stats})
        notify_observers("facet_discovery", "completed", facet_stats)
        
        # Notify observer that facet planner is starting
        notify_observers("facet_planner", "in_progress", {"plan": plan_out, "facet_stats": facet_stats})
        branches = pick_facet_branches(plan_out, facet_stats, query=enhanced_query)  # Call the synchronous function
        _logger.info("facet_planner_complete", extra={"trace_id": trace_id, "branches": branches})
        notify_observers("facet_planner", "completed", {"branches": branches})
        
        # Notify observer that narrowed search is starting
        notify_observers("narrowed_search", "in_progress", {"branches": branches})
        narrowed = run_branches(query=enhanced_query, branches=branches)
        _logger.info("narrowed_search_complete", extra={"trace_id": trace_id, "narrowed_count": len(narrowed)})
        notify_observers("narrowed_search", "completed", {"count": len(narrowed)})
        
        # Notify observer that reranking is starting
        notify_observers("rerank_diversify", "in_progress", {"candidates_count": len(narrowed)})
        reranked, boosted_count = rerank_and_diversify(query=enhanced_query, candidates=narrowed, plan=plan_out)
        _logger.info("rerank_complete", extra={"trace_id": trace_id, "reranked_count": len(reranked), "boosted_count": boosted_count})
        notify_observers("rerank_diversify", "completed", {"count": len(reranked), "boosted_count": boosted_count})
        print(f"DEBUG: Reranked results: {len(reranked)}")
        
        # Notify observer that validator is starting
        notify_observers("validator", "in_progress", {"query": enhanced_query, "results_count": len(reranked)})
        verdict = validate(query=enhanced_query, top=reranked, llm=llm)
        _logger.info("validator_complete", extra={"trace_id": trace_id, "verdict": verdict})
        notify_observers("validator", "completed", verdict)
        
        # Debug: Print verdict details
        print(f"DEBUG: Verdict type: {type(verdict)}")
        print(f"DEBUG: Verdict content: {verdict}")
        print(f"DEBUG: Verdict keys: {verdict.keys() if isinstance(verdict, dict) else 'Not a dict'}")
        print(f"DEBUG: verdict.get('valid'): {verdict.get('valid')}")
        print(f"DEBUG: verdict.get('valid') is True: {verdict.get('valid') is True}")

        if verdict.get("valid") is True:
            # Notify observer that answerer is starting
            notify_observers("answerer", "in_progress", {"query": enhanced_query, "results_count": len(reranked)})
            answer: Answer = compose_answer(query=enhanced_query, top=reranked, llm=llm)
            record_observation(trace_id=trace_id, plan=plan_out, counts={"stage1": len(cands), "final": len(reranked)})
            notify_observers("answerer", "completed", {"text": answer.get("text", ""), "citations_count": len(answer.get("citations", []))})
            
            # Store the assistant's response in conversation memory
            from memory.conversation_memory import conversation_memory
            conversation_memory.add_assistant_message(
                session_id=session_id,
                message=answer.get("text", ""),
                citations=answer.get("citations", [])
            )
            
            # Notify observer that memory updater is starting
            notify_observers("memory_updater", "in_progress", {"answer_length": len(answer.get("text", "")), "top_count": len(reranked)})
            memory_result = update_memory(answer=answer, top=reranked, verdict=verdict)
            notify_observers("memory_updater", "completed", memory_result)
            
            return {
                "text": answer.get("text", ""), 
                "citations": answer.get("citations", []),
                "session_id": session_id,
                "has_context": context["has_context"]
            }
        elif verdict.get("action") == "GREET":
            # Handle greeting queries
            greeting_response = "Hello! How can I help you today?"
            
            # Store the assistant's response in conversation memory
            from memory.conversation_memory import conversation_memory
            conversation_memory.add_assistant_message(
                session_id=session_id,
                message=greeting_response,
                citations=[]
            )
            
            # Notify observer that answerer is skipped
            notify_observers("answerer", "completed", {"text": greeting_response, "citations_count": 0, "skipped": False})
            # Notify observer that memory updater is skipped
            notify_observers("memory_updater", "completed", {"updated": False, "skipped": True})
            
            return {
                "text": greeting_response, 
                "citations": [],
                "session_id": session_id,
                "has_context": context["has_context"]
            }
        else:
            # Transparent placeholder response to avoid confusion
            reason = verdict.get("reason", "Unknown validation failure")
            msg = f"I couldn't find relevant information for your query. {reason}"
            
            # Store the assistant's response in conversation memory
            from memory.conversation_memory import conversation_memory
            conversation_memory.add_assistant_message(
                session_id=session_id,
                message=msg,
                citations=[]
            )
            
            # Notify observer that answerer is skipped
            notify_observers("answerer", "completed", {"text": msg, "citations_count": 0, "skipped": True})
            # Notify observer that memory updater is skipped
            notify_observers("memory_updater", "completed", {"updated": False, "skipped": True})
            
            return {
                "text": msg, 
                "citations": [],
                "session_id": session_id,
                "has_context": context["has_context"]
            }
    except Exception as exc:
        _logger.exception("graph_error", extra={"trace_id": trace_id, "error": str(exc)})
        return {"text": f"[ERROR] {exc}", "citations": []}
    finally:
        _logger.removeFilter(tf)