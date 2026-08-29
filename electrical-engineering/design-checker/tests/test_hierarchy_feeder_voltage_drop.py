import unittest

from src.board_graph import add_radial_circuit, add_sub_board_feeder, make_radial_board_graph
from src.hierarchy_planner import FeederInstallationDeclaration, calculate_board_hierarchy


class HierarchyFeederVoltageDropTests(unittest.TestCase):
    def _graph(self):
        graph = make_radial_board_graph(board_id="DB-01", description="Main board")
        graph = add_sub_board_feeder(
            graph,
            feeder_id="DBF-01",
            sub_board_id="DB-02",
            description="Three-phase sub-board",
        )
        return add_radial_circuit(
            graph,
            circuit_id="C-01",
            description="Three-phase load",
            load_kw=18.0,
            phase="three",
            power_factor=0.9,
            parent_busbar_id="DBF-01:DB-02:busbar",
        )

    def test_feeder_length_requires_explicit_annex_g_default_opt_in(self):
        with self.assertRaisesRegex(ValueError, "allow_annex_g_defaults=True"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    length_m=25.0,
                    basis_note="Measured feeder route length.",
                ),),
            )

    def test_feeder_voltage_drop_can_use_explicit_pf_with_opted_in_impedance_defaults(self):
        result = calculate_board_hierarchy(
            self._graph(),
            feeder_installations=(FeederInstallationDeclaration(
                feeder_circuit_id="DBF-01",
                length_m=25.0,
                power_factor=0.92,
                allow_annex_g_defaults=True,
                basis_note="Measured feeder route; Annex G impedance defaults explicitly accepted.",
            ),),
        )
        rollup = result.feeder_rollups[0]
        self.assertEqual(rollup.cable_status, "CANDIDATE")
        self.assertIsNotNone(rollup.cable_candidate_mm2)
        self.assertTrue(rollup.installation_declared)

    def test_voltage_drop_limit_requires_length_and_source(self):
        with self.assertRaisesRegex(ValueError, "limit requires length_m"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    permitted_voltage_drop_percent=3.0,
                    basis_note="Project declaration.",
                ),),
            )

        with self.assertRaisesRegex(ValueError, "limit source is required"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    length_m=25.0,
                    permitted_voltage_drop_percent=3.0,
                    allow_annex_g_defaults=True,
                    basis_note="Project declaration.",
                ),),
            )

    def test_feeder_power_factor_is_validated_and_only_allowed_with_length(self):
        with self.assertRaisesRegex(ValueError, "power_factor must be greater than 0"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    length_m=25.0,
                    power_factor=0.0,
                    allow_annex_g_defaults=True,
                    basis_note="Project declaration.",
                ),),
            )

        with self.assertRaisesRegex(ValueError, "only used when length_m is declared"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    power_factor=0.9,
                    basis_note="Project declaration.",
                ),),
            )

    def test_non_positive_feeder_length_is_rejected_before_calculation(self):
        with self.assertRaisesRegex(ValueError, "length_m must be finite and greater than 0"):
            calculate_board_hierarchy(
                self._graph(),
                feeder_installations=(FeederInstallationDeclaration(
                    feeder_circuit_id="DBF-01",
                    length_m=0.0,
                    allow_annex_g_defaults=True,
                    basis_note="Project declaration.",
                ),),
            )


if __name__ == "__main__":
    unittest.main()
