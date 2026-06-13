from typing import Any, Dict
from .base_agent import BaseAgent

class ResearchAgent(BaseAgent):
    """
    Performs multi-source internet searches, reads articles and papers, 
    and synthesizes summaries with full inline citations.
    """
    def __init__(self, llm_provider):
        super().__init__(name="research", llm_provider=llm_provider)
        self._capabilities = [
            "search_duckduckgo", "search_google", "search_wikipedia", 
            "search_arxiv", "fetch_page_content"
        ]

    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        target_task = ""
        pending_tasks = state.get("pending_tasks", [])
        if pending_tasks:
            target_task = pending_tasks[0].get("description", "")
        else:
            messages = state.get("messages", [])
            if messages:
                target_task = messages[-1].get("content", "")

        system_prompt = f"""
You are the dedicated Research Agent. Your job is to deeply investigate topics using a multi-source approach.

Topic to Research: "{target_task}"

Your Capabilities (MCP Tools):
1. **search_duckduckgo(query)**: Good for general web queries. Returns links + snippets.
2. **search_google(query)**: Good for product comparisons and broad reach. Returns links.
3. **search_wikipedia(query)**: Good for factual baseline context. Returns encyclopedic summary.
4. **search_arxiv(query)**: Good for highly technical topics and academic papers. Returns abstracts and PDF URLs.
5. **fetch_page_content(url)**: Fetches the raw text content of a webpage for deep reading.

Strict Methodology:
1. Determine the intent of the research (Is it technical? Academic? A product comparison?).
2. Select the best combination of search tools. For example, use Arxiv for papers, Wikipedia for facts, and Google/DuckDuckGo for products or general articles.
3. You MUST read the underlying information. Either rely on the rich snippets from Arxiv/Wikipedia, or explicitly call `fetch_page_content` on URLs returned by Google/DuckDuckGo.
4. Synthesize your findings into a comprehensive, well-structured summary.
5. ALWAYS append exact source URLs as references at the bottom of your final output.

Output your execution plan, call the appropriate tools iteratively, and compile the final report.
"""

        try:
            response = await self._llm_provider.generate(
                prompt=target_task,
                system_prompt=system_prompt,
                tools=self._capabilities
            )
            
            return {
                "current_agent": self.get_name(),
                "next_node": "executor_agent",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": response}]
            }
        except Exception as e:
            return {
                "current_agent": self.get_name(),
                "next_node": "END",
                "messages": state.get("messages", []) + [{"role": "assistant", "content": f"Failed to process Research command: {str(e)}"}]
            }
