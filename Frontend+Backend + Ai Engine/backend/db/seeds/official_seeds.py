from sqlalchemy.orm import Session
from backend.db.models import (
    OfficialManufacturerBrand,
    OfficialLOV,
    OfficialUOM,
    OfficialDecimalFraction
)
from backend.core.logging import logger

# ---------------------------------------------------------------------------
# MULTI-INDUSTRY MANUFACTURER / BRAND SEED DATA
# ---------------------------------------------------------------------------
INITIAL_MANUFACTURER_BRANDS = [
    # Bearings
    {"manufacturer": "SKF Group", "brand": "SKF", "normalized_name": "skf"},
    {"manufacturer": "NSK Ltd.", "brand": "NSK", "normalized_name": "nsk"},
    {"manufacturer": "Schaeffler Group", "brand": "FAG", "normalized_name": "fag"},
    {"manufacturer": "Schaeffler Group", "brand": "INA", "normalized_name": "ina"},
    {"manufacturer": "The Timken Company", "brand": "TIMKEN", "normalized_name": "timken"},
    {"manufacturer": "NTN Corporation", "brand": "NTN", "normalized_name": "ntn"},
    {"manufacturer": "Nachi-Fujikoshi Corp.", "brand": "NACHI", "normalized_name": "nachi"},
    # Motors
    {"manufacturer": "ABB Ltd.", "brand": "ABB", "normalized_name": "abb"},
    {"manufacturer": "Siemens AG", "brand": "SIEMENS", "normalized_name": "siemens"},
    {"manufacturer": "WEG S.A.", "brand": "WEG", "normalized_name": "weg"},
    {"manufacturer": "Nidec Corporation", "brand": "NIDEC", "normalized_name": "nidec"},
    {"manufacturer": "Baldor Electric Company", "brand": "BALDOR", "normalized_name": "baldor"},
    {"manufacturer": "Regal Rexnord", "brand": "MARATHON", "normalized_name": "marathon"},
    # Pumps
    {"manufacturer": "Grundfos A/S", "brand": "GRUNDFOS", "normalized_name": "grundfos"},
    {"manufacturer": "Xylem Inc.", "brand": "XYLEM", "normalized_name": "xylem"},
    {"manufacturer": "Flowserve Corporation", "brand": "FLOWSERVE", "normalized_name": "flowserve"},
    {"manufacturer": "KSB SE & Co.", "brand": "KSB", "normalized_name": "ksb"},
    {"manufacturer": "Sulzer Ltd.", "brand": "SULZER", "normalized_name": "sulzer"},
    # Valves
    {"manufacturer": "Emerson Electric", "brand": "EMERSON", "normalized_name": "emerson"},
    {"manufacturer": "Emerson Electric", "brand": "FISHER", "normalized_name": "fisher"},
    {"manufacturer": "Honeywell International", "brand": "HONEYWELL", "normalized_name": "honeywell"},
    {"manufacturer": "Flowserve Corporation", "brand": "VALTEK", "normalized_name": "valtek"},
    {"manufacturer": "IMI plc", "brand": "IMI", "normalized_name": "imi"},
    # Sensors
    {"manufacturer": "TE Connectivity", "brand": "TE", "normalized_name": "te"},
    {"manufacturer": "Omega Engineering", "brand": "OMEGA", "normalized_name": "omega"},
    {"manufacturer": "Endress+Hauser", "brand": "ENDRESS+HAUSER", "normalized_name": "endress+hauser"},
    {"manufacturer": "SICK AG", "brand": "SICK", "normalized_name": "sick"},
    {"manufacturer": "IFM Electronic", "brand": "IFM", "normalized_name": "ifm"},
    # Electrical Components
    {"manufacturer": "Schneider Electric", "brand": "SCHNEIDER", "normalized_name": "schneider"},
    {"manufacturer": "Eaton Corporation", "brand": "EATON", "normalized_name": "eaton"},
    {"manufacturer": "ABB Ltd.", "brand": "ABB ELECTRIFICATION", "normalized_name": "abb electrification"},
    # Fasteners
    {"manufacturer": "Hilti Corporation", "brand": "HILTI", "normalized_name": "hilti"},
    {"manufacturer": "Fastenal Company", "brand": "FASTENAL", "normalized_name": "fastenal"},
    {"manufacturer": "Nord-Lock Group", "brand": "NORD-LOCK", "normalized_name": "nord-lock"},
    # Hydraulics / Pneumatics
    {"manufacturer": "Parker Hannifin", "brand": "PARKER", "normalized_name": "parker"},
    {"manufacturer": "Bosch Rexroth", "brand": "REXROTH", "normalized_name": "rexroth"},
    {"manufacturer": "SMC Corporation", "brand": "SMC", "normalized_name": "smc"},
    {"manufacturer": "Festo SE & Co.", "brand": "FESTO", "normalized_name": "festo"},
    # HVAC
    {"manufacturer": "Daikin Industries", "brand": "DAIKIN", "normalized_name": "daikin"},
    {"manufacturer": "Carrier Global", "brand": "CARRIER", "normalized_name": "carrier"},
    {"manufacturer": "Trane Technologies", "brand": "TRANE", "normalized_name": "trane"},
    # Automotive
    {"manufacturer": "Robert Bosch GmbH", "brand": "BOSCH", "normalized_name": "bosch"},
    {"manufacturer": "Denso Corporation", "brand": "DENSO", "normalized_name": "denso"},
    {"manufacturer": "Continental AG", "brand": "CONTINENTAL", "normalized_name": "continental"},
    # Safety Equipment
    {"manufacturer": "3M Company", "brand": "3M", "normalized_name": "3m"},
    {"manufacturer": "Honeywell Safety Products", "brand": "HONEYWELL SAFETY", "normalized_name": "honeywell safety"},
    {"manufacturer": "MSA Safety", "brand": "MSA", "normalized_name": "msa"},
    # Industrial Automation
    {"manufacturer": "Rockwell Automation", "brand": "ALLEN-BRADLEY", "normalized_name": "allen-bradley"},
    {"manufacturer": "Mitsubishi Electric", "brand": "MITSUBISHI", "normalized_name": "mitsubishi"},
    {"manufacturer": "Omron Corporation", "brand": "OMRON", "normalized_name": "omron"},
    # Power Equipment
    {"manufacturer": "Caterpillar Inc.", "brand": "CAT", "normalized_name": "cat"},
    {"manufacturer": "Cummins Inc.", "brand": "CUMMINS", "normalized_name": "cummins"},
    # Construction
    {"manufacturer": "DeWalt", "brand": "DEWALT", "normalized_name": "dewalt"},
    {"manufacturer": "Makita Corporation", "brand": "MAKITA", "normalized_name": "makita"},
    {"manufacturer": "Milwaukee Tool", "brand": "MILWAUKEE", "normalized_name": "milwaukee"},
]

