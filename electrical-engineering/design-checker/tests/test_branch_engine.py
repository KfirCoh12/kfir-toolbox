import unittest

from src.branch_engine import FinalBranchDesignRequest, calculate_final_branch


class FinalBranchDesignTests(unittest.TestCase):
    def test_auto_mode_uses_expected_load_through_existing_circuit_engine(self):
        result = calculate_final_branch(FinalBranchDesignRequest(
            circuit_id="C-01",
            description="AHU",
            mode="auto",
            expected_load_kw=18,
            voltage_v=400,
            phase="three",
            power_factor=0.9,
        ))
        self.assertEqual(result.circuit.request.load_type, "kw")
        self.assertEqual(result.circuit.request.load_value, 18)
        self.assertGreater(result.design_current_a, 0)
        self.assertIsNotNone(result.breaker_a)
        self.assertIsNotNone(result.connection)

    def test_manual_mode_uses_fixed_connection_rating_as_required_branch_current(self):
        result = calculate_final_branch(FinalBranchDesignRequest(
            circuit_id="C-02",
            description="Known industrial outlet",
            mode="manual",
            connection_option_id="industrial_32a_3ph",
            voltage_v=400,
            phase="three",
            power_factor=0.9,
        ))
        self.assertEqual(result.circuit.request.load_type, "a")
        self.assertEqual(result.circuit.request.load_value, 32.0)
        self.assertAlmostEqual(result.design_current_a, 32.0)
        self.assertEqual(result.breaker_a, 32.0)
        self.assertEqual(result.connection.id, "industrial_32a_3ph")
        self.assertEqual(result.connection_rating_a, 32.0)
        self.assertIsNotNone(result.cable_mm2)

    def test_manual_mode_preserves_exact_user_connection_choice(self):
        result = calculate_final_branch(FinalBranchDesignRequest(
            circuit_id="C-03",
            description="General socket",
            mode="manual",
            connection_option_id="general_socket_16a_1ph",
            voltage_v=230,
            phase="single",
            power_factor=0.9,
        ))
        self.assertEqual(result.connection.id, "general_socket_16a_1ph")
        self.assertEqual(result.connection_rating_a, 16.0)
        self.assertEqual(result.breaker_a, 16.0)
        self.assertIsNone(result.cable_mm2)
        self.assertEqual(result.circuit.verification.scope_status, "PARTIAL_SCOPE")

    def test_manual_mode_rejects_phase_mismatch_and_unrated_fixed_connection(self):
        with self.assertRaisesRegex(ValueError, "phase does not match"):
            calculate_final_branch(FinalBranchDesignRequest(
                circuit_id="C-04",
                description="Wrong phase",
                mode="manual",
                connection_option_id="industrial_32a_1ph",
                voltage_v=400,
                phase="three",
            ))
        with self.assertRaisesRegex(ValueError, "declared nominal current rating"):
            calculate_final_branch(FinalBranchDesignRequest(
                circuit_id="C-05",
                description="Fixed connection",
                mode="manual",
                connection_option_id="fixed_connection_3ph",
                voltage_v=400,
                phase="three",
            ))

    def test_modes_require_only_their_own_input_contract(self):
        with self.assertRaisesRegex(ValueError, "expected_load_kw is required"):
            calculate_final_branch(FinalBranchDesignRequest(
                circuit_id="C-06",
                description="Missing auto load",
                mode="auto",
                voltage_v=400,
                phase="three",
            ))
        with self.assertRaisesRegex(ValueError, "connection_option_id is required"):
            calculate_final_branch(FinalBranchDesignRequest(
                circuit_id="C-07",
                description="Missing manual connection",
                mode="manual",
                voltage_v=400,
                phase="three",
            ))


if __name__ == "__main__":
    unittest.main()
