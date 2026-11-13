"""Safety regression: licensed EODHD calls are private-repository-only.

This protects GitHub Actions jobs in this repository, not arbitrary local
executions, existing historical Actions logs or manually uploaded data.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PRIVATE_GATE = "github.event.repository.private == true"

# All workflows exposing the EODHD API token MUST be explicitly gated.
EODHD_WORKFLOWS = {
    "eodhd-eu-free-one-stock.yml": "single-eu-eod-read-only",
    "eodhd-helsinki-splits.yml": "fetch-split-events",
    "eodhd-helsinki-two-stock.yml": "Read two Helsinki stock histories",
    "us-active-delisted-catalog.yml": "personal-metadata-only",
    "broad-market-catalog.yml": "inventory-private-metadata",
}


class LicensedResearchPrivacyTests(unittest.TestCase):
    def test_all_eodhd_workflows_explicitly_guarded(self):
        seen = set()
        for path in WORKFLOWS.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if "secrets.EODHD_API_TOKEN" not in text:
                continue
            seen.add(path.name)
            self.assertIn(path.name, EODHD_WORKFLOWS)
            marker = EODHD_WORKFLOWS[path.name]
            self.assertIn(marker, text)
            self.assertIn(PRIVATE_GATE, text, path.name)
            if path.name == "eodhd-helsinki-two-stock.yml":
                # This workflow's offline test job is public, but live
                # data step must have its own private-only condition.
                self.assertIn(
                    "if: ${{ github.event.repository.private == true && "
                    "inputs.approve_two_personal_eod_requests == true }}",
                    text,
                )
            else:
                # All other jobs with EODHD tokens have job-level guards.
                self.assertIn(
                    "    if: ${{ github.event.repository.private == true",
                    text,
                    path.name,
                )
        self.assertEqual(seen, set(EODHD_WORKFLOWS))

    def test_public_dashboard_not_connected_to_eodhd(self):
        dashboard = (WORKFLOWS / "dashboard.yml").read_text(encoding="utf-8")
        self.assertNotIn("EODHD_API_TOKEN", dashboard)
        self.assertNotIn("licensed_data", dashboard)
        self.assertNotIn("licensed_reports", dashboard)

    def test_accidentally_generated_data_is_gitignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for pattern in (
            "licensed_data/", "private_data/", "licensed_reports/",
            "private_reports/", "*.parquet", "*.duckdb", "*.sqlite3",
        ):
            self.assertIn(pattern, ignored)


if __name__ == "__main__":
    unittest.main()
