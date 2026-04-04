from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.agent.storage.source_control_plane import (
    SourceControlPlaneStore,
    control_plane_db_path,
    ensure_control_plane_db,
)


class SourceControlPlaneStoreTests(unittest.TestCase):
    def test_bootstraps_control_plane_tables(self) -> None:
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            db_path = ensure_control_plane_db(base_dir=base_dir)

            self.assertEqual(db_path, control_plane_db_path(base_dir=base_dir))
            self.assertTrue(db_path.exists())

            store = SourceControlPlaneStore(base_dir=base_dir)
            operator_state = store.get_operator_state("reuters_business")

            self.assertIsNone(operator_state)


if __name__ == "__main__":
    unittest.main()
