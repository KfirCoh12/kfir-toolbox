import copy
import unittest

from src.board_graph import add_radial_circuit, make_radial_board_graph
from src.hierarchy_enrichment import enrich_graph_with_hierarchy_plan
from src.hierarchy_persistence import (
    HierarchyEngineeringProject,
    project_from_document,
    project_to_document,
)
from src.hierarchy_planner import calculate_board_hierarchy


class HierarchyPersistenceDerivedResultTests(unittest.TestCase):
    def _raw_project(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Process load",
            load_kw=5.0,
            phase="three",
        )
        return HierarchyEngineeringProject(graph=graph)

    def test_enriched_graph_results_are_not_persisted_as_engineering_inputs(self):
        raw_project = self._raw_project()
        result = calculate_board_hierarchy(raw_project.graph)
        enriched_graph = enrich_graph_with_hierarchy_plan(raw_project.graph, result)

        self.assertTrue(
            any(
                node.rating_a is not None
                or node.cable_mm2 is not None
                or node.assigned_phase is not None
                or node.scope_status is not None
                or node.issue_codes
                for node in enriched_graph.nodes
            )
        )

        document = project_to_document(HierarchyEngineeringProject(graph=enriched_graph))
        saved_nodes = document["project"]["graph"]["nodes"]
        for node in saved_nodes:
            self.assertIsNone(node["rating_a"])
            self.assertIsNone(node["cable_mm2"])
            self.assertIsNone(node["cable_runs"])
            self.assertIsNone(node["assigned_phase"])
            self.assertIsNone(node["scope_status"])
            self.assertEqual(node["issue_codes"], [])

        restored = project_from_document(document)
        self.assertEqual(restored.graph, raw_project.graph)
        self.assertEqual(
            calculate_board_hierarchy(restored.graph),
            calculate_board_hierarchy(raw_project.graph),
        )

    def test_existing_schema_document_with_stale_enrichment_is_sanitized_on_load(self):
        raw_project = self._raw_project()
        document = project_to_document(raw_project)
        stale = copy.deepcopy(document)
        device = next(
            node
            for node in stale["project"]["graph"]["nodes"]
            if node["kind"] == "protective_device"
        )
        device["rating_a"] = 999.0
        device["assigned_phase"] = "L1"
        device["scope_status"] = "SUPPORTED_SCOPE"
        device["issue_codes"] = ["STALE_RESULT"]
        cable = next(
            node
            for node in stale["project"]["graph"]["nodes"]
            if node["kind"] == "cable"
        )
        cable["cable_mm2"] = 999.0
        cable["cable_runs"] = 7

        restored = project_from_document(stale)

        restored_device = next(
            node for node in restored.graph.nodes if node.kind == "protective_device"
        )
        restored_cable = next(node for node in restored.graph.nodes if node.kind == "cable")
        self.assertIsNone(restored_device.rating_a)
        self.assertIsNone(restored_device.assigned_phase)
        self.assertIsNone(restored_device.scope_status)
        self.assertEqual(restored_device.issue_codes, tuple())
        self.assertIsNone(restored_cable.cable_mm2)
        self.assertIsNone(restored_cable.cable_runs)
        self.assertEqual(restored.graph, raw_project.graph)


if __name__ == "__main__":
    unittest.main()
