#============================================================================
# Exceptions


class PathError(Exception):
    "PathError: base exception for path module."


class NoSchemeError(PathError):
    "NoSchemeError is raised if scheme is used that has no backend"


class WrongSchemeError(PathError):
    "WrongSchemeError is raised if functionality requires specific schemes"

class FileDoesNotExistError(PathError):
    "FileDoesNotExistError is raised, if resource does not exist"

class NoDefinedOperationError(PathError):
    "NoDefinedOperationError is raised if method is not supported by backend"

class OptionsError(PathError):
    "OptionsError is raised if specific options need to be used"


class RemoteConnectionTimeout(PathError):
    "Remote connection could not be established"

