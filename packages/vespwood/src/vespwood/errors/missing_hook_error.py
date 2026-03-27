class MissingHookError(Exception):
    def __init__(self, hooks: list[str]):
        self.hooks = hooks
        super().__init__("Hooks not provided:", hooks)