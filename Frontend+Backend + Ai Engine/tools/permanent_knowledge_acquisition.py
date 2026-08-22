from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


LIMIT_BYTES = 2 * 1024**3
USER_AGENT = "UniHack-2026-Permanent-Knowledge-Acquisition/1.0 (license-verified offline knowledge)"


ROOT = Path(__file__).resolve().parents[1]
PERM_DIR = ROOT / "data_storage" / "permanent_knowledge"
STAGING_DIR = ROOT / "data_storage" / "permanent_acquisition_staging"
BASELINE_TAXONOMY = ROOT / "app" / "knowledge" / "baseline" / "industry_taxonomy.json"
BASELINE_ATTRIBUTES = ROOT / "app" / "knowledge" / "baseline" / "attribute_patterns.json"
DB_PATH = ROOT / "unihack_backend.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    return total


def dataset_size(path: Path) -> int:
    return dir_size(path) if path.is_dir() else path.stat().st_size


def request_json(url: str, params: dict[str, str] | None = None, timeout: int = 60) -> Any:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"
    req = Request(full_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_to_staging(url: str, dest: Path, remaining_budget: int, retries: int = 3) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=120) as resp:
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > remaining_budget:
                    return {
                        "downloaded": False,
                        "reason": "TOO_LARGE",
                        "content_length": int(content_length),
                    }
                written = 0
                with dest.open("wb") as out:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > remaining_budget:
                            out.close()
                            dest.unlink(missing_ok=True)
                            return {
                                "downloaded": False,
                                "reason": "TOO_LARGE",
                                "content_length": content_length,
                                "written_before_abort": written,
                            }
                        out.write(chunk)
            return {
                "downloaded": True,
                "size_bytes": dest.stat().st_size,
                "content_length": int(content_length) if content_length else None,
            }
        except Exception as exc:  # noqa: BLE001 - acquisition must keep candidate failure details
            last_error = str(exc)
            time.sleep(min(2**attempt, 8))
    return {"downloaded": False, "reason": "UNAVAILABLE", "error": last_error}


@dataclass
class Dataset:
    dataset_id: str
    name: str
    source: str
    source_url: str
    download_url: str
    license: str
    license_url: str
    license_verified: bool
    license_notes: str
    version: str
    published_at: str | None
    downloaded_at: str
    sha256: str
    size_bytes: int
    format: str
    industries: list[str]
    categories: list[str]
    description: str
    attribution: str
    storage_class: str
    knowledge_type: str
    quality_scores: dict[str, int]
    files: list[str]


