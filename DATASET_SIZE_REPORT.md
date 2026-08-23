# DATASET SIZE REPORT

This document summarizes the size footprint of the offline knowledge corpus on the filesystem and in the vector database.

- **Total Acquired Corpus Size:** 16,403,274 bytes (~16 MB)
- **Target Limit:** 2,147,483,648 bytes (2 GB)
- **Usage Percent:** 0.76%

*Note: The total size is significantly below the 2 GB limit because Wikipedia and Wikidata acquisitions failed due to HTTP 429 Too Many Requests.*

## Size Breakdown by Dataset

| Dataset | Size (Bytes) |
|---|---|
| North American Industry Classification System 2022 | 5,249,110 |
| QUDT Units and Quantity Kinds | 5,095,847 |
| ENERGY STAR Certified Light Commercial HVAC | 4,496,119 |
| ENERGY STAR Certified Ventilating Fans | 421,997 |
| ENERGY STAR Certified Electric Vehicle Supply Equipment - DC-Output | 389,165 |
| ENERGY STAR Certified Electric Vehicle Supply Equipment - AC-Output | 351,514 |
| ENERGY STAR Certified Data Center Storage - File I/O | 171,368 |
| ENERGY STAR Certified Commercial Boilers | 124,314 |
| **Total** | **16,299,434** (Data only) |

The total filesystem footprint, including manifest and auditing files, is 16,403,274 bytes.
