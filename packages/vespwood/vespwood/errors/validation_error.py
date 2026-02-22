class ValidationError(Exception):
    def __init__(self, validator_response: str):
        self.validator_response = validator_response
        super().__init__(validator_response)