# ---------------------------------------------------------------------------
# MULTI-INDUSTRY LIST OF VALUES (LOV)
# ---------------------------------------------------------------------------
INITIAL_LOVS = [
    # Bearings
    {"taxonomy_category": "Bearings", "attribute_name": "Seal Type", "allowed_value": "2RS1", "remarks": "Rubber seal on both sides"},
    {"taxonomy_category": "Bearings", "attribute_name": "Seal Type", "allowed_value": "ZZ", "remarks": "Metal shield on both sides"},
    {"taxonomy_category": "Bearings", "attribute_name": "Seal Type", "allowed_value": "Open", "remarks": "No seals"},
    {"taxonomy_category": "Bearings", "attribute_name": "Cage Material", "allowed_value": "Steel", "remarks": "Standard pressed steel cage"},
    {"taxonomy_category": "Bearings", "attribute_name": "Cage Material", "allowed_value": "Brass", "remarks": "Machined brass cage"},
    {"taxonomy_category": "Bearings", "attribute_name": "Cage Material", "allowed_value": "Polyamide", "remarks": "Glass fiber reinforced polyamide cage"},
    {"taxonomy_category": "Bearings", "attribute_name": "Internal Clearance", "allowed_value": "C3", "remarks": "Greater than normal clearance"},
    {"taxonomy_category": "Bearings", "attribute_name": "Internal Clearance", "allowed_value": "CN", "remarks": "Normal clearance"},
    # Motors
    {"taxonomy_category": "Motors", "attribute_name": "Enclosure Rating", "allowed_value": "TEFC", "remarks": "Totally Enclosed Fan Cooled"},
    {"taxonomy_category": "Motors", "attribute_name": "Enclosure Rating", "allowed_value": "ODP", "remarks": "Open Drip Proof"},
    {"taxonomy_category": "Motors", "attribute_name": "Enclosure Rating", "allowed_value": "TENV", "remarks": "Totally Enclosed Non-Ventilated"},
    {"taxonomy_category": "Motors", "attribute_name": "Enclosure Rating", "allowed_value": "TEAO", "remarks": "Totally Enclosed Air Over"},
    {"taxonomy_category": "Motors", "attribute_name": "Frame Size", "allowed_value": "NEMA 56", "remarks": "NEMA standard frame"},
    {"taxonomy_category": "Motors", "attribute_name": "Frame Size", "allowed_value": "IEC 90", "remarks": "IEC standard frame"},
    {"taxonomy_category": "Motors", "attribute_name": "Efficiency Class", "allowed_value": "IE1", "remarks": "Standard efficiency"},
    {"taxonomy_category": "Motors", "attribute_name": "Efficiency Class", "allowed_value": "IE2", "remarks": "High efficiency"},
    {"taxonomy_category": "Motors", "attribute_name": "Efficiency Class", "allowed_value": "IE3", "remarks": "Premium efficiency"},
    {"taxonomy_category": "Motors", "attribute_name": "Efficiency Class", "allowed_value": "IE4", "remarks": "Super premium efficiency"},
    # Pumps
    {"taxonomy_category": "Pumps", "attribute_name": "Pump Type", "allowed_value": "Centrifugal", "remarks": "Rotodynamic pump"},
    {"taxonomy_category": "Pumps", "attribute_name": "Pump Type", "allowed_value": "Positive Displacement", "remarks": "Volumetric pump"},
    {"taxonomy_category": "Pumps", "attribute_name": "Pump Type", "allowed_value": "Submersible", "remarks": "Submerged operation pump"},
    {"taxonomy_category": "Pumps", "attribute_name": "Seal Type", "allowed_value": "Mechanical Seal", "remarks": "Standard mechanical seal"},
    {"taxonomy_category": "Pumps", "attribute_name": "Seal Type", "allowed_value": "Packed Gland", "remarks": "Traditional packing seal"},
    # Valves
    {"taxonomy_category": "Valves", "attribute_name": "Valve Type", "allowed_value": "Gate", "remarks": "Linear motion isolation valve"},
    {"taxonomy_category": "Valves", "attribute_name": "Valve Type", "allowed_value": "Globe", "remarks": "Linear motion throttling valve"},
    {"taxonomy_category": "Valves", "attribute_name": "Valve Type", "allowed_value": "Ball", "remarks": "Quarter-turn valve"},
    {"taxonomy_category": "Valves", "attribute_name": "Valve Type", "allowed_value": "Butterfly", "remarks": "Quarter-turn valve"},
    {"taxonomy_category": "Valves", "attribute_name": "Valve Type", "allowed_value": "Check", "remarks": "Non-return valve"},
    {"taxonomy_category": "Valves", "attribute_name": "End Connection", "allowed_value": "Flanged", "remarks": "Bolted flange connection"},
    {"taxonomy_category": "Valves", "attribute_name": "End Connection", "allowed_value": "Threaded", "remarks": "NPT/BSP threaded"},
    {"taxonomy_category": "Valves", "attribute_name": "End Connection", "allowed_value": "Welded", "remarks": "Butt-weld or socket-weld"},
    # Sensors
    {"taxonomy_category": "Sensors", "attribute_name": "Sensor Type", "allowed_value": "RTD", "remarks": "Resistance Temperature Detector"},
    {"taxonomy_category": "Sensors", "attribute_name": "Sensor Type", "allowed_value": "Thermocouple", "remarks": "Thermoelectric sensor"},
    {"taxonomy_category": "Sensors", "attribute_name": "Sensor Type", "allowed_value": "Pressure Transducer", "remarks": "Pressure measurement sensor"},
    {"taxonomy_category": "Sensors", "attribute_name": "Sensor Type", "allowed_value": "Proximity", "remarks": "Inductive/capacitive proximity sensor"},
    {"taxonomy_category": "Sensors", "attribute_name": "Output Signal", "allowed_value": "4-20 mA", "remarks": "Analog current loop"},
    {"taxonomy_category": "Sensors", "attribute_name": "Output Signal", "allowed_value": "0-10 V", "remarks": "Analog voltage"},
    {"taxonomy_category": "Sensors", "attribute_name": "Output Signal", "allowed_value": "HART", "remarks": "Highway Addressable Remote Transducer"},
    # Fasteners
    {"taxonomy_category": "Fasteners", "attribute_name": "Fastener Type", "allowed_value": "Hex Bolt", "remarks": "Standard hexagonal bolt"},
    {"taxonomy_category": "Fasteners", "attribute_name": "Fastener Type", "allowed_value": "Socket Head Cap Screw", "remarks": "Allen bolt"},
    {"taxonomy_category": "Fasteners", "attribute_name": "Grade", "allowed_value": "8.8", "remarks": "Medium carbon steel, quenched and tempered"},
    {"taxonomy_category": "Fasteners", "attribute_name": "Grade", "allowed_value": "10.9", "remarks": "Alloy steel, quenched and tempered"},
    {"taxonomy_category": "Fasteners", "attribute_name": "Grade", "allowed_value": "12.9", "remarks": "Alloy steel, quenched and tempered"},
    # HVAC
    {"taxonomy_category": "HVAC", "attribute_name": "System Type", "allowed_value": "Split System", "remarks": "Indoor/outdoor split"},
    {"taxonomy_category": "HVAC", "attribute_name": "System Type", "allowed_value": "VRF", "remarks": "Variable Refrigerant Flow"},
    {"taxonomy_category": "HVAC", "attribute_name": "Refrigerant", "allowed_value": "R-410A", "remarks": "HFC blend"},
    {"taxonomy_category": "HVAC", "attribute_name": "Refrigerant", "allowed_value": "R-32", "remarks": "Lower GWP refrigerant"},
    # Safety Equipment
    {"taxonomy_category": "Safety Equipment", "attribute_name": "Protection Class", "allowed_value": "EN 388", "remarks": "Mechanical risks protection"},
    {"taxonomy_category": "Safety Equipment", "attribute_name": "Protection Class", "allowed_value": "EN 166", "remarks": "Eye protection"},
    {"taxonomy_category": "Safety Equipment", "attribute_name": "Protection Class", "allowed_value": "EN 352", "remarks": "Hearing protection"},
    # Electrical Components
    {"taxonomy_category": "Electrical Components", "attribute_name": "Component Type", "allowed_value": "Circuit Breaker", "remarks": "Overcurrent protection device"},
    {"taxonomy_category": "Electrical Components", "attribute_name": "Component Type", "allowed_value": "Contactor", "remarks": "Electrically controlled switch"},
    {"taxonomy_category": "Electrical Components", "attribute_name": "Component Type", "allowed_value": "Relay", "remarks": "Electromechanical switch"},
    {"taxonomy_category": "Electrical Components", "attribute_name": "Voltage Rating", "allowed_value": "240V AC", "remarks": "Single phase"},
    {"taxonomy_category": "Electrical Components", "attribute_name": "Voltage Rating", "allowed_value": "415V AC", "remarks": "Three phase"},
    # Industrial Automation
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Controller Type", "allowed_value": "PLC", "remarks": "Programmable Logic Controller"},
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Controller Type", "allowed_value": "DCS", "remarks": "Distributed Control System"},
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Controller Type", "allowed_value": "SCADA", "remarks": "Supervisory Control and Data Acquisition"},
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Communication", "allowed_value": "Modbus", "remarks": "Serial communication protocol"},
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Communication", "allowed_value": "Profibus", "remarks": "Process field bus"},
    {"taxonomy_category": "Industrial Automation", "attribute_name": "Communication", "allowed_value": "EtherNet/IP", "remarks": "Industrial Ethernet protocol"},
]

