class MissingSchemaError(Exception):
    def __init__(self, schemas: list[str]):
        self.schemas = schemas
        super().__init__("Schemas not provided to agent:", schemas)


