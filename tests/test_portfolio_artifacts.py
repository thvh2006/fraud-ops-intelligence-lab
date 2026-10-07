from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def test_excel_analyst_pack_is_a_valid_workbook() -> None:
    workbook = ROOT / "deliverables" / "Fraud_Ops_Analysis.xlsx"
    assert workbook.stat().st_size > 50_000
    with ZipFile(workbook) as archive:
        names = set(archive.namelist())
    assert "xl/workbook.xml" in names
    assert "xl/worksheets/sheet6.xml" in names


def test_dashboard_preview_is_present() -> None:
    preview = ROOT / "docs" / "assets" / "dashboard-preview.png"
    assert preview.stat().st_size > 50_000
