"""Dependency-free Bridge domain errors used by transport routing."""


class CharacterWriteValidationError(ValueError):
    pass


class CharacterRevisionConflict(RuntimeError):
    def __init__(self, *, current_revision: str):
        super().__init__("Character revision conflict")
        self.current_revision = current_revision
