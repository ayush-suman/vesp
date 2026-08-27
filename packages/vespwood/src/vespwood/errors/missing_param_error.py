class MissingParamError(Exception):
    def __init__(self, *params: str):
        self.params = params
        super().__init__("Params not provided to agent:", params)