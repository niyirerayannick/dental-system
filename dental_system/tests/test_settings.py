import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ProductionDatabaseSettingsTests(SimpleTestCase):
    def test_sqlite_blocked_when_debug_false_without_database_url(self):
        project_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["DEBUG"] = "False"
        env.pop("DATABASE_URL", None)
        env["DJANGO_SETTINGS_MODULE"] = "dental_system.settings"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import django; django.setup()",
            ],
            cwd=project_root,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        combined = f"{result.stdout}\n{result.stderr}"
        self.assertIn("DATABASE_URL is required", combined)
