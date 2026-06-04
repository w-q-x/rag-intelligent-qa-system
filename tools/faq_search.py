from infrastructure.rag import vector_store

from .base import Tool, ToolParameter


def search_faq(query: str, top_k: int = 5) -> str:
    results = vector_store.search(query, top_k=top_k)
    if not results:
        return "No relevant knowledge base entries were found."

    formatted_results = []
    for index, item in enumerate(results, 1):
        source = item.get("source", {})
        source_file = source.get("file", "unknown")
        distance = item.get("distance", 0.0)
        text = item.get("text", "")
        formatted_results.append(
            f"{index}. Source: {source_file}\n"
            f"   Score distance: {distance:.4f}\n"
            f"   Content: {text}"
        )
    return "\n\n".join(formatted_results)


search_faq_tool = Tool(
    name="search_faq",
    description="Search the knowledge base and return relevant child chunks.",
    func=search_faq,
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query.",
            required=True,
        ),
        ToolParameter(
            name="top_k",
            type="integer",
            description="Number of results to return.",
            required=False,
            default=5,
        ),
    ],
)
