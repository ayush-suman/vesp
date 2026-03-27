class MissingParamError(Exception):
    def __init__(self, params: list[str]):
        self.params = params
        super().__init__("Params not provided to agent:", params)