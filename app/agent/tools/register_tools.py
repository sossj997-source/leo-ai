from app.agent.tool_registry import ToolRegistry

from app.agent.tools.basic_tools import (
    get_time,
    calculator,
    calculate_percentage,
)

from app.agent.tools.system_tools import (
    get_system_info,
)

from app.agent.tools.windows_tools import (
    open_app,
)

from app.agent.tools.file_tools import (
    open_folder,
    list_files,
    create_folder,
    find_file,
    open_file,
)

from app.agent.tools.browser_tools import (
    open_website,
)

from app.agent.tools.writing_tools import (
    open_text_editor,
    write_text,
    open_editor_and_write,
)

from app.agent.tools.browser_automation import (
    open_browser,
    navigate_to_url,
    search_page,
    click_first_result,
    type_text,
)

from app.agent.proactive_manager import ProactiveManager
from app.agent.tools.proactive_tools import ProactiveTools


def register_basic_tools(
    registry: ToolRegistry,
    proactive_manager: ProactiveManager | None = None,
) -> ToolRegistry:
    """
    Register Leo's available tools.
    """

    # ==================================================
    # TIME
    # ==================================================

    registry.register(
        name="get_time",
        description="Get the current local date and time.",
        function=get_time,
        parameters={},
    )

    # ==================================================
    # CALCULATOR
    # ==================================================

    registry.register(
        name="calculator",
        description="Perform safe mathematical calculations.",
        function=calculator,
        parameters={
            "expression": {
                "type": "string",
                "description": "Mathematical expression to calculate.",
                "required": True,
            }
        },
    )

    # ==================================================
    # PERCENTAGE
    # ==================================================

    registry.register(
        name="calculate_percentage",
        description="Calculate a percentage of a given value.",
        function=calculate_percentage,
        parameters={
            "value": {
                "type": "number",
                "description": "The base value.",
                "required": True,
            },
            "percentage": {
                "type": "number",
                "description": "The percentage to calculate.",
                "required": True,
            },
        },
    )

    # ==================================================
    # SYSTEM INFO
    # ==================================================

    registry.register(
        name="system_info",
        description=(
            "Get basic information about the current "
            "computer, including operating system, "
            "processor, RAM, CPU usage, machine type, "
            "and Python version."
        ),
        function=get_system_info,
        parameters={},
    )

    # ==================================================
    # OPEN APP
    # ==================================================

    registry.register(
        name="open_app",
        description=(
            "Open a safe Windows application such as "
            "Notepad, Calculator, Paint, or another "
            "executable available in the system PATH."
        ),
        function=open_app,
        parameters={
            "app_name": {
                "type": "string",
                "description": "Name of the Windows application to open.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # OPEN FOLDER
    # ==================================================

    registry.register(
        name="open_folder",
        description=(
            "Open a folder in Windows File Explorer. "
            "Supports common folders such as Desktop, "
            "Downloads, Documents, Pictures, Music, and Videos."
        ),
        function=open_folder,
        parameters={
            "folder_name": {
                "type": "string",
                "description": "Name or path of the folder to open.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # LIST FILES
    # ==================================================

    registry.register(
        name="list_files",
        description="List files and folders inside a specified folder.",
        function=list_files,
        parameters={
            "folder_name": {
                "type": "string",
                "description": "Name or path of the folder to inspect.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # CREATE FOLDER
    # ==================================================

    registry.register(
        name="create_folder",
        description=(
            "Create a new folder inside a specified "
            "location such as Desktop or Downloads."
        ),
        function=create_folder,
        parameters={
            "folder_name": {
                "type": "string",
                "description": "Name of the new folder.",
                "required": True,
            },
            "location": {
                "type": "string",
                "description": "Parent location where the folder should be created.",
                "required": True,
            },
        },
        requires_confirmation=False,
    )

    # ==================================================
    # FIND FILE
    # ==================================================

    registry.register(
        name="find_file",
        description=(
            "Search for a file or folder by its exact "
            "name inside a specified folder."
        ),
        function=find_file,
        parameters={
            "file_name": {
                "type": "string",
                "description": "Name of the file or folder to find.",
                "required": True,
            },
            "search_folder": {
                "type": "string",
                "description": "Folder where the search should start.",
                "required": True,
            },
        },
        requires_confirmation=False,
    )

    # ==================================================
    # OPEN FILE
    # ==================================================

    registry.register(
        name="open_file",
        description="Open a file using its default Windows application.",
        function=open_file,
        parameters={
            "file_path": {
                "type": "string",
                "description": "Full path of the file to open.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # OPEN WEBSITE
    # ==================================================

    registry.register(
        name="open_website",
        description=(
            "Open a website URL in an existing Chrome session. "
            "A new tab may be created inside that existing Chrome, "
            "but Leo never launches a new browser process."
        ),
        function=open_website,
        parameters={
            "url": {
                "type": "string",
                "description": "Website URL to open.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # OPEN BROWSER
    # ==================================================

    registry.register(
        name="open_browser",
        description=(
            "Connect to and focus the already-running Chrome. "
            "Leo never launches a new browser process or profile."
        ),
        function=open_browser,
        parameters={
            "browser_name": {
                "type": "string",
                "description": "Use 'chrome'. Existing Chrome only.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # NAVIGATE TO URL
    # ==================================================

    registry.register(
        name="navigate_to_url",
        description=(
            "Navigate to a website in existing Chrome. "
            "This may create a new tab inside the existing Chrome "
            "process, but never launches a new browser."
        ),
        function=navigate_to_url,
        parameters={
            "url": {
                "type": "string",
                "description": "The complete website URL to open.",
                "required": True,
            },
            "browser_name": {
                "type": "string",
                "description": "Browser to use: existing Chrome only.",
                "required": False,
            },
        },
        requires_confirmation=False,
    )

    # ==================================================
    # SEARCH CURRENT BROWSER PAGE
    # ==================================================

    registry.register(
        name="browser_search",
        description=(
            "Search using the visible search box in the currently "
            "active existing Chrome tab. Does not launch a browser."
        ),
        function=search_page,
        parameters={
            "query": {
                "type": "string",
                "description": "Text to search for.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # CLICK FIRST SEARCH RESULT
    # ==================================================

    registry.register(
        name="browser_click_first_result",
        description=(
            "Click the first visible search result in the currently "
            "active existing Chrome tab. Does not launch a browser."
        ),
        function=click_first_result,
        parameters={},
        requires_confirmation=False,
    )

    # ==================================================
    # BROWSER TYPE TEXT
    # ==================================================

    registry.register(
        name="browser_type_text",
        description=(
            "Type text into the currently focused visible Chrome field "
            "using PyAutoGUI. Does not use CDP or an extension."
        ),
        function=type_text,
        parameters={
            "text": {
                "type": "string",
                "description": "Text to type into the active browser field.",
                "required": True,
            }
        },
        requires_confirmation=False,
    )

    # ==================================================
    # WRITING TOOLS
    # ==================================================

    registry.register(
        name="open_text_editor",
        description=(
            "Open a local text editor for writing. "
            "Supported editors are Notepad and WordPad."
        ),
        function=open_text_editor,
        parameters={
            "editor": {
                "type": "string",
                "description": "Editor to open: notepad or wordpad.",
                "required": False,
            }
        },
        requires_confirmation=False,
    )

    registry.register(
        name="write_text",
        description=(
            "Type text into the currently focused visible text editor "
            "using PyAutoGUI."
        ),
        function=write_text,
        parameters={
            "text": {
                "type": "string",
                "description": "Text to write.",
                "required": True,
            },
            "clear_existing": {
                "type": "boolean",
                "description": "Select all existing text before writing.",
                "required": False,
            },
        },
        requires_confirmation=False,
    )

    registry.register(
        name="open_editor_and_write",
        description=(
            "Open Notepad or WordPad and write the supplied text into it."
        ),
        function=open_editor_and_write,
        parameters={
            "text": {
                "type": "string",
                "description": "Text to write.",
                "required": True,
            },
            "editor": {
                "type": "string",
                "description": "Editor to open: notepad or wordpad.",
                "required": False,
            },
            "clear_existing": {
                "type": "boolean",
                "description": "Select all existing text before writing.",
                "required": False,
            },
        },
        requires_confirmation=False,
    )

    # ==================================================
    # PROACTIVE TOOLS
    # ==================================================

    if proactive_manager is not None:

        proactive_tools = ProactiveTools(proactive_manager)

        # CREATE REMINDER
        registry.register(
            name="create_reminder",
            description=(
                "Create a proactive reminder that Leo "
                "will execute at a specified date and time."
            ),
            function=proactive_tools.create_reminder,
            parameters={
                "name": {
                    "type": "string",
                    "description": "Unique name for the reminder.",
                    "required": True,
                },
                "run_at": {
                    "type": "string",
                    "description": (
                        "Reminder execution time in ISO datetime format, "
                        "for example 2026-09-08T17:30:00."
                    ),
                    "required": True,
                },
                "message": {
                    "type": "string",
                    "description": "Message Leo should remind the user.",
                    "required": True,
                },
                "repeat_seconds": {
                    "type": "integer",
                    "description": (
                        "Optional repeat interval in seconds. "
                        "Use 86400 for daily reminders."
                    )
                }
            },
            requires_confirmation=False,
        )

        # REMOVE REMINDER
        registry.register(
            name="remove_reminder",
            description="Remove an existing proactive reminder by its name.",
            function=proactive_tools.remove_reminder,
            parameters={
                "name": {
                    "type": "string",
                    "description": "Name of the reminder to remove.",
                    "required": True,
                }
            },
            requires_confirmation=False,
        )

        # LIST REMINDERS
        registry.register(
            name="list_reminders",
            description="List all proactive reminders currently known to Leo.",
            function=proactive_tools.list_reminders,
            parameters={},
            requires_confirmation=False,
        )

        # CREATE ACTIVITY RULE
        registry.register(
            name="create_activity_rule",
            description=(
                "Create a proactive rule that triggers when "
                "a specific application becomes active."
            ),
            function=proactive_tools.create_activity_rule,
            parameters={
                "name": {
                    "type": "string",
                    "description": "Unique name for the activity rule.",
                    "required": True,
                },
                "app_name": {
                    "type": "string",
                    "description": (
                        "Application process name, for example "
                        "msedge.exe or Code.exe."
                    ),
                    "required": True,
                },
                "message": {
                    "type": "string",
                    "description": (
                        "Message Leo should show when the "
                        "application becomes active."
                    ),
                    "required": True,
                },
            },
            requires_confirmation=False,
        )

    return registry