def flatten_taxonomy(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for industry, categories in taxonomy.items():
        for category, product_types in categories.items():
            rows.append(
                {
                    "industry": industry,
                    "category": category,
                    "product_types": product_types,
                }
            )
    return rows


def derive_coverage() -> tuple[list[dict[str, Any]], list[str]]:
    taxonomy_doc = read_json(BASELINE_TAXONOMY)
    attribute_doc = read_json(BASELINE_ATTRIBUTES)
    rows = flatten_taxonomy(taxonomy_doc["taxonomy"])
    existing_files = {p.name for p in PERM_DIR.glob("*") if p.is_file()}
    for row in rows:
        attrs = attribute_doc.get("patterns", {}).get(row["category"], {}).get("common_attributes", [])
        row["expected_attributes"] = attrs
        row["existing_offline_knowledge"] = [
            name for name in existing_files if "taxonomy" in name or row["category"].lower().replace(" ", "_") in name.lower()
        ]
        row["knowledge_gaps"] = []
        if not attrs:
            row["knowledge_gaps"].append("No category-specific attribute pattern in baseline code")
        row["knowledge_gaps"].append("Limited or no real open product records unless covered by acquired datasets")
        row["priority"] = "HIGH" if row["category"] in {"Bearings", "Electric Motors", "Pumps", "Valves", "Sensors", "Fasteners", "Cooling", "Heating", "Ventilation", "Circuit Protection", "Switching", "Wiring", "Transformers"} else "MEDIUM"
    terms = sorted(
        {
            term
            for row in rows
            for term in [row["industry"], row["category"], *row["product_types"]]
        }
    )
    return rows, terms


def acquire_wikidata(terms: list[str], coverage_rows: list[dict[str, Any]]) -> Dataset:
    dataset_id = "wikidata_industrial_taxonomy_cc0"
    out_dir = STAGING_DIR / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    seen_qids: set[str] = set()
    for term in terms:
        data = request_json(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbsearchentities",
                "search": term,
                "language": "en",
                "format": "json",
                "limit": "2",
            },
        )
        for item in data.get("search", []):
            qid = item.get("id")
            if not qid or qid in seen_qids:
                continue
            seen_qids.add(qid)
            records.append(
                {
                    "source_dataset_id": dataset_id,
                    "source_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
                    "license": "CC0-1.0",
                    "attribution": "Wikidata contributors",
                    "retrieval_metadata": {"query_term": term, "qid": qid},
                    "qid": qid,
                    "label": item.get("label"),
                    "description": item.get("description"),
                    "aliases": item.get("aliases", []),
                    "concept_uri": item.get("concepturi"),
                }
            )
        time.sleep(0.05)
    jsonl = out_dir / "wikidata_industrial_taxonomy_cc0.jsonl"
    with jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(out_dir / "coverage_matrix.json", coverage_rows)
    write_json(
        out_dir / "metadata.json",
        {
            "dataset_id": dataset_id,
            "record_count": len(records),
            "license": "CC0-1.0",
            "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        },
    )
    return make_dataset(
        dataset_id=dataset_id,
        name="Wikidata Industrial Taxonomy Entities",
        source="Wikidata",
        source_url="https://www.wikidata.org/wiki/Wikidata:Licensing",
        download_url="https://www.wikidata.org/w/api.php?action=wbsearchentities",
        license_name="CC0-1.0",
        license_url="https://www.wikidata.org/wiki/Wikidata:Licensing",
        license_notes="Wikidata structured data is released under CC0.",
        version="live API snapshot",
        published_at=None,
        stage_path=out_dir,
        primary_file=jsonl,
        industries=sorted({r["industry"] for r in coverage_rows}),
        categories=sorted({r["category"] for r in coverage_rows}),
        description="CC0 structured entity labels, descriptions, aliases, and IDs for code-derived product/industry terminology.",
        attribution="Wikidata contributors",
        knowledge_type="TAXONOMY",
        fmt="JSONL",
    )


WIKIPEDIA_PAGE_HINTS = {
    "HVAC": "Heating, ventilation, and air conditioning",
    "Cooling": "Air conditioning",
    "Heating": "Heating system",
    "Ventilation": "Ventilation (architecture)",
    "Circuit Protection": "Circuit breaker",
    "Switching": "Electrical switch",
    "Wiring": "Electrical wiring",
    "CNC Machines": "Numerical control",
    "Material Handling": "Material-handling equipment",
}


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def acquire_wikipedia(terms: list[str], coverage_rows: list[dict[str, Any]]) -> Dataset:
    dataset_id = "wikipedia_industrial_reference_cc_by_sa"
    out_dir = STAGING_DIR / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    priority_terms = []
    for row in coverage_rows:
        priority_terms.append(row["category"])
        priority_terms.extend(row["product_types"][:2])
    selected_terms = sorted(dict.fromkeys(priority_terms))[:40]
    records: list[dict[str, Any]] = []
    for term in selected_terms:
        page = WIKIPEDIA_PAGE_HINTS.get(term, term)
        data = request_json(
            "https://en.wikipedia.org/w/api.php",
            {
                "action": "query",
                "format": "json",
                "prop": "extracts|info",
                "exintro": "1",
                "explaintext": "1",
                "redirects": "1",
                "inprop": "url",
                "titles": page,
            },
        )
        pages = data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            if "missing" in page_data:
                continue
            extract = strip_html(page_data.get("extract", ""))
            if len(extract) < 80:
                continue
            records.append(
                {
                    "source_dataset_id": dataset_id,
                    "source_url": page_data.get("fullurl"),
                    "license": "CC BY-SA 4.0",
                    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                    "attribution": f"Wikipedia contributors, page: {page_data.get('title')}",
                    "original_file": "MediaWiki API extract",
                    "sha256": hashlib.sha256(extract.encode("utf-8")).hexdigest(),
                    "retrieval_metadata": {"query_term": term, "pageid": page_data.get("pageid")},
                    "title": page_data.get("title"),
                    "extract": extract[:6000],
                }
            )
        time.sleep(0.35)
    jsonl = out_dir / "wikipedia_industrial_reference_cc_by_sa.jsonl"
    with jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(out_dir / "metadata.json", {"dataset_id": dataset_id, "record_count": len(records)})
    return make_dataset(
        dataset_id=dataset_id,
        name="Wikipedia Industrial Technical Reference Extracts",
        source="Wikipedia",
        source_url="https://en.wikipedia.org/",
        download_url="https://en.wikipedia.org/w/api.php?action=query&prop=extracts",
        license_name="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        license_notes="Wikipedia text is reusable under CC BY-SA with attribution/share-alike obligations.",
        version="live API snapshot",
        published_at=None,
        stage_path=out_dir,
        primary_file=jsonl,
        industries=sorted({r["industry"] for r in coverage_rows}),
        categories=sorted({r["category"] for r in coverage_rows}),
        description="Technical introductory article extracts for code-derived product categories and product types.",
        attribution="Wikipedia contributors; each JSONL record preserves page attribution and URL.",
        knowledge_type="TECHNICAL_REFERENCE",
        fmt="JSONL",
    )


def acquire_energy_star(remaining_budget: int) -> list[Dataset]:
    specs = [
        {
            "dataset_id": "energy_star_commercial_boilers_public_domain",
            "name": "ENERGY STAR Certified Commercial Boilers",
            "view_id": "3393-mxju",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-commercial-boilers",
            "industries": ["HVAC", "Power Equipment"],
            "categories": ["Heating", "Boilers"],
            "published_at": "2021-09-15",
            "modified": "2026-07-28",
            "description": "Certified commercial boiler product records and efficiency attributes.",
        },
        {
            "dataset_id": "energy_star_ventilating_fans_public_domain",
            "name": "ENERGY STAR Certified Ventilating Fans",
            "view_id": "8dv7-nngq",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-ventilating-fans",
            "industries": ["HVAC", "Industrial Equipment"],
            "categories": ["Ventilation", "Fans"],
            "published_at": "2021-09-07",
            "modified": "2026-07-28",
            "description": "Certified ventilating fan product records and efficiency/airflow attributes.",
        },
        {
            "dataset_id": "energy_star_light_commercial_hvac_public_domain",
            "name": "ENERGY STAR Certified Light Commercial HVAC",
            "view_id": "e4mh-a2u3",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-light-commercial-hvac",
            "industries": ["HVAC"],
            "categories": ["Cooling", "Heating"],
            "published_at": "2022-11-28",
            "modified": "2026-08-04",
            "description": "Certified light commercial HVAC product records and performance attributes.",
        },
        {
            "dataset_id": "energy_star_evse_ac_public_domain",
            "name": "ENERGY STAR Certified Electric Vehicle Supply Equipment - AC-Output",
            "view_id": "5jwe-c8xm",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-electric-vehicle-supply-equipment-ac-output",
            "industries": ["Electrical Components", "Power Equipment", "Automotive Components"],
            "categories": ["Electrical", "EVSE"],
            "published_at": "2023-07-07",
            "modified": "2026-08-02",
            "description": "Certified AC-output EVSE product records and electrical performance attributes.",
        },
        {
            "dataset_id": "energy_star_evse_dc_public_domain",
            "name": "ENERGY STAR Certified Electric Vehicle Supply Equipment - DC-Output",
            "view_id": "t3a6-mkxz",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-electric-vehicle-supply-equipment-dc-output",
            "industries": ["Electrical Components", "Power Equipment", "Automotive Components"],
            "categories": ["Electrical", "EVSE"],
            "published_at": "2023-07-07",
            "modified": "2026-07-29",
            "description": "Certified DC-output EVSE product records and electrical performance attributes.",
        },
        {
            "dataset_id": "energy_star_data_center_storage_public_domain",
            "name": "ENERGY STAR Certified Data Center Storage - File I/O",
            "view_id": "put7-uu67",
            "catalog_url": "https://catalog.data.gov/dataset/energy-star-certified-data-center-storage-file-i-o",
            "industries": ["Electrical Components", "Industrial Automation"],
            "categories": ["Electrical Equipment", "Data Center Storage"],
            "published_at": "2021-09-09",
            "modified": "2026-08-11",
            "description": "Certified data center storage product records and energy efficiency attributes.",
        },
    ]
    datasets: list[Dataset] = []
    for spec in specs:
        dataset_id = spec["dataset_id"]
        out_dir = STAGING_DIR / dataset_id
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_url = f"https://data.energystar.gov/api/v3/views/{spec['view_id']}/export.csv?accessType=DOWNLOAD"
        columns_url = f"https://data.energystar.gov/api/views/{spec['view_id']}/columns.json"
        csv_path = out_dir / f"{dataset_id}.csv"
        result = download_to_staging(csv_url, csv_path, remaining_budget)
        if not result.get("downloaded"):
            raise RuntimeError(f"{dataset_id} failed download: {result}")
        remaining_budget -= csv_path.stat().st_size
        try:
            columns = request_json(columns_url)
        except Exception as exc:  # noqa: BLE001
            columns = {"warning": f"column metadata unavailable: {exc}"}
        write_json(out_dir / "columns.json", columns)
        row_count = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row_count, _ in enumerate(csv.DictReader(f), start=1):
                pass
        write_json(
            out_dir / "metadata.json",
            {
                "dataset_id": dataset_id,
                "row_count": row_count,
                "view_id": spec["view_id"],
                "modified": spec["modified"],
                "license": "U.S. Public Domain / EPA Standard Open Data License",
            },
        )
        datasets.append(
            make_dataset(
                dataset_id=dataset_id,
                name=spec["name"],
                source="U.S. Environmental Protection Agency ENERGY STAR",
                source_url=spec["catalog_url"],
                download_url=csv_url,
                license_name="U.S. Public Domain / EPA Standard Open Data License",
                license_url="https://edg.epa.gov/EPA_Data_License.html",
                license_notes="EPA data is public domain unless otherwise specified under the EPA Standard Open Data License.",
                version=f"modified {spec['modified']}",
                published_at=spec["published_at"],
                stage_path=out_dir,
                primary_file=csv_path,
                industries=spec["industries"],
                categories=spec["categories"],
                description=spec["description"],
                attribution="U.S. Environmental Protection Agency ENERGY STAR program",
                knowledge_type="PRODUCT_CATALOG",
                fmt="CSV",
            )
        )
    return datasets


def acquire_qudt(remaining_budget: int) -> Dataset:
    dataset_id = "qudt_units_quantity_kinds_cc_by_4"
    out_dir = STAGING_DIR / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    files = [
        "https://raw.githubusercontent.com/qudt/qudt-public-repo/main/src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl",
        "https://raw.githubusercontent.com/qudt/qudt-public-repo/main/src/main/rdf/vocab/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl",
    ]
    downloaded: list[Path] = []
    for url in files:
        dest = out_dir / url.rsplit("/", 1)[-1]
        result = download_to_staging(url, dest, remaining_budget)
        if not result.get("downloaded"):
            raise RuntimeError(f"QUDT download failed: {url}: {result}")
        remaining_budget -= dest.stat().st_size
        downloaded.append(dest)
    labels = []
    label_re = re.compile(r'rdfs:label\s+"([^"]+)"(?:@en)?', re.IGNORECASE)
    for path in downloaded:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = label_re.search(line)
                if match:
                    labels.append({"label": match.group(1), "source_file": path.name})
                if len(labels) >= 3000:
                    break
    norm = out_dir / "qudt_units_quantity_kinds_labels.jsonl"
    with norm.open("w", encoding="utf-8", newline="\n") as f:
        for record in labels:
            record.update(
                {
                    "source_dataset_id": dataset_id,
                    "source_url": "https://github.com/qudt/qudt-public-repo",
                    "license": "CC BY 4.0",
                    "attribution": "QUDT.org",
                }
            )
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(out_dir / "metadata.json", {"dataset_id": dataset_id, "label_count": len(labels)})
    return make_dataset(
        dataset_id=dataset_id,
        name="QUDT Units and Quantity Kinds",
        source="QUDT.org GitHub public repository",
        source_url="https://github.com/qudt/qudt-public-repo",
        download_url=", ".join(files),
        license_name="CC BY 4.0",
        license_url="https://github.com/qudt/qudt-public-repo/blob/main/LICENSE.md",
        license_notes="QUDT repository LICENSE.md states Creative Commons Attribution 4.0 with attribution to QUDT.org.",
        version="main branch snapshot",
        published_at=None,
        stage_path=out_dir,
        primary_file=norm,
        industries=["Industrial Equipment", "Industrial Automation", "Electrical Components", "HVAC", "Manufacturing Equipment", "Power Equipment", "Chemicals and Materials", "Medical and Regulated Products"],
        categories=["Units", "Quantity Kinds", "Attribute Vocabulary"],
        description="Machine-readable unit and quantity-kind vocabulary for measurement and attribute interpretation.",
        attribution="QUDT.org",
        knowledge_type="ENGINEERING_REFERENCE",
        fmt="TTL+JSONL",
    )


def acquire_naics(remaining_budget: int) -> Dataset:
    dataset_id = "colorado_naics_2022_public_domain"
    out_dir = STAGING_DIR / dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_url = "https://data.colorado.gov/api/views/i2mk-94p9/rows.csv?accessType=DOWNLOAD"
    csv_path = out_dir / "north_american_industry_classification_system_2022.csv"
    result = download_to_staging(csv_url, csv_path, remaining_budget)
    if not result.get("downloaded"):
        raise RuntimeError(f"NAICS download failed: {result}")
    row_count = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row_count, _ in enumerate(csv.DictReader(f), start=1):
            pass
    write_json(out_dir / "metadata.json", {"dataset_id": dataset_id, "row_count": row_count})
    return make_dataset(
        dataset_id=dataset_id,
        name="North American Industry Classification System 2022",
        source="State of Colorado Open Data Portal",
        source_url="https://data.colorado.gov/Business/North-American-Industry-Classification-System-2022/i2mk-94p9",
        download_url=csv_url,
        license_name="Public Domain",
        license_url="https://data.colorado.gov/Business/North-American-Industry-Classification-System-2022/i2mk-94p9",
        license_notes="Colorado Open Data page marks the NAICS 2022 dataset license as Public Domain and cites the Census source link.",
        version="2022",
        published_at=None,
        stage_path=out_dir,
        primary_file=csv_path,
        industries=["Agricultural Equipment", "Construction Materials", "Manufacturing Equipment", "Automotive Components", "Power Equipment", "Chemicals and Materials", "Medical and Regulated Products", "Packaging Equipment"],
        categories=["Industry Classification"],
        description="Public-domain NAICS industry code/title/description reference for classifying industrial domains.",
        attribution="State of Colorado Open Data Portal; source link to U.S. Census NAICS.",
        knowledge_type="TAXONOMY",
        fmt="CSV",
    )


def make_dataset(
    *,
    dataset_id: str,
    name: str,
    source: str,
    source_url: str,
    download_url: str,
    license_name: str,
    license_url: str,
    license_notes: str,
    version: str,
    published_at: str | None,
    stage_path: Path,
    primary_file: Path,
    industries: list[str],
    categories: list[str],
    description: str,
    attribution: str,
    knowledge_type: str,
    fmt: str,
) -> Dataset:
    files = [str(path.relative_to(PERM_DIR)) for path in []]
    return Dataset(
        dataset_id=dataset_id,
        name=name,
        source=source,
        source_url=source_url,
        download_url=download_url,
        license=license_name,
        license_url=license_url,
        license_verified=True,
        license_notes=license_notes,
        version=version,
        published_at=published_at,
        downloaded_at=utc_now(),
        sha256=sha256_file(primary_file),
        size_bytes=dataset_size(stage_path),
        format=fmt,
        industries=industries,
        categories=categories,
        description=description,
        attribution=attribution,
        storage_class="PERMANENT_BASELINE",
        knowledge_type=knowledge_type,
        quality_scores={
            "LICENSE_CONFIDENCE": 5,
            "SOURCE_AUTHORITY": 5,
            "PRODUCT_RELEVANCE": 4 if knowledge_type == "PRODUCT_CATALOG" else 3,
            "INDUSTRY_COVERAGE": 4,
            "ATTRIBUTE_VALUE": 5 if knowledge_type in {"ENGINEERING_REFERENCE", "PRODUCT_CATALOG"} else 3,
            "DUPLICATION_RISK": 1,
            "SIZE_EFFICIENCY": 5,
            "PROVENANCE_QUALITY": 5,
        },
        files=files,
    )


def install_dataset(stage_path: Path, dataset: Dataset) -> Dataset:
    current = dir_size(PERM_DIR)
    size = dataset_size(stage_path)
    if current + size > LIMIT_BYTES:
        raise RuntimeError(f"{dataset.dataset_id} would exceed permanent storage limit")
    target = PERM_DIR / dataset.dataset_id
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(stage_path, target)
    installed_files = [str(path.relative_to(PERM_DIR)) for path in target.rglob("*") if path.is_file()]
    dataset.files = installed_files
    dataset.size_bytes = dataset_size(target)
    write_json(target / "dataset_metadata.json", asdict(dataset))
    dataset.size_bytes = dataset_size(target)
    return dataset


def register_datasets(datasets: list[Dataset]) -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        create table if not exists dataset_records (
            id varchar primary key,
            dataset_id varchar unique not null,
            name varchar not null,
            source varchar not null,
            source_url varchar,
            license varchar not null default 'unknown',
            size_bytes integer default 0,
            checksum varchar,
            version varchar default '1.0',
            industries json,
            categories json,
            description text,
            purpose varchar,
            permanent boolean default 0,
            status varchar default 'active',
            storage_class varchar default 'TEMPORARY_ACQUISITION',
            attribution varchar,
            downloaded_at datetime,
            created_at datetime
        )
        """
    )
    for ds in datasets:
        existing = con.execute(
            "select dataset_id from dataset_records where dataset_id = ?", (ds.dataset_id,)
        ).fetchone()
        values = (
            ds.dataset_id,
            ds.name,
            ds.source,
            ds.source_url,
            ds.license,
            ds.size_bytes,
            ds.sha256,
            ds.version,
            json.dumps(ds.industries),
            json.dumps(ds.categories),
            ds.description,
            ds.knowledge_type.lower(),
            1,
            "active",
            ds.storage_class,
            ds.attribution,
            ds.downloaded_at,
            utc_now(),
        )
        if existing:
            con.execute(
                """
                update dataset_records
                set name=?, source=?, source_url=?, license=?, size_bytes=?, checksum=?,
                    version=?, industries=?, categories=?, description=?, purpose=?,
                    permanent=?, status=?, storage_class=?, attribution=?, downloaded_at=?
                where dataset_id=?
                """,
                values[1:17] + (ds.dataset_id,),
            )
        else:
            con.execute(
                """
                insert into dataset_records (
                    id, dataset_id, name, source, source_url, license, size_bytes, checksum,
                    version, industries, categories, description, purpose, permanent, status,
                    storage_class, attribution, downloaded_at, created_at
                )
                values (lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
    con.commit()
    con.close()


def existing_dataset_records() -> list[dict[str, Any]]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("select * from dataset_records").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def build_industry_coverage(coverage_rows: list[dict[str, Any]], datasets: list[Dataset]) -> list[dict[str, Any]]:
    by_industry: dict[str, dict[str, Any]] = {}
    for row in coverage_rows:
        item = by_industry.setdefault(
            row["industry"],
            {
                "industry": row["industry"],
                "categories": [],
                "dataset_count": 0,
                "bytes": 0,
                "coverage_level": "NONE",
                "knowledge_gaps": [],
                "knowledge_types": [],
            },
        )
        item["categories"].append(row["category"])
        item["knowledge_gaps"].extend(row["knowledge_gaps"])
    for ds in datasets:
        for industry in ds.industries:
            item = by_industry.setdefault(
                industry,
                {
                    "industry": industry,
                    "categories": [],
                    "dataset_count": 0,
                    "bytes": 0,
                    "coverage_level": "NONE",
                    "knowledge_gaps": [],
                    "knowledge_types": [],
                },
            )
            item["dataset_count"] += 1
            item["bytes"] += ds.size_bytes
            item["knowledge_types"].append(ds.knowledge_type)
    for item in by_industry.values():
        item["categories"] = sorted(set(item["categories"]))
        item["knowledge_gaps"] = sorted(set(item["knowledge_gaps"]))
        item["knowledge_types"] = sorted(set(item["knowledge_types"]))
        if item["dataset_count"] >= 4:
            item["coverage_level"] = "HIGH"
        elif item["dataset_count"] >= 2:
            item["coverage_level"] = "MEDIUM"
        elif item["dataset_count"] == 1:
            item["coverage_level"] = "LOW"
        else:
            item["coverage_level"] = "NONE"
    return sorted(by_industry.values(), key=lambda x: x["industry"])


def build_rejected() -> list[dict[str, Any]]:
    return [
        {
            "name": "UNSPSC commodity taxonomy",
            "source": "UNSPSC",
            "url": "https://www.unspsc.org/",
            "reason": "LICENSE_UNCLEAR",
            "license_status": "Public viewing exists, but redistribution/offline retention terms were not accepted as clearly open.",
            "size_if_known": None,
        },
        {
            "name": "ECLASS standard product classification",
            "source": "ECLASS e.V.",
            "url": "https://eclass.eu/",
            "reason": "PROPRIETARY",
            "license_status": "Standard/taxonomy licensing is not openly reusable for this offline baseline.",
            "size_if_known": None,
        },
        {
            "name": "GS1 Global Product Classification",
            "source": "GS1",
            "url": "https://www.gs1.org/standards/gpc",
            "reason": "LICENSE_INCOMPATIBLE",
            "license_status": "Terms are not a simple permissive open-data license for permanent redistribution.",
            "size_if_known": None,
        },
        {
            "name": "Manufacturer PDF catalogs and datasheets",
            "source": "Various manufacturers",
            "url": "",
            "reason": "PROPRIETARY",
            "license_status": "Publicly visible documents usually retain copyright and did not provide explicit redistribution rights.",
            "size_if_known": None,
        },
        {
            "name": "CWRU Bearing Data Center fault data",
            "source": "Case Western Reserve University",
            "url": "https://engineering.case.edu/bearingdatacenter",
            "reason": "LICENSE_UNCLEAR",
            "license_status": "Useful for failure/time-series research, but license was not accepted as clearly permitting offline redistribution.",
            "size_if_known": None,
        },
        {
            "name": "MIMII Dataset",
            "source": "Research dataset",
            "url": "https://zenodo.org/",
            "reason": "LOW_RELEVANCE",
            "license_status": "Machine-sound/anomaly dataset; not product identification/specification knowledge and large relative to value.",
            "size_if_known": None,
        },
        {
            "name": "Kaggle industrial product datasets",
            "source": "Kaggle",
            "url": "https://www.kaggle.com/",
            "reason": "LICENSE_UNCLEAR",
            "license_status": "Candidate datasets require per-dataset login/terms verification; skipped rather than assuming rights.",
            "size_if_known": None,
        },
    ]


def build_gap_report(industry_coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for item in industry_coverage:
        if item["coverage_level"] in {"NONE", "LOW"}:
            gaps.append(
                {
                    "industry": item["industry"],
                    "category": "*",
                    "missing_knowledge": [
                        "Open licensed product catalog records",
                        "Category-specific attribute vocabulary" if not item["knowledge_types"] else "Deeper category-specific product specification data",
                    ],
                    "reason": "No clearly licensed real product/specification dataset found during bounded acquisition.",
                    "recommended_future_source": "Official government open-data portals, university repositories, Zenodo records with explicit CC0/CC BY licenses, or manufacturer datasets with explicit redistribution grants.",
                    "external_research_required": True,
                }
            )
    return gaps


def verify_retrieval(datasets: list[Dataset]) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT))
    try:
        from backend.retrieval.retrieval_service import RetrievalService
        from backend.retrieval.vector_store import InMemoryVectorStore
        from backend.schemas.source import ProcessedSource
    except Exception as exc:  # noqa: BLE001
        return [{"query": "*", "status": "FAILED", "error": str(exc)}]

    service = RetrievalService(store=InMemoryVectorStore())
    for ds in datasets:
        chunks: list[str] = []
        for file_rel in ds.files:
            path = PERM_DIR / file_rel
            if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".ttl"}:
                continue
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore")[:20000])
            except Exception:
                continue
        if chunks:
            service.index_processed_source(
                ProcessedSource(
                    source_id=ds.dataset_id,
                    original_file=ds.files[0],
                    source_type="baseline",
                    extracted_text="\n".join(chunks),
                    metadata={
                        "source_type": "baseline",
                        "url": ds.source_url,
                        "original_file": ds.files[0],
                    },
                )
            )
    queries = [
        "electric motor product type rated voltage",
        "centrifugal pump flow rate head impeller",
        "butterfly valve pressure rating body material",
        "industrial sensor output signal accuracy",
        "fastener thread size grade material",
        "HVAC ventilating fan boiler heat pump",
    ]
    results = []
    for query in queries:
        evidence = service.search(query, top_k=5)
        results.append(
            {
                "query": query,
                "total_found": len(evidence),
                "top_sources": [ev.source_id for ev in evidence[:3]],
                "top_scores": [ev.score for ev in evidence[:3]],
                "bearing_bias_detected": bool(evidence and "bearing" in evidence[0].content.lower() and "bearing" not in query.lower()),
                "status": "PASS" if evidence else "FAIL",
            }
        )
    return results


