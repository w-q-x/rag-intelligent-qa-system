import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from domain.customer_service.prompts import QUESTION_REWRITE_PROMPT, SYSTEM_PROMPT
from llm import chat_service
from services.rag_service import rag_service
from tools import search_faq_tool

load_dotenv()


class CustomerServiceAgent:
    """RAG agent based on Small-to-Big parent context retrieval."""

    def __init__(self):
        self.tool_descriptions = search_faq_tool.to_prompt_desc()
        self.system_prompt = SYSTEM_PROMPT.format(tool_descriptions=self.tool_descriptions)
        self.rewrite_enabled = os.getenv("AGENT_REWRITE_ENABLED", "true").lower() == "true"

    def _rewrite_question(self, original_question: str) -> str:
        if not self.rewrite_enabled:
            return original_question

        prompt = QUESTION_REWRITE_PROMPT.format(original_question=original_question)
        try:
            rewritten = chat_service.chat_completion([{"role": "user", "content": prompt}])
            return rewritten.strip() if rewritten else original_question
        except Exception:
            return original_question

    def _format_history(self, history: Optional[List[Dict[str, Any]]]) -> str:
        if not history:
            return "None"

        history_parts = []
        for msg in history[-6:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history_parts.append(f"User: {content}")
            elif role == "assistant":
                history_parts.append(f"Assistant: {content}")
        return "\n".join(history_parts) if history_parts else "None"

    def _build_context(self, big_chunks: List[Dict[str, Any]], small_chunks: List[Dict[str, Any]]) -> str:
        if big_chunks:
            context_parts = []
            for index, big_chunk in enumerate(big_chunks, 1):
                metadata = big_chunk.get("metadata", {})
                source_file = metadata.get("source_file", "unknown")
                page_number = metadata.get("page_number")
                page_text = f"\nPage: {page_number}" if page_number else ""
                context_parts.append(
                    f"[Reference document {index}]\n"
                    f"Source: {source_file}{page_text}\n"
                    f"Parent chunk id: {big_chunk.get('big_chunk_id', '')}\n"
                    f"{big_chunk.get('text', '')}"
                )
            return "\n\n".join(context_parts)

        if small_chunks:
            return "\n\n".join(
                f"[Matched child chunk {index}]\n"
                f"Source: {chunk.get('source', {}).get('file', 'unknown')}\n"
                f"{chunk.get('text', '')}"
                for index, chunk in enumerate(small_chunks, 1)
            )

        return "No relevant knowledge base context was found."

    def _collect_sources(self, small_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sources = []
        seen = set()
        for chunk in small_chunks:
            source = chunk.get("source")
            if not source:
                continue
            key = (source.get("file"), source.get("doc_id"), source.get("chunk_id"))
            if key in seen:
                continue
            seen.add(key)
            sources.append(source)
        return sources

    def run(self, question: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        rewritten_question = self._rewrite_question(question)

        big_chunks, small_chunks = rag_service.retrieve_parent_context(
            rewritten_question, use_hybrid=True
        )
        formatted_history = self._format_history(history)
        context = self._build_context(big_chunks, small_chunks)

        final_prompt = f"""You are an intelligent customer-service assistant.

System instruction:
{self.system_prompt}

Conversation history:
{formatted_history}

Knowledge base context:
{context}

Current user question:
{question}

Answer requirements:
1. Use the knowledge base context as the source of truth.
2. If the context does not contain enough relevant information, say that no reliable answer was found in the knowledge base.
3. Be concise, accurate, and polite.
4. Do not invent facts outside the retrieved context.
"""

        raw_reply = chat_service.chat_completion([{"role": "user", "content": final_prompt}])
        raw_reply = raw_reply.strip() if raw_reply else "No answer could be generated."

        # Parse the LLM structured output: ### thinking / ### action / ### reply
        import re as _re
        sections = {"reply": "", "thinking": "", "action": ""}
        current_section = None
        for line in raw_reply.splitlines():
            m = _re.match(r"^###\s*(thinking|action|reply)", line)
            if m:
                current_section = {"thinking": "thinking", "action": "action", "reply": "reply"}[m.group(1)]
                continue
            if current_section:
                sections[current_section] += line + "\n"

        reply = sections["reply"].strip() or raw_reply
        llm_thinking = sections["thinking"].strip()
        llm_action = sections["action"].strip()

        thinking_parts = []
        if rewritten_question != question:
            thinking_parts.append(f"Rewritten question: {rewritten_question}")
        thinking_parts.append(f"Retrieved child chunks: {len(small_chunks)}")
        thinking_parts.append(f"Retrieved parent chunks: {len(big_chunks)}")
        if llm_thinking:
            thinking_parts.append(f"LLM reasoning:\n{llm_thinking}")
        if llm_action:
            thinking_parts.append(f"LLM action: {llm_action}")

        return {
            "thinking": "\n".join(thinking_parts),
            "action": "small_to_big_retrieval",
            "reply": reply.strip() if reply else "No answer could be generated.",
            "sources": self._collect_sources(small_chunks),
            "rewritten_question": rewritten_question,
            "final_prompt": final_prompt,
            "small_chunks": small_chunks,
            "big_chunks": big_chunks,
        }

    def _build_context_with_citations(
        self, big_chunks, small_chunks
    ):
        sources = []
        context_parts = []
        if big_chunks:
            for index, big_chunk in enumerate(big_chunks, 1):
                metadata = big_chunk.get('metadata', {})
                source_file = metadata.get('source_file', 'unknown')
                page_number = metadata.get('page_number')
                page_text = f', Page {page_number}' if page_number else ''
                context_parts.append(
                    f'[Reference {index}]\n'
                    f'Source: {source_file}{page_text}\n'
                    f"{big_chunk.get('text', '')}"
                )
                sources.append({
                    'index': index,
                    'file': source_file,
                    'chunk_id': big_chunk.get('big_chunk_id', ''),
                    'page': page_number,
                })
        elif small_chunks:
            for index, chunk in enumerate(small_chunks, 1):
                source_info = chunk.get('source', {})
                source_file = source_info.get('file', 'unknown')
                context_parts.append(
                    f'[Reference {index}]\n'
                    f'Source: {source_file}\n'
                    f"{chunk.get('text', '')}"
                )
                sources.append({
                    'index': index,
                    'file': source_file,
                    'chunk_id': chunk.get('small_chunk_id', ''),
                    'page': source_info.get('page_number'),
                })
        context = '\n\n'.join(context_parts) if context_parts else 'No relevant context found.'
        return context, sources

    def _generate_title(self, question, reply):
        from domain.customer_service.prompts import TITLE_GENERATION_PROMPT
        try:
            prompt = TITLE_GENERATION_PROMPT.format(question=question, reply=reply[:500])
            title = chat_service.chat_completion([{'role': 'user', 'content': prompt}])
            return title.strip()[:20] if title else question[:50]
        except Exception:
            return question[:50]

    def run_stream(self, question, history=None):
        from domain.customer_service.prompts import CITATION_FINAL_PROMPT_TEMPLATE, STREAM_SYSTEM_PROMPT
        rewritten_question = self._rewrite_question(question)
        big_chunks, small_chunks = rag_service.retrieve_parent_context(rewritten_question, use_hybrid=True)
        yield {'event': 'thinking', 'data': {'text': f'Retrieved {len(small_chunks)} child chunks and {len(big_chunks)} parent chunks.', 'rewritten_question': rewritten_question if rewritten_question != question else None}}
        formatted_history = self._format_history(history)
        context, sources = self._build_context_with_citations(big_chunks, small_chunks)
        yield {'event': 'sources', 'data': {'sources': sources}}
        final_prompt = CITATION_FINAL_PROMPT_TEMPLATE.format(system_prompt=STREAM_SYSTEM_PROMPT, history=formatted_history, context=context, question=question)
        full_reply = []
        try:
            for token in chat_service.chat_completion_stream([{'role': 'user', 'content': final_prompt}]):
                full_reply.append(token)
                yield {'event': 'token', 'data': {'text': token}}
        except Exception:
            fallback = chat_service.chat_completion([{'role': 'user', 'content': final_prompt}])
            full_reply = [fallback]
            yield {'event': 'token', 'data': {'text': fallback}}
        reply = ''.join(full_reply).strip()
        if not reply:
            reply = 'No answer could be generated.'
        yield {'event': 'done', 'data': {'reply': reply, 'sources': sources, 'rewritten_question': rewritten_question if rewritten_question != question else None, 'final_prompt': final_prompt}}

    def chat(self, question: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
        result = self.run(question, history)
        return result.get("reply", "")


customer_service_agent = CustomerServiceAgent()

__all__ = ["CustomerServiceAgent", "customer_service_agent"]
