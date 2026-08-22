"""Deterministic validation engine — does NOT depend entirely on an LLM."""

from __future__ import annotations

import logging
import re

from ai_engine.schemas import (
    FieldStatus,
    ProductIntelligenceResult,
    ValidationCheck,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Known units for validation
VALID_UNITS = {
    "in", "inch", "inches", "ft", "feet", "mm", "cm", "m",
    "oz", "lb", "lbs", "g", "kg",
    "V", "A", "W", "kW", "HP",
    "°C", "°F", "dBA", "dB",
    "L/min", "GPM", "bar", "psi", "RPM", "FPM",
    "each", "pack", "box", "set",
}


class ValidationEngine:
    """Deterministic + heuristic validation for product intelligence.

    Checks schema, types, units, numeric consistency, required fields,
    duplicates, conflicts, malformed values, evidence presence.
    """

    def validate(self, result: ProductIntelligenceResult) -> ValidationResult:
        """Run all validation checks on a product result."""
        report = ValidationResult()

        self._check_identity(result, report)
        self._check_descriptions(result, report)
        self._check_features(result, report)
        self._check_attributes(result, report)
        self._check_evidence_presence(result, report)
        self._check_conflicts(result, report)
        self._check_duplicate_attributes(result, report)

        logger.info(
            f"Validation: {report.passed_checks}/{report.total_checks} passed, "
            f"{report.failed_checks} failed, {report.warning_checks} warnings"
        )
        return report

    def _check_identity(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Validate product identity fields."""
        identity = result.identity

        report.add_check(ValidationCheck(
            check_name="identity_part_number",
            passed=bool(identity.part_number),
            field_name="part_number",
            message="Part number is present" if identity.part_number else "Part number is missing",
            severity="ERROR" if not identity.part_number else "INFO",
        ))

        report.add_check(ValidationCheck(
            check_name="identity_manufacturer",
            passed=bool(identity.manufacturer),
            field_name="manufacturer",
            message="Manufacturer is present" if identity.manufacturer else "Manufacturer is missing",
            severity="WARNING" if not identity.manufacturer else "INFO",
        ))

    def _check_descriptions(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Validate description fields."""
        if result.short_description and result.short_description.value:
            desc = result.short_description.value
            report.add_check(ValidationCheck(
                check_name="short_desc_length",
                passed=len(desc) <= 200,
                field_name="short_description",
                message=f"Short description length: {len(desc)} chars" + (
                    " (exceeds 200)" if len(desc) > 200 else ""
                ),
                severity="WARNING" if len(desc) > 200 else "INFO",
            ))

        if result.long_description and result.long_description.value:
            desc = result.long_description.value
            report.add_check(ValidationCheck(
                check_name="long_desc_present",
                passed=len(desc) > 20,
                field_name="long_description",
                message="Long description is substantive" if len(desc) > 20 else "Long description too short",
                severity="WARNING" if len(desc) <= 20 else "INFO",
            ))

    def _check_features(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Validate feature fields."""
        report.add_check(ValidationCheck(
            check_name="features_count",
            passed=len(result.features) <= 20,
            field_name="features",
            message=f"Feature count: {len(result.features)}" + (
                " (exceeds 20 max)" if len(result.features) > 20 else ""
            ),
            severity="WARNING" if len(result.features) > 20 else "INFO",
        ))

    def _check_attributes(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Validate attribute fields — types, units, values."""
        for attr in result.attributes:
            # Check for empty attribute names
            report.add_check(ValidationCheck(
                check_name=f"attr_name_{attr.field_name}",
                passed=bool(attr.field_name and attr.field_name.strip()),
                field_name=attr.field_name,
                message="Attribute has a valid name" if attr.field_name else "Empty attribute name",
                severity="ERROR" if not attr.field_name else "INFO",
            ))

            # Validate units if present
            if attr.unit:
                is_known_unit = attr.unit in VALID_UNITS
                report.add_check(ValidationCheck(
                    check_name=f"attr_unit_{attr.field_name}",
                    passed=is_known_unit,
                    field_name=attr.field_name,
                    message=f"Unit '{attr.unit}' is " + ("recognized" if is_known_unit else "non-standard"),
                    severity="WARNING" if not is_known_unit else "INFO",
                ))

            # Validate numeric values contain actual numbers
            if attr.value and attr.unit:
                numeric_match = re.search(r'\d', str(attr.value))
                if not numeric_match and attr.unit in {"V", "A", "W", "kW", "mm", "cm", "in", "kg", "lb", "dBA"}:
                    report.add_check(ValidationCheck(
                        check_name=f"attr_numeric_{attr.field_name}",
                        passed=False,
                        field_name=attr.field_name,
                        message=f"Expected numeric value for unit '{attr.unit}' but got '{attr.value}'",
                        severity="WARNING",
                    ))

            # Mark validation status on the field
            attr.validation_passed = True  # Default to true, set false if checks fail

    def _check_evidence_presence(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Ensure DIRECTLY_SUPPORTED fields have evidence."""
        all_fields = [result.short_description, result.long_description] + result.attributes
        for field in all_fields:
            if field is None:
                continue
            if field.status == FieldStatus.DIRECTLY_SUPPORTED and not field.evidence:
                report.add_check(ValidationCheck(
                    check_name=f"evidence_presence_{field.field_name}",
                    passed=False,
                    field_name=field.field_name,
                    message="Field claims DIRECTLY_SUPPORTED but has no evidence attached",
                    severity="WARNING",
                ))
                field.validation_passed = False

    def _check_conflicts(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Flag unresolved conflicts."""
        for conflict in result.conflicts:
            report.add_check(ValidationCheck(
                check_name=f"conflict_{conflict.field_name}",
                passed=False,
                field_name=conflict.field_name,
                message=f"Unresolved conflict: '{conflict.value_a}' vs '{conflict.value_b}'",
                severity="WARNING",
            ))

    def _check_duplicate_attributes(self, result: ProductIntelligenceResult, report: ValidationResult) -> None:
        """Check for duplicate attribute names."""
        seen: dict[str, int] = {}
        for attr in result.attributes:
            name = attr.field_name.lower()
            seen[name] = seen.get(name, 0) + 1

        for name, count in seen.items():
            if count > 1:
                report.add_check(ValidationCheck(
                    check_name=f"duplicate_attr_{name}",
                    passed=False,
                    field_name=name,
                    message=f"Duplicate attribute '{name}' appears {count} times",
                    severity="WARNING",
                ))
