class MissingValidatorError(Exception):
    def __init__(self, *validators: str):
        self.validators = validators
        super().__init__("Validators not provided to agent:", validators)