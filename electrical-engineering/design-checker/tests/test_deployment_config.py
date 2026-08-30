import unittest
from pathlib import Path


class DeploymentConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.dockerfile = (cls.root / "Dockerfile").read_text(encoding="utf-8")
        cls.dockerignore = (cls.root / ".dockerignore").read_text(encoding="utf-8")
        cls.persistence = (cls.root / "src" / "board_persistence.py").read_text(encoding="utf-8")

    def test_container_runs_streamlit_on_external_interface(self):
        self.assertIn("streamlit run app.py", self.dockerfile)
        self.assertIn("--server.address=0.0.0.0", self.dockerfile)
        self.assertIn("${PORT:-8501}", self.dockerfile)

    def test_container_does_not_copy_common_secret_files(self):
        self.assertIn(".streamlit/secrets.toml", self.dockerignore)
        self.assertIn(".env", self.dockerignore)
        self.assertIn(".kfir-toolbox/", self.dockerignore)

    def test_persistence_supports_private_hosted_data_mount(self):
        self.assertIn('KFIR_TOOLBOX_DATA_DIR', self.persistence)
        self.assertIn('toolbox_data_root()', self.persistence)


if __name__ == "__main__":
    unittest.main()
