class ScriptRepositoryError(Exception):
    pass


class ScriptNotFoundError(ScriptRepositoryError):
    pass


class ScriptReadError(ScriptRepositoryError):
    pass
