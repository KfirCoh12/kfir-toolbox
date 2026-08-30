import json
import tempfile
import unittest
from pathlib import Path

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.circuit_engine import CircuitDesignRequest
from src.hierarchy_persistence import (
    HierarchyEngineeringProject,
    load_hierarchy_project,
    project_to_document,
    save_hierarchy_project,
)


class HierarchyPersistenceStrictJsonTests(unittest.TestCase):
    def _project(self, *, load_value: float = 18.0) -> HierarchyEngineeringProject:
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Sub-board",
        )
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Child load",
            load_kw=1.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        override = CircuitDesignRequest(
            circuit_id="C-01",
            description="Child load",
            load_type="kva",
            load_value=load_value,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
            demand_factor=0.9,
            material="copper",
        )
        return HierarchyEngineeringProject(
            graph=graph,
            circuit_request_overrides=(override,),
        )

    def test_save_rejects_non_finite_numeric_input_without_overwriting_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            path.write_text("existing-valid-save", encoding="utf-8")

            with self.assertRaises(ValueError):
                save_hierarchy_project(self._project(load_value=float("nan")), path)

            self.assertEqual(path.read_text(encoding="utf-8"), "existing-valid-save")
            self.assertEqual(list(Path(directory).glob(".hierarchy.json.*.tmp")), [])

    def test_load_rejects_non_standard_non_finite_json_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            document = project_to_document(self._project())
            text = json.dumps(document).replace('"load_value": 18.0', '"load_value": NaN')
            self.assertIn('"load_value": NaN', text)
            path.write_text(text, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Non-finite numeric token"):
                load_hierarchy_project(path)

    def test_load_rejects_duplicate_engineering_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            document = project_to_document(self._project())
            text = json.dumps(document).replace(
                '"load_value": 18.0',
                '"load_value": 18.0, "load_value": 20.0',
            )
            self.assertIn('"load_value": 18.0, "load_value": 20.0', text)
            path.write_text(text, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate object key"):
                load_hierarchy_project(path)


if __name__ == "__main__":
    unittest.main()
