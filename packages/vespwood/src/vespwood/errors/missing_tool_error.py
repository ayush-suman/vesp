class MissingToolError(Exception):
    def __init__(self, *tools: str):
        self.tools = tools
        super().__init__("Tools not provided to agent:", tools)
