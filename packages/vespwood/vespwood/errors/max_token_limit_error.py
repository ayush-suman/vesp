class MaxTokenLimitError(Exception):
    def __init__(self, assistant_response: str):
        self.assistant_response = assistant_response
        super().__init__(assistant_response)