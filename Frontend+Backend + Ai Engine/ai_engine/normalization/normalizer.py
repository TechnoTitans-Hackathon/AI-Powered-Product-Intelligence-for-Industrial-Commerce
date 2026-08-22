"""Value normalizer — normalizes without destroying original evidence."""

from __future__ import annotations

import re
import logging
from typing import Any, Optional

from ai_engine.schemas import FieldValue

logger = logging.getLogger(__name__)

# Unit normalization mapping
UNIT_ALIASES: dict[str, str] = {
    "inch": "in", "inches": "in", '"': "in",
    "foot": "ft", "feet": "ft", "'": "ft",
    "millimeter": "mm", "millimeters": "mm", "millimetre": "mm",
    "centimeter": "cm", "centimeters": "cm", "centimetre": "cm",
    "meter": "m", "meters": "m", "metre": "m",
    "kilogram": "kg", "kilograms": "kg", "kilo": "kg",
    "gram": "g", "grams": "g",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz",
    "volt": "V", "volts": "V",
    "amp": "A", "amps": "A", "ampere": "A", "amperes": "A",
    "watt": "W", "watts": "W",
    "kilowatt": "kW", "kilowatts": "kW",
    "horsepower": "HP",
    "celsius": "°C", "deg c": "°C", "deg. c": "°C", "degrees c": "°C",
    "fahrenheit": "°F", "deg f": "°F", "deg. f": "°F",
    "decibel": "dB", "decibels": "dB",
    "rpm": "RPM", "r.p.m.": "RPM",
}


class NormalizationEngine:
    """Normalizes values while preserving originals.

    Example:
        Original: "25 mm"
        Normalized value: 25.0
        Unit: mm
        Display: 25 mm
    """

    def normalize_field(self, field: FieldValue) -> FieldValue:
        """Normalize a single field value."""
        if field.value is None:
            return field

        original = field.value
        # Try to extract numeric value and unit
        numeric, unit = self._extract_numeric_and_unit(original)

        if numeric is not None:
            field.normalized_value = numeric
            if unit:
                field.unit = self._normalize_unit(unit)
            field.display_value = self._format_display(numeric, field.unit)
        else:
            # Non-numeric value — just clean up
            field.normalized_value = original.strip()
            field.display_value = original.strip()

        return field

    def normalize_product(self, fields: list[FieldValue]) -> list[FieldValue]:
        """Normalize all fields in a product."""
        return [self.normalize_field(f) for f in fields]

    @staticmethod
    def _extract_numeric_and_unit(value: str) -> tuple[Optional[float], Optional[str]]:
        """Extract a numeric value and unit from a string.

        Examples:
            '25 mm' → (25.0, 'mm')
            '120 V' → (120.0, 'V')
            '2.2 kW' → (2.2, 'kW')
            'Stainless Steel' → (None, None)
        """
        # Pattern: optional sign, digits (with optional decimal), optional unit
        match = re.match(
            r'^\s*([+-]?\d+(?:[.,]\d+)?(?:/\d+)?)\s*([a-zA-Z°/%]+(?:/[a-zA-Z]+)?)?\s*$',
            value.strip()
        )
        if match:
            num_str = match.group(1).replace(",", "")
            try:
                numeric = float(num_str)
                unit = match.group(2) if match.group(2) else None
                return numeric, unit
            except ValueError:
                pass

        # Try fraction pattern: "1/2 x 18 inch"
        fraction_match = re.match(r'^\s*(\d+/\d+)\s*(.+)$', value.strip())
        if fraction_match:
            try:
                parts = fraction_match.group(1).split("/")
                numeric = float(parts[0]) / float(parts[1])
                return numeric, fraction_match.group(2).strip()
            except (ValueError, ZeroDivisionError):
                pass

        return None, None

    @staticmethod
    def _normalize_unit(unit: str) -> str:
        """Normalize a unit string to its canonical form."""
        return UNIT_ALIASES.get(unit.lower().strip(), unit.strip())

    @staticmethod
    def _format_display(value: float, unit: Optional[str]) -> str:
        """Format a numeric value and unit for display."""
        # Show integers without decimal
        if value == int(value):
            display = str(int(value))
        else:
            display = f"{value:g}"

        if unit:
            display = f"{display} {unit}"
        return display
