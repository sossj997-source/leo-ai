from app.agent.agent import Agent
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.register_tools import register_basic_tools
from app.services.groq_service import GroqService
from app.services.vector_store import VectorStoreService
from app.agent.proactive_manager import ProactiveManager


def create_agent():

    vector_store = VectorStoreService()

    groq_service = GroqService(
        vector_store
    )

    proactive_manager = ProactiveManager()
    proactive_manager.start()

    registry = ToolRegistry()

    register_basic_tools(
        registry,
        proactive_manager=proactive_manager,
    )

    agent = Agent(
        groq_service=groq_service,
        tool_registry=registry,
    )

    return agent, registry


def main():

    print("\n================================")
    print("       LEO AGENT TEST")
    print("================================")

    try:

        agent, registry = create_agent()

        print(
            f"\nRegistered tools: {len(registry)}"
        )

        print("\nAvailable tools:")

        for tool in registry.list_tools():
            print(
                f"- {tool.name}: "
                f"{tool.description}"
            )

        print(
            "\nLeo Agent ready, Sirr."
        )

        print(
            "Type 'exit' or 'quit' to stop."
        )

        print(
            "================================\n"
        )

        while True:

            try:

                user_input = input(
                    "You: "
                ).strip()

            except (
                KeyboardInterrupt,
                EOFError
            ):

                print(
                    "\n\nLeo Agent stopped."
                )
                break

            if not user_input:
                continue

            if user_input.lower() in {
                "exit",
                "quit"
            }:

                print(
                    "\nLeo: Goodbye Sirr 👽"
                )
                break

            print(
                "\nLeo is thinking..."
            )

            result = agent.run(
                user_input
            )

            print(
                "\nLeo:",
                result.message
            )

            if result.tool_calls:

                print(
                    "\nTool used:"
                )

                for tool in result.tool_calls:

                    print(
                        f"- {tool.tool_name}"
                    )

            if result.tool_results:

                print(
                    "\nTool result:"
                )

                for tool_result in (
                    result.tool_results
                ):

                    if tool_result.success:

                        print(
                            f"- {tool_result.result}"
                        )

                    else:

                        print(
                            f"- Error: "
                            f"{tool_result.error}"
                        )

            print()

    except Exception as e:

        print(
            "\nAgent initialization failed:"
        )

        print(
            repr(e)
        )


if __name__ == "__main__":
    main()