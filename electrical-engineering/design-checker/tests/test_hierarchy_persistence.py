import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.circuit_engine import CircuitDesignRequest
from src.hierarchy_constraints import BreakerRatingConstraint, assess_breaker_constraints
from src.hierarchy_persistence import (
    HierarchyEngineeringProject,
    clear_hierarchy_project,
    load_hierarchy_project,
    project_from_document,
    project_to_document,
    save_hierarchy_project,
)
from src.hierarchy_planner import (
    FeederInstallationDeclaration,
    FeederPhaseMappingDeclaration,
    calculate_board_hierarchy,
)


class HierarchyPersistenceTests(unittest.TestCase):
    def _project(self):
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
            description="Child process load",
            load_kw=1.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )
        override = CircuitDesignRequest(
            circuit_id="C-01",
            description="Child process load",
            load_type="kva",
            load_value=18.0,
            voltage_v=400.0,
            phase="three",
            power_factor=None,
            demand_factor=0.9,
            material="copper",
        )
        installation = FeederInstallationDeclaration(
            feeder_circuit_id="DBF-01",
            material="copper",
            ambient_temperature_c=35.0,
            grouped_circuits=1,
            parallel_runs=1,
            basis_note="Reviewed feeder installation declaration",
        )
        mapping = FeederPhaseMappingDeclaration(
            feeder_circuit_id="DBF-01",
            child_l1_to_parent="L2",
            child_l2_to_parent="L3",
            child_l3_to_parent="L1",
            basis_note="Reviewed phase transposition",
        )
        constraint = BreakerRatingConstraint(
            node_id="C-01:device",
            rating_a=32.0,
            basis_note="Existing downstream breaker rating",
        )
        return HierarchyEngineeringProject(
            graph=graph,
            circuit_request_overrides=(override,),
            feeder_installations=(installation,),
            feeder_phase_mappings=(mapping,),
            breaker_constraints=(constraint,),
        )

    def test_document_round_trip_preserves_source_inputs(self):
        project = self._project()
        document = project_to_document(project)
        restored = project_from_document(document)
        self.assertEqual(restored, project)
        self.assertEqual(document["schema_version"], 2)
        self.assertIsInstance(document["project"]["graph"]["nodes"][0]["issue_codes"], list)
        self.assertEqual(
            document["project"]["breaker_constraints"][0]["node_id"],
            "C-01:device",
        )

    def test_file_round_trip_preserves_inputs_and_recalculates_same_hierarchy(self):
        project = self._project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            save_hierarchy_project(project, path)
            restored = load_hierarchy_project(path)
            self.assertEqual(restored, project)

            before = calculate_board_hierarchy(
                project.graph,
                project.circuit_request_overrides,
                project.feeder_installations,
                project.feeder_phase_mappings,
            )
            after = calculate_board_hierarchy(
                restored.graph,
                restored.circuit_request_overrides,
                restored.feeder_installations,
                restored.feeder_phase_mappings,
            )
            self.assertEqual(after, before)
            self.assertEqual(
                assess_breaker_constraints(project.graph, before, project.breaker_constraints),
                assess_breaker_constraints(restored.graph, after, restored.breaker_constraints),
            )

    def test_save_flushes_temporary_file_to_os_before_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            with patch("src.hierarchy_persistence.os.fsync") as fsync:
                save_hierarchy_project(self._project(), path)
            fsync.assert_called_once()
            self.assertEqual(load_hierarchy_project(path), self._project())

    def test_failed_replace_preserves_existing_target_and_removes_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            path = directory_path / "hierarchy.json"
            path.write_text("existing-valid-save", encoding="utf-8")

            with patch.object(Path, "replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    save_hierarchy_project(self._project(), path)

            self.assertEqual(path.read_text(encoding="utf-8"), "existing-valid-save")
            self.assertEqual(list(directory_path.glob(".hierarchy.json.*.tmp")), [])

    def test_saved_document_contains_inputs_not_calculated_results(self):
        document = project_to_document(self._project())
        serialized = json.dumps(document)
        self.assertIn("breaker_constraints", serialized)
        self.assertNotIn("BreakerConstraintAssessment", serialized)
        self.assertNotIn("required_current_a", serialized)
        self.assertNotIn("feeder_rollups", serialized)
        self.assertNotIn("breaker_candidate_a", serialized)
        self.assertNotIn("cable_candidate_mm2", serialized)

    def test_version_one_document_migrates_with_empty_breaker_constraints(self):
        document = project_to_document(self._project())
        legacy = copy.deepcopy(document)
        legacy["schema_version"] = 1
        del legacy["project"]["breaker_constraints"]

        restored = project_from_document(legacy)

        self.assertEqual(restored.graph, self._project().graph)
        self.assertEqual(restored.circuit_request_overrides, self._project().circuit_request_overrides)
        self.assertEqual(restored.feeder_installations, self._project().feeder_installations)
        self.assertEqual(restored.feeder_phase_mappings, self._project().feeder_phase_mappings)
        self.assertEqual(restored.breaker_constraints, tuple())
        self.assertEqual(project_to_document(restored)["schema_version"], 2)

    def test_unknown_schema_fields_are_rejected_instead_of_ignored(self):
        document = project_to_document(self._project())
        document["project"]["unexpected_future_field"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            project_from_document(document)

        document = project_to_document(self._project())
        document["project"]["graph"]["nodes"][0]["unexpected"] = "value"
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            project_from_document(document)

    def test_unsupported_schema_version_is_rejected(self):
        document = project_to_document(self._project())
        document["schema_version"] = 999
        with self.assertRaisesRegex(ValueError, "unsupported schema version"):
            project_from_document(document)

    def test_invalid_graph_is_rejected_during_load(self):
        document = project_to_document(self._project())
        document["project"]["graph"]["nodes"][0]["label"] = ""
        with self.assertRaisesRegex(ValueError, "requires a label"):
            project_from_document(document)

    def test_missing_file_returns_none_and_clear_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            self.assertIsNone(load_hierarchy_project(path))
            clear_hierarchy_project(path)
            save_hierarchy_project(self._project(), path)
            self.assertTrue(path.exists())
            clear_hierarchy_project(path)
            self.assertFalse(path.exists())
            clear_hierarchy_project(path)


if __name__ == "__main__":
    unittest.main()
