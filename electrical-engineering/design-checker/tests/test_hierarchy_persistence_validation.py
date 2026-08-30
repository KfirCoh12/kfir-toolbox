import tempfile
import unittest
from pathlib import Path

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.circuit_engine import CircuitDesignRequest
from src.hierarchy_constraints import BreakerRatingConstraint
from src.hierarchy_persistence import (
    HierarchyEngineeringProject,
    project_from_document,
    project_to_document,
    save_hierarchy_project,
    validate_hierarchy_project,
)
from src.hierarchy_planner import FeederInstallationDeclaration, FeederPhaseMappingDeclaration


class HierarchyPersistenceValidationTests(unittest.TestCase):
    def _graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Sub-board",
        )
        return add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Child load",
            load_kw=5.0,
            phase="three",
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

    def test_valid_project_passes_semantic_validation(self):
        project = HierarchyEngineeringProject(graph=self._graph())
        self.assertIsNone(validate_hierarchy_project(project))

    def test_unknown_circuit_override_is_rejected_before_persistence(self):
        project = HierarchyEngineeringProject(
            graph=self._graph(),
            circuit_request_overrides=(
                CircuitDesignRequest(
                    circuit_id="C-404",
                    description="Unknown load",
                    load_type="a",
                    load_value=16.0,
                    voltage_v=400.0,
                    phase="three",
                    power_factor=None,
                    demand_factor=1.0,
                    material="copper",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "unknown graph load"):
            project_to_document(project)

    def test_duplicate_feeder_installations_are_rejected_before_persistence(self):
        declaration = FeederInstallationDeclaration(
            feeder_circuit_id="DBF-01",
            material="copper",
            basis_note="Reviewed installation",
        )
        project = HierarchyEngineeringProject(
            graph=self._graph(),
            feeder_installations=(declaration, declaration),
        )
        with self.assertRaisesRegex(ValueError, "duplicate feeder installation"):
            project_to_document(project)

    def test_invalid_phase_mapping_is_rejected_when_loading_document(self):
        document = project_to_document(HierarchyEngineeringProject(graph=self._graph()))
        document["project"]["feeder_phase_mappings"] = [
            {
                "feeder_circuit_id": "DBF-01",
                "child_l1_to_parent": "L1",
                "child_l2_to_parent": "L1",
                "child_l3_to_parent": "L3",
                "basis_note": "Invalid duplicate target",
            }
        ]
        with self.assertRaisesRegex(ValueError, "one-to-one phase permutation"):
            project_from_document(document)

    def test_unknown_feeder_installation_is_rejected_when_loading_document(self):
        document = project_to_document(HierarchyEngineeringProject(graph=self._graph()))
        document["project"]["feeder_installations"] = [
            {
                "feeder_circuit_id": "DBF-404",
                "material": "copper",
                "ambient_temperature_c": 30.0,
                "grouped_circuits": 1,
                "grouping_arrangement": None,
                "parallel_runs": 1,
                "equal_current_sharing_confirmed": None,
                "length_m": None,
                "power_factor": None,
                "permitted_voltage_drop_percent": None,
                "voltage_drop_limit_source": None,
                "allow_annex_g_defaults": False,
                "basis_note": "Reviewed installation",
            }
        ]
        with self.assertRaisesRegex(ValueError, "unknown sub-board feeder"):
            project_from_document(document)

    def test_unknown_breaker_constraint_is_rejected_before_persistence(self):
        project = HierarchyEngineeringProject(
            graph=self._graph(),
            breaker_constraints=(
                BreakerRatingConstraint(
                    node_id="missing:device",
                    rating_a=32.0,
                    basis_note="Recorded breaker rating",
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "unknown node"):
            project_to_document(project)

    def test_duplicate_breaker_constraints_are_rejected_when_loading_document(self):
        project = HierarchyEngineeringProject(
            graph=self._graph(),
            breaker_constraints=(
                BreakerRatingConstraint(
                    node_id="C-01:device",
                    rating_a=32.0,
                    basis_note="Recorded breaker rating",
                ),
            ),
        )
        document = project_to_document(project)
        document["project"]["breaker_constraints"].append(
            dict(document["project"]["breaker_constraints"][0])
        )
        with self.assertRaisesRegex(ValueError, "duplicate breaker constraint"):
            project_from_document(document)

    def test_failed_save_does_not_replace_existing_valid_file(self):
        valid = HierarchyEngineeringProject(graph=self._graph())
        invalid = HierarchyEngineeringProject(
            graph=self._graph(),
            feeder_phase_mappings=(
                FeederPhaseMappingDeclaration(
                    feeder_circuit_id="DBF-01",
                    child_l1_to_parent="L1",
                    child_l2_to_parent="L1",
                    child_l3_to_parent="L3",
                    basis_note="Invalid duplicate target",
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hierarchy.json"
            save_hierarchy_project(valid, path)
            original = path.read_text(encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "one-to-one phase permutation"):
                save_hierarchy_project(invalid, path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
