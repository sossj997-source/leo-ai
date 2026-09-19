from typing import Any, Callable, Dict, List, Optional


class ToolDefinition:
    """
    Leo ke ek tool ki complete definition.
    """

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        requires_confirmation: bool = False,
    ):
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters or {}
        self.requires_confirmation = requires_confirmation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
        }


class ToolRegistry:
    """
    Leo ke saare available tools ko register,
    find aur execute karta hai.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    # ==================================================
    # REGISTER TOOL
    # ==================================================

    def register(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Any]] = None,
        requires_confirmation: bool = False,
    ) -> ToolDefinition:

        if not name or not name.strip():
            raise ValueError(
                "Tool name cannot be empty."
            )

        if not callable(function):
            raise TypeError(
                f"Tool '{name}' function must be callable."
            )

        name = name.strip()

        if name in self._tools:
            raise ValueError(
                f"Tool '{name}' is already registered."
            )

        tool = ToolDefinition(
            name=name,
            description=description.strip(),
            function=function,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
        )

        self._tools[name] = tool

        return tool

    # ==================================================
    # UNREGISTER TOOL
    # ==================================================

    def unregister(
        self,
        name: str
    ) -> bool:

        if name in self._tools:
            del self._tools[name]
            return True

        return False

    # ==================================================
    # GET TOOL
    # ==================================================

    def get(
        self,
        name: str
    ) -> Optional[ToolDefinition]:

        return self._tools.get(name)

    # ==================================================
    # CHECK TOOL
    # ==================================================

    def has(
        self,
        name: str
    ) -> bool:

        return name in self._tools

    # ==================================================
    # LIST TOOLS
    # ==================================================

    def list_tools(
        self
    ) -> List[ToolDefinition]:

        return list(
            self._tools.values()
        )

    # ==================================================
    # TOOL SCHEMAS
    # ==================================================

    def get_tool_schemas(
        self
    ) -> List[Dict[str, Any]]:

        return [
            tool.to_dict()
            for tool in self._tools.values()
        ]

    # ==================================================
    # ARGUMENT NORMALIZATION
    # ==================================================

    def _normalize_arguments(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize common LLM argument-name variations.

        Example:

            application -> app_name
            application_name -> app_name
            program -> app_name
            app -> app_name

        Only aliases for parameters that actually exist
        on the tool are accepted.
        """

        if not arguments:
            return {}

        normalized = dict(arguments)

        aliases = {
            "application": "app_name",
            "application_name": "app_name",
            "program": "app_name",
            "program_name": "app_name",
            "app": "app_name",
            "expression_text": "expression",
            "math_expression": "expression",
        }

        for alias, canonical in aliases.items():

            if (
                alias in normalized
                and canonical in tool.parameters
                and canonical not in normalized
            ):

                normalized[canonical] = normalized.pop(
                    alias
                )

        return normalized

    # ==================================================
    # VALIDATE ARGUMENTS
    # ==================================================

    def _validate_arguments(
        self,
        tool: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> None:

        expected = tool.parameters or {}

        # Unknown arguments
        unknown = [
            key
            for key in arguments
            if key not in expected
        ]

        if unknown:

            raise ValueError(
                f"Unknown argument(s) for tool "
                f"'{tool.name}': "
                f"{', '.join(unknown)}"
            )

        # Required arguments
        for name, schema in expected.items():

            if (
                schema.get("required", False)
                and name not in arguments
            ):

                raise ValueError(
                    f"Missing required argument "
                    f"'{name}' for tool "
                    f"'{tool.name}'."
                )

    # ==================================================
    # EXECUTE TOOL
    # ==================================================

    def execute(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:

        tool = self.get(name)

        if not tool:

            raise ValueError(
                f"Tool '{name}' is not registered."
            )

        arguments = arguments or {}

        if not isinstance(
            arguments,
            dict
        ):

            raise ValueError(
                "Tool arguments must be an object."
            )

        # Normalize aliases
        arguments = self._normalize_arguments(
            tool,
            arguments,
        )

        # Validate arguments
        self._validate_arguments(
            tool,
            arguments,
        )

        try:

            return tool.function(
                **arguments
            )

        except TypeError as e:

            raise ValueError(
                f"Invalid arguments for tool "
                f"'{name}': {e}"
            ) from e

        except Exception as e:

            raise RuntimeError(
                f"Tool '{name}' execution failed: {e}"
            ) from e

    # ==================================================
    # CONFIRMATION CHECK
    # ==================================================

    def requires_confirmation(
        self,
        name: str
    ) -> bool:

        tool = self.get(name)

        if not tool:

            raise ValueError(
                f"Tool '{name}' is not registered."
            )

        return tool.requires_confirmation

    # ==================================================
    # CLEAR
    # ==================================================

    def clear(
        self
    ) -> None:

        self._tools.clear()

    # ==================================================
    # TOOL COUNT
    # ==================================================

    def __len__(
        self
    ) -> int:

        return len(self._tools)