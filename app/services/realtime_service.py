import logging
import os

from tavily import TavilyClient

from config import (
    GROQ_MODEL,
    ASSISTANT_NAME,
)

from app.services.groq_service import GroqService


logger = logging.getLogger("JARVIS")


class RealTimeGroqService(GroqService):

    def __init__(self, vector_store):

        super().__init__(vector_store)

        self.model = GROQ_MODEL
        self.assistant_name = ASSISTANT_NAME

        # -------------------------------
        # Tavily
        # -------------------------------

        self.tavily_client = None

        tavily_key = os.getenv("TAVILY_API_KEY")

        if tavily_key:
            try:
                self.tavily_client = TavilyClient(
                    api_key=tavily_key
                )

                logger.info(
                    "Tavily realtime search enabled."
                )

            except Exception as e:
                logger.error(
                    f"Tavily initialization failed: {repr(e)}"
                )

        else:
            logger.warning(
                "TAVILY_API_KEY not found."
            )

    # ==================================================
    # SEARCH QUERY
    # ==================================================

    def _extract_search_query(
        self,
        question,
        chat_history=None
    ):

        if not question:
            return ""

        return question.strip()[:500]

    # ==================================================
    # TAVILY SEARCH
    # ==================================================

    def search_tavily(self, query):

        if not self.tavily_client:
            return None

        if not query:
            return None

        try:

            return self.tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True
            )

        except Exception as e:

            logger.error(
                f"Tavily search failed: {repr(e)}"
            )

            return None

    # ==================================================
    # FORMAT SEARCH RESULTS
    # ==================================================

    def _format_search_results(
        self,
        search_results
    ):

        if not search_results:
            return ""

        parts = []

        answer = search_results.get(
            "answer"
        )

        if answer:
            parts.append(
                f"Summary:\n{answer}"
            )

        results = search_results.get(
            "results",
            []
        )

        for index, result in enumerate(
            results[:5],
            start=1
        ):

            title = result.get(
                "title",
                ""
            )

            content = result.get(
                "content",
                ""
            )

            url = result.get(
                "url",
                ""
            )

            if content:
                parts.append(
                    f"Source {index}: {title}\n"
                    f"{content[:1200]}\n"
                    f"URL: {url}"
                )

        return "\n\n".join(parts)

    # ==================================================
    # NORMAL REALTIME RESPONSE
    # ==================================================

    def get_response(
        self,
        question,
        chat_history=None
    ):

        search_query = (
            self._extract_search_query(
                question,
                chat_history
            )
        )

        search_results = (
            self.search_tavily(
                search_query
            )
        )

        extra_system_parts = []

        formatted_results = (
            self._format_search_results(
                search_results
            )
        )

        if formatted_results:

            extra_system_parts.append(
                "Fresh web search information:\n\n"
                + formatted_results
            )

        else:

            extra_system_parts.append(
                "No fresh web search information "
                "was available."
            )

        prompt, messages = (
            self._build_prompt_and_messages(
                question,
                chat_history,
                extra_system_parts=extra_system_parts
            )
        )

        response = self._invoke_llm(
            prompt,
            messages,
            question
        )

        self._extract_memory(
            question
        )

        return response

    # ==================================================
    # REALTIME STREAM
    # ==================================================

    def stream_response(
        self,
        question,
        chat_history=None
    ):

        try:

            # ------------------------------------------
            # 1. Search
            # ------------------------------------------

            search_query = (
                self._extract_search_query(
                    question,
                    chat_history
                )
            )

            search_results = (
                self.search_tavily(
                    search_query
                )
            )

            # ------------------------------------------
            # 2. Send search results to frontend
            # ------------------------------------------

            if search_results:

                yield {
                    "search_results": search_results
                }

            # ------------------------------------------
            # 3. Prepare compact search context
            # ------------------------------------------

            formatted_results = (
                self._format_search_results(
                    search_results
                )
            )

            extra_system_parts = []

            if formatted_results:

                extra_system_parts.append(
                    "Fresh web search information:\n\n"
                    + formatted_results
                )

            else:

                extra_system_parts.append(
                    "No fresh web search information "
                    "was available."
                )

            # ------------------------------------------
            # 4. Build prompt
            # ------------------------------------------

            prompt, messages = (
                self._build_prompt_and_messages(
                    question,
                    chat_history,
                    extra_system_parts=extra_system_parts
                )
            )

            # ------------------------------------------
            # 5. Stream Groq response
            # ------------------------------------------

            yield from self._stream_llm(
                prompt,
                messages,
                question
            )

            # ------------------------------------------
            # 6. Memory
            # ------------------------------------------

            self._extract_memory(
                question
            )

        except Exception as e:

            logger.error(
                f"Realtime stream failed: {repr(e)}"
            )

            raise Exception(
                f"Realtime stream error: {str(e)}"
            ) from e