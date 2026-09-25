class ClaimValidationError(ValueError):
    pass


class ClaimConflictError(RuntimeError):
    pass


class ClaimResourceNotFoundError(LookupError):
    pass