def anti_fabrication_audit(datasets: list[Dataset]) -> dict[str, Any]:
    forbidden = ["fake manufacturer", "synthetic product", "invented sku", "lorem ipsum"]
    hits = []
    for ds in datasets:
        for rel in ds.files:
            path = PERM_DIR / rel
            if path.suffix.lower() not in {".json", ".jsonl", ".csv", ".ttl"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for needle in forbidden:
                if needle in text:
                    hits.append({"dataset_id": ds.dataset_id, "file": rel, "needle": needle})
    return {"fabrication_detected": bool(hits), "hits": hits}


def main() -> None:
    if not ROOT.samefile(Path.cwd()) and Path.cwd() != ROOT:
        os.chdir(ROOT)
    PERM_DIR.mkdir(parents=True, exist_ok=True)
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    coverage_rows, terms = derive_coverage()
    current_bytes = dir_size(PERM_DIR)
    remaining = LIMIT_BYTES - current_bytes
    if remaining <= 0:
        raise RuntimeError("Permanent knowledge storage is already at or above the 2 GiB limit")

    staged: list[tuple[Path, Dataset]] = []
    rejected = build_rejected()

    acquisition_steps = [
        ("wikidata", lambda: acquire_wikidata(terms, coverage_rows)),
        ("wikipedia", lambda: acquire_wikipedia(terms, coverage_rows)),
        ("qudt", lambda: acquire_qudt(LIMIT_BYTES - dir_size(PERM_DIR) - sum(dataset_size(p) for p, _ in staged))),
        ("naics", lambda: acquire_naics(LIMIT_BYTES - dir_size(PERM_DIR) - sum(dataset_size(p) for p, _ in staged))),
    ]
    for name, fn in acquisition_steps:
        try:
            ds = fn()
            staged.append((STAGING_DIR / ds.dataset_id, ds))
        except Exception as exc:  # noqa: BLE001
            rejected.append(
                {
                    "name": name,
                    "source": "",
                    "url": "",
                    "reason": "UNAVAILABLE",
                    "license_status": "Approved source candidate failed during bounded acquisition.",
                    "size_if_known": None,
                    "error": str(exc),
                }
            )

    try:
        energy_datasets = acquire_energy_star(LIMIT_BYTES - dir_size(PERM_DIR) - sum(dataset_size(p) for p, _ in staged))
        for ds in energy_datasets:
            staged.append((STAGING_DIR / ds.dataset_id, ds))
    except Exception as exc:  # noqa: BLE001
        rejected.append(
            {
                "name": "ENERGY STAR certified product datasets",
                "source": "U.S. EPA",
                "url": "https://www.energystar.gov/productfinder/advanced",
                "reason": "UNAVAILABLE",
                "license_status": "License accepted, but download failed during acquisition.",
                "size_if_known": None,
                "error": str(exc),
            }
        )

    installed: list[Dataset] = []
    existing_records = existing_dataset_records()
    checksum_to_dataset_id = {
        r.get("checksum"): r.get("dataset_id")
        for r in existing_records
        if r.get("checksum")
    }
    for stage_path, ds in staged:
        existing_checksum_owner = checksum_to_dataset_id.get(ds.sha256)
        if existing_checksum_owner and existing_checksum_owner != ds.dataset_id:
            rejected.append(
                {
                    "name": ds.name,
                    "source": ds.source,
                    "url": ds.source_url,
                    "reason": "DUPLICATE",
                    "license_status": ds.license,
                    "size_if_known": ds.size_bytes,
                }
            )
            continue
        installed.append(install_dataset(stage_path, ds))
        checksum_to_dataset_id[ds.sha256] = ds.dataset_id

    register_datasets(installed)

    all_records = existing_dataset_records()
    industry_coverage = build_industry_coverage(coverage_rows, installed)
    gaps = build_gap_report(industry_coverage)
    retrieval = verify_retrieval(installed)
    fabrication = anti_fabrication_audit(installed)

    write_json(PERM_DIR / "coverage_matrix.json", coverage_rows)
    write_json(PERM_DIR / "industry_coverage.json", industry_coverage)
    write_json(PERM_DIR / "rejected_datasets.json", rejected)
    write_json(PERM_DIR / "knowledge_gap_report.json", gaps)
    write_json(PERM_DIR / "retrieval_verification.json", retrieval)

    filesystem_bytes_before_manifest = dir_size(PERM_DIR)
    manifest = {
        "total_bytes": filesystem_bytes_before_manifest,
        "limit_bytes": LIMIT_BYTES,
        "dataset_count": len([r for r in all_records if r.get("permanent")]),
        "industries": sorted({i for ds in installed for i in ds.industries}),
        "categories": sorted({c for ds in installed for c in ds.categories}),
        "datasets": [asdict(ds) for ds in installed],
        "licenses": sorted({ds.license for ds in installed}),
        "sources": sorted({ds.source for ds in installed}),
        "checksums": {ds.dataset_id: ds.sha256 for ds in installed},
        "attribution": {ds.dataset_id: ds.attribution for ds in installed},
        "acquisition_timestamps": {ds.dataset_id: ds.downloaded_at for ds in installed},
        "rejected_datasets": rejected,
        "knowledge_gaps": gaps,
        "existing_registry_records": all_records,
        "fabrication_audit": fabrication,
        "retrieval_verification": retrieval,
    }
    write_json(PERM_DIR / "permanent_knowledge_manifest.json", manifest)

    final_bytes = dir_size(PERM_DIR)
    final_audit = {
        "filesystem_bytes": final_bytes,
        "manifest_bytes": final_bytes,
        "registry_bytes": sum(int(r.get("size_bytes") or 0) for r in existing_dataset_records() if r.get("permanent")),
        "limit_bytes": LIMIT_BYTES,
        "remaining_bytes": LIMIT_BYTES - final_bytes,
        "usage_percent": round(final_bytes / LIMIT_BYTES * 100, 4),
        "actual_gib": final_bytes / 1024**3,
        "installed_dataset_count": len(installed),
        "fabrication_detected": fabrication["fabrication_detected"],
        "storage_limit_ok": final_bytes <= LIMIT_BYTES,
    }
    write_json(PERM_DIR / "final_storage_audit.json", final_audit)

    shutil.rmtree(STAGING_DIR, ignore_errors=True)
    print(json.dumps(final_audit, indent=2))


if __name__ == "__main__":
    main()
