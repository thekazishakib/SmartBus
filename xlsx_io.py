"""Read saved workbook inputs directly, ignoring cached formula values."""

import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from zipfile import ZipFile

NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
MAIN = NS["s"]


def tag(x: str) -> str:
    return "{" + MAIN + "}" + x


def read_book(path: Path | str) -> dict[str, dict[str, object]]:
    with ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            shared = [
                "".join(t.text or "" for t in si.findall(".//s:t", NS))
                for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(
                    "s:si", NS
                )
            ]
        rel = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        }
        sheets = {}
        for s in ET.fromstring(z.read("xl/workbook.xml")).findall(
            "s:sheets/s:sheet", NS
        ):
            target = rel[s.attrib["{" + NS["r"] + "}id"]]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            cells = {}
            for c in ET.fromstring(z.read(target)).findall(
                ".//s:sheetData/s:row/s:c", NS
            ):
                if c.find("s:f", NS) is not None:
                    continue
                typ = c.get("t")
                v = c.find("s:v", NS)
                if typ == "inlineStr":
                    value = "".join(t.text or "" for t in c.findall(".//s:t", NS))
                elif v is None:
                    continue
                elif typ == "s":
                    value = shared[int(v.text)]
                elif typ in ("str", "e"):
                    value = v.text
                else:
                    try:
                        value = float(v.text)
                        value = int(value) if value.is_integer() else value
                    except (ValueError, TypeError):
                        value = v.text
                cells[c.attrib["r"]] = value
            sheets[s.attrib["name"]] = cells
        if "Read the Manual" not in sheets:
            raise ValueError("Old workbook format: " + str(path))
        return sheets


def rows(
    cells: Mapping[str, object], cols: Sequence[str], end: int
) -> list[list[object]]:
    return [
        [cells.get(f"{c}{r}") for c in cols]
        for r in range(6, end + 1)
        if cells.get(f"A{r}") not in (None, "")
    ]
