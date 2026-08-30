import unittest
from pathlib import Path


class DeploymentConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.dockerfile = (cls.root / "Dockerfile").read_text(encoding="utf-8")
        cls.dockerignore = (cls.root / ".dockerignore").read_text(encoding="utf-8")
        cls.persistence = (cls.root / "src" / "board_persistence.py").read_text(encoding="utf-8")
        cls.private_app = (cls.root / "private_app.py").read_text(encoding="utf-8")

    def test_container_runs_private_streamlit_entrypoint_on_external_interface(self):
        self.assertIn("streamlit run private_app.py", self.dockerfile)
        self.assertIn("--server.address=0.0.0.0", self.dockerfile)
        self.assertIn("${PORT:-8501}", self.dockerfile)

    def test_container_defaults_to_private_auth_and_persistent_data_dir(self):
        self.assertIn("KFIR_TOOLBOX_REQUIRE_AUTH=1", self.dockerfile)
        self.assertIn("KFIR_TOOLBOX_DATA_DIR=/data", self.dockerfile)
        self.assertIn("USER toolbox", self.dockerfile)
        self.assertIn("/_stcore/health", self.dockerfile)

    def test_private_entrypoint_fails_closed_without_explicit_allowlist(self):
        self.assertIn("if not authentication_required():", self.private_app)
        self.assertIn("if not allowed_emails():", self.private_app)
        self.assertIn("require_authenticated_user(st)", self.private_app)
        self.assertIn("st.navigation", self.private_app)

    def test_container_does_not_copy_common_secret_files(self):
        self.assertIn(".streamlit/secrets.toml", self.dockerignore)
        self.assertIn(".env", self.dockerignore)
        self.assertIn(".kfir-toolbox/", self.dockerignore)

    def test_persistence_supports_private_hosted_data_mount(self):
        self.assertIn("KFIR_TOOLBOX_DATA_DIR", self.persistence)
        self.assertIn("toolbox_data_root()", self.persistence)


if __name__ == "__main__":
    unittest.main()
