from typing import Any
from typing import Callable
from typing import Dict

ExtractorType = Callable[[str], Dict[str, Any]]


class ActionProcessor:
    def __init__(
        self,
        tools: Dict[str, Any] | None = None,
        custom_extractor: ExtractorType | None = None,
    ) -> None:
        self.tools = tools or {}
        self.dict = {tool.name: tool for tool in tools}
        self.custom_extractor = custom_extractor

    def extract_function(self, text: str) -> Dict[str, Any] | None:
        if self.custom_extractor:
            extracted = self.custom_extractor(text)
            if (
                not isinstance(extracted, dict)
                or "name" not in extracted
                or "parameters" not in extracted
            ):
                raise ValueError(
                    "Custom extractor must return a dictionary with 'name' and 'parameters' keys."
                )
            return extracted
        else:
            import json

            j = json.loads(text)
            return {"name": j["function"], "parameters": j["parameters"]}

    def respond(self, text: str):
        function = None
        try:
            function = self.extract_function(text)
        except Exception as e:
            exception_type = type(e).__name__
            exception_message = str(e)
            full_exception_string = f"{exception_type}: {exception_message}"
            return (
                None,
                False,
                f"Unable to extract a valid function from the input. Error encountered in extractor: {full_exception_string}",
            )

        if function["name"] not in self.dict:
            return None, False, "Function or tool not found"

        response = ""
        try:
            response = self.dict[function["name"]](**function["parameters"])
        except Exception as e:
            exception_type = type(e).__name__
            exception_message = str(e)
            full_exception_string = f"{exception_type}: {exception_message}"
            return (
                None,
                False,
                f"Unable to invoke valid function {function['name']}, parameters: {function['parameters']}. Error encountered: {full_exception_string}",
            )

        return response, True, None
