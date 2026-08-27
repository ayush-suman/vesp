class MissingStructureError(Exception):
    def __init__(self, *structures: str):
        self.structures = structures
        super().__init__("Structures not provided:", structures)