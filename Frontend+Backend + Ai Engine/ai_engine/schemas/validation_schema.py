"""Validation result schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    """A single validation check result."""
    check_name: str
    passed: bool
    field_name: Optional[str] = None
    message: str = ""
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Aggregated validation result for a product."""
    passed: bool = True
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    checks: list[ValidationCheck] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def add_check(self, check: ValidationCheck) -> None:
        """Add a check and update aggregates."""
        self.checks.append(check)
        self.total_checks += 1
        if check.passed:
            self.passed_checks += 1
        elif check.severity == "WARNING":
            self.warning_checks += 1
            self.warnings.append(f"{check.check_name}: {check.message}")
        else:
            self.failed_checks += 1
            self.errors.append(f"{check.check_name}: {check.message}")
            self.passed = False