# ---------------------------------------------------------------------------
# MULTI-INDUSTRY UNIT OF MEASURE (UOM)
# ---------------------------------------------------------------------------
INITIAL_UOMS = [
    # Length
    {"standard_unit": "Millimeter", "abbreviation": "mm", "allowed_synonyms": ["mm", "millimetre", "millimeters", "millimetres"], "conversion_factor": 1.0},
    {"standard_unit": "Centimeter", "abbreviation": "cm", "allowed_synonyms": ["cm", "centimeter", "centimetre"], "conversion_factor": 10.0},
    {"standard_unit": "Meter", "abbreviation": "m", "allowed_synonyms": ["m", "meter", "metre", "meters", "metres"], "conversion_factor": 1000.0},
    {"standard_unit": "Inch", "abbreviation": "in", "allowed_synonyms": ["in", "\"", "inch", "inches"], "conversion_factor": 25.4},
    {"standard_unit": "Foot", "abbreviation": "ft", "allowed_synonyms": ["ft", "foot", "feet"], "conversion_factor": 304.8},
    # Mass
    {"standard_unit": "Kilogram", "abbreviation": "kg", "allowed_synonyms": ["kg", "kilo", "kilograms"], "conversion_factor": 1.0},
    {"standard_unit": "Gram", "abbreviation": "g", "allowed_synonyms": ["g", "gram", "grams"], "conversion_factor": 0.001},
    {"standard_unit": "Pound", "abbreviation": "lb", "allowed_synonyms": ["lb", "lbs", "pound", "pounds"], "conversion_factor": 0.453592},
    {"standard_unit": "Ounce", "abbreviation": "oz", "allowed_synonyms": ["oz", "ounce", "ounces"], "conversion_factor": 0.0283495},
    # Force
    {"standard_unit": "Newton", "abbreviation": "N", "allowed_synonyms": ["N", "newton", "newtons"], "conversion_factor": 1.0},
    {"standard_unit": "Kilonewton", "abbreviation": "kN", "allowed_synonyms": ["kN", "kilonewton"], "conversion_factor": 1000.0},
    # Pressure
    {"standard_unit": "Pascal", "abbreviation": "Pa", "allowed_synonyms": ["Pa", "pascal"], "conversion_factor": 1.0},
    {"standard_unit": "Kilopascal", "abbreviation": "kPa", "allowed_synonyms": ["kPa", "kilopascal"], "conversion_factor": 1000.0},
    {"standard_unit": "Megapascal", "abbreviation": "MPa", "allowed_synonyms": ["MPa", "megapascal"], "conversion_factor": 1000000.0},
    {"standard_unit": "Bar", "abbreviation": "bar", "allowed_synonyms": ["bar", "bars"], "conversion_factor": 100000.0},
    {"standard_unit": "Pounds per Square Inch", "abbreviation": "psi", "allowed_synonyms": ["psi", "PSI", "lb/in²"], "conversion_factor": 6894.76},
    # Temperature
    {"standard_unit": "Celsius", "abbreviation": "°C", "allowed_synonyms": ["°C", "C", "deg C", "celsius"], "conversion_factor": 1.0},
    {"standard_unit": "Fahrenheit", "abbreviation": "°F", "allowed_synonyms": ["°F", "F", "deg F", "fahrenheit"], "conversion_factor": 1.0},
    {"standard_unit": "Kelvin", "abbreviation": "K", "allowed_synonyms": ["K", "kelvin"], "conversion_factor": 1.0},
    # Electrical
    {"standard_unit": "Volt", "abbreviation": "V", "allowed_synonyms": ["V", "volt", "volts"], "conversion_factor": 1.0},
    {"standard_unit": "Ampere", "abbreviation": "A", "allowed_synonyms": ["A", "amp", "amps", "ampere"], "conversion_factor": 1.0},
    {"standard_unit": "Milliampere", "abbreviation": "mA", "allowed_synonyms": ["mA", "milliamp", "milliampere"], "conversion_factor": 0.001},
    {"standard_unit": "Watt", "abbreviation": "W", "allowed_synonyms": ["W", "watt", "watts"], "conversion_factor": 1.0},
    {"standard_unit": "Kilowatt", "abbreviation": "kW", "allowed_synonyms": ["kW", "kilowatt", "kilowatts"], "conversion_factor": 1000.0},
    {"standard_unit": "Horsepower", "abbreviation": "HP", "allowed_synonyms": ["HP", "hp", "horsepower"], "conversion_factor": 745.7},
    {"standard_unit": "Ohm", "abbreviation": "Ω", "allowed_synonyms": ["Ω", "ohm", "ohms"], "conversion_factor": 1.0},
    {"standard_unit": "Hertz", "abbreviation": "Hz", "allowed_synonyms": ["Hz", "hertz"], "conversion_factor": 1.0},
    {"standard_unit": "Kilohertz", "abbreviation": "kHz", "allowed_synonyms": ["kHz", "kilohertz"], "conversion_factor": 1000.0},
    # Rotational
    {"standard_unit": "Revolutions Per Minute", "abbreviation": "rpm", "allowed_synonyms": ["rpm", "RPM", "r/min"], "conversion_factor": 1.0},
    # Torque
    {"standard_unit": "Newton Meter", "abbreviation": "Nm", "allowed_synonyms": ["Nm", "N-m", "N·m", "newton meter", "newton metre"], "conversion_factor": 1.0},
    # Flow
    {"standard_unit": "Liters Per Minute", "abbreviation": "L/min", "allowed_synonyms": ["L/min", "LPM", "lpm", "l/min"], "conversion_factor": 1.0},
    {"standard_unit": "Gallons Per Minute", "abbreviation": "GPM", "allowed_synonyms": ["GPM", "gpm", "gal/min"], "conversion_factor": 3.78541},
    {"standard_unit": "Cubic Meters Per Hour", "abbreviation": "m³/h", "allowed_synonyms": ["m³/h", "m3/h", "cmh"], "conversion_factor": 16.6667},
    # Volume
    {"standard_unit": "Liter", "abbreviation": "L", "allowed_synonyms": ["L", "l", "liter", "litre", "liters", "litres"], "conversion_factor": 1.0},
    # Sound
    {"standard_unit": "Decibel", "abbreviation": "dB", "allowed_synonyms": ["dB", "decibel", "decibels"], "conversion_factor": 1.0},
    # Light
    {"standard_unit": "Lux", "abbreviation": "lx", "allowed_synonyms": ["lx", "lux"], "conversion_factor": 1.0},
    # Ingress Protection
    {"standard_unit": "IP Rating", "abbreviation": "IP", "allowed_synonyms": ["IP", "ip"], "conversion_factor": 1.0},
]

