import json
from app.domain.interfaces import LLM, VectorStore
from app.models import QuestionLog
from app.tools import TOOL_SCHEMAS, search_documents, get_document, search_previous_questions, calculate_score

AVAILABLE_TOOLS = {
    "search_documents": lambda args, db, user_id, vector_store: search_documents(args["query"], vector_store),
    "get_document": lambda args, db, user_id, vector_store: get_document(args["document_id"], db),
    "search_previous_questions": lambda args, db, user_id, vector_store: search_previous_questions(args["keyword"], user_id, db),
    "calculate_score": lambda args, db, user_id, vector_store: calculate_score(args["distances"]),
}


class AskAgentUseCase:
    def __init__(self, llm: LLM, vector_store: VectorStore, max_iterations: int = 5):
        self.llm = llm
        self.vector_store = vector_store
        self.max_iterations = max_iterations

    def execute(self, question: str, db, user_id: int) -> dict:
        messages = [
            {"role": "system", "content": (
                "You are a medical knowledge assistant. You must ALWAYS call search_documents "
                "at least once before answering any question about medical conditions, symptoms, "
                "or treatments — even if you believe you already know the answer. Base your final "
                "answer ONLY on the content returned by your tools, never on your own general "
                "knowledge. If the retrieved content does not contain enough information, say "
                "clearly: 'I don't have enough information to answer this.' Other tools "
                "(search_previous_questions, get_document, calculate_score) are available to use "
                "as appropriate, in addition to search_documents."
            )},
            {"role": "user", "content": question},
        ]

        collected_sources = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for iteration in range(self.max_iterations):
            force_search = (iteration == 0)
            tool_choice = {"type": "function", "function": {"name": "search_documents"}} if force_search else "auto"

            response = self.llm.generate(messages, tools=TOOL_SCHEMAS, tool_choice=tool_choice)

            total_prompt_tokens += response.prompt_tokens
            total_completion_tokens += response.completion_tokens

            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls,
            })

            if not response.tool_calls:
                question_log = QuestionLog(user_id=user_id, question=question, answer=response.content)
                db.add(question_log)
                db.commit()
                return {
                    "answer": response.content,
                    "sources": collected_sources,
                    "iterations": iteration + 1,
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens,
                }

            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    result = {"error": f"Could not parse arguments for {tool_name}"}
                else:
                    tool_function = AVAILABLE_TOOLS.get(tool_name)
                    if tool_function is None:
                        result = {"error": f"Unknown tool: {tool_name}"}
                    else:
                        result = tool_function(arguments, db, user_id, self.vector_store)

                        if tool_name == "search_documents" and "chunks" in result:
                            for chunk in result["chunks"]:
                                collected_sources.append({
                                    "title": chunk["document_title"],
                                    "source": chunk["document_source"],
                                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

        return {
            "answer": "I wasn't able to complete this within the allowed steps.",
            "sources": collected_sources,
            "iterations": self.max_iterations,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
        }