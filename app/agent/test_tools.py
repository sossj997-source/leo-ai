from app.agent.tool_registry import ToolRegistry
from app.agent.tools.register_tools import register_basic_tools


def main():
    registry = ToolRegistry()
    register_basic_tools(registry)

    print("\n=== REGISTERED TOOLS ===")

    for tool in registry.list_tools():
        print(f"- {tool.name}")

    print("\n=== FILE TOOL TESTS ===")

    print("\n1. Open Downloads:")
    print(registry.execute(
        "open_folder",
        {"folder_name": "Downloads"}
    ))

    print("\n2. List Downloads:")
    result = registry.execute(
        "list_files",
        {"folder_name": "Downloads"}
    )
    print(result)

    print("\n3. Create LeoTest folder:")
    print(registry.execute(
        "create_folder",
        {
            "folder_name": "LeoTest",
            "location": "Desktop"
        }
    ))

    print("\n4. Find LeoTest:")
    result = registry.execute(
        "find_file",
        {
            "file_name": "LeoTest",
            "search_folder": "Desktop"
        }
    )
    print(result)


if __name__ == "__main__":
    main()