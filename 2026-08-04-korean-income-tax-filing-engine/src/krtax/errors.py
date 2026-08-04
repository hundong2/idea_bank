class TaxDomainError(Exception):
    """Base class for deterministic domain failures."""


class ValidationError(TaxDomainError):
    """Input is internally inconsistent or outside its declared contract."""


class UnsupportedCase(TaxDomainError):
    """The case requires a tax rule not implemented by this bounded module."""


class EFileSpecUnavailable(TaxDomainError):
    """No reviewed official e-file schema is registered for the requested year."""