INITIAL_DECIMAL_FRACTIONS = [
    {"fraction": "1/16", "decimal_value": 0.0625, "standard_representation": "0.0625 in"},
    {"fraction": "1/8", "decimal_value": 0.125, "standard_representation": "0.125 in"},
    {"fraction": "3/16", "decimal_value": 0.1875, "standard_representation": "0.1875 in"},
    {"fraction": "1/4", "decimal_value": 0.25, "standard_representation": "0.250 in"},
    {"fraction": "5/16", "decimal_value": 0.3125, "standard_representation": "0.3125 in"},
    {"fraction": "3/8", "decimal_value": 0.375, "standard_representation": "0.375 in"},
    {"fraction": "7/16", "decimal_value": 0.4375, "standard_representation": "0.4375 in"},
    {"fraction": "1/2", "decimal_value": 0.5, "standard_representation": "0.500 in"},
    {"fraction": "9/16", "decimal_value": 0.5625, "standard_representation": "0.5625 in"},
    {"fraction": "5/8", "decimal_value": 0.625, "standard_representation": "0.625 in"},
    {"fraction": "11/16", "decimal_value": 0.6875, "standard_representation": "0.6875 in"},
    {"fraction": "3/4", "decimal_value": 0.75, "standard_representation": "0.750 in"},
    {"fraction": "13/16", "decimal_value": 0.8125, "standard_representation": "0.8125 in"},
    {"fraction": "7/8", "decimal_value": 0.875, "standard_representation": "0.875 in"},
    {"fraction": "15/16", "decimal_value": 0.9375, "standard_representation": "0.9375 in"},
    {"fraction": "1", "decimal_value": 1.0, "standard_representation": "1.000 in"},
]

def seed_official_knowledge(db: Session):
    """
    Populates official controlled knowledge if missing.
    Covers multiple industrial/commercial domains — NOT bearing-specific.
    """
    if db.query(OfficialManufacturerBrand).count() == 0:
        logger.info("Seeding Official Manufacturer & Brand Master (multi-industry)...")
        for item in INITIAL_MANUFACTURER_BRANDS:
            db.add(OfficialManufacturerBrand(**item))

    if db.query(OfficialLOV).count() == 0:
        logger.info("Seeding Official LOV Master (multi-industry)...")
        for item in INITIAL_LOVS:
            db.add(OfficialLOV(**item))

    if db.query(OfficialUOM).count() == 0:
        logger.info("Seeding Official UOM Master (multi-industry)...")
        for item in INITIAL_UOMS:
            db.add(OfficialUOM(**item))

    if db.query(OfficialDecimalFraction).count() == 0:
        logger.info("Seeding Official Decimal / Fraction Master...")
        for item in INITIAL_DECIMAL_FRACTIONS:
            db.add(OfficialDecimalFraction(**item))

    db.commit()
    logger.info("Official controlled knowledge seeding complete (multi-industry).")
