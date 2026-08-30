import unittest
from pathlib import Path


class DeploymentConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.dockerfile = (cls.root / "Dockerfile").read_text(encoding="utf-8")
        cls.docker_entrypoint = (cls.root / "docker-entrypoint.sh").read_text(encoding="utf-8")
        cls.dockerignore = (cls.root / ".dockerignore").read_text(encoding="utf-8")
        cls.gitignore = (cls.root / ".gitignore").read_text(encoding="utf-8")
        cls.persistence = (cls.root / "src" / "board_persistence.py").read_text(encoding="utf-8")
        cls.private_app = (cls.root / "private_app.py").read_text(encoding="utf-8")
        cls.secrets_example = (cls.root / ".streamlit" / "secrets.toml.example").read_text(encoding="utf-8")
        cls.private_deployment = (cls.root / "docs" / "PRIVATE_DEPLOYMENT.md").read_text(encoding="utf-8")
        cls.render_blueprint = (cls.root / "render.yaml").read_text(encoding="utf-8")
        cls.railway_config = (cls.root / "railway.json").read_text(encoding="utf-8")
        cls.railway_deployment = (cls.root / "docs" / "RAILWAY_DEPLOYMENT.md").read_text(encoding="utf-8")

    def test_container_runs_private_streamlit_entrypoint_on_external_interface(self):
        self.assertIn('CMD ["/app/docker-entrypoint.sh"]', self.dockerfile)
        self.assertIn("streamlit run private_app.py", self.docker_entrypoint)
        self.assertIn("--server.address=0.0.0.0", self.docker_entrypoint)
        self.assertIn('${PORT:-8501}', self.docker_entrypoint)

    def test_container_defaults_to_private_auth_and_persistent_data_dir(self):
        self.assertIn("KFIR_TOOLBOX_REQUIRE_AUTH=1", self.dockerfile)
        self.assertIn("KFIR_TOOLBOX_DATA_DIR=/data", self.dockerfile)
        self.assertIn("USER toolbox", self.dockerfile)
        self.assertIn("/_stcore/health", self.dockerfile)

    def test_runtime_entrypoint_materializes_oidc_secrets_from_environment(self):
        self.assertIn("KFIR_TOOLBOX_GOOGLE_CLIENT_ID", self.docker_entrypoint)
        self.assertIn("KFIR_TOOLBOX_GOOGLE_CLIENT_SECRET", self.docker_entrypoint)
        self.assertIn("KFIR_TOOLBOX_COOKIE_SECRET", self.docker_entrypoint)
        self.assertIn("RAILWAY_PUBLIC_DOMAIN", self.docker_entrypoint)
        self.assertIn("/oauth2callback", self.docker_entrypoint)
        self.assertIn("https://accounts.google.com/.well-known/openid-configuration", self.docker_entrypoint)
        self.assertIn('/app/.streamlit/secrets.toml', self.docker_entrypoint)

    def test_private_entrypoint_fails_closed_without_explicit_allowlist(self):
        self.assertIn("if not authentication_required():", self.private_app)
        self.assertIn("if not allowed_emails():", self.private_app)
        self.assertIn("require_authenticated_user(st)", self.private_app)
        self.assertIn("st.navigation", self.private_app)

    def test_private_entrypoint_exposes_logout_after_authentication(self):
        self.assertIn('st.button("Log out"', self.private_app)
        self.assertIn("st.logout()", self.private_app)

    def test_private_navigation_is_bound_to_authenticated_user_storage(self):
        self.assertIn("email = require_authenticated_user(st)", self.private_app)
        self.assertIn("with persistence_scope_for_email(email):", self.private_app)
        self.assertIn('root / "users" / storage_key', self.persistence)
        self.assertIn("hashlib.sha256", self.persistence)

    def test_container_does_not_copy_common_secret_files(self):
        self.assertIn(".streamlit/secrets.toml", self.dockerignore)
        self.assertIn(".env", self.dockerignore)
        self.assertIn(".kfir-toolbox/", self.dockerignore)

    def test_git_ignores_real_private_credentials(self):
        self.assertIn(".streamlit/secrets.toml", self.gitignore)
        self.assertIn(".env", self.gitignore)

    def test_google_oidc_template_contains_only_placeholders(self):
        self.assertIn("https://accounts.google.com/.well-known/openid-configuration", self.secrets_example)
        self.assertIn("https://YOUR_HOSTNAME/oauth2callback", self.secrets_example)
        self.assertIn("REPLACE_WITH_GOOGLE_CLIENT_ID", self.secrets_example)
        self.assertIn("REPLACE_WITH_GOOGLE_CLIENT_SECRET", self.secrets_example)
        self.assertNotIn("AIza", self.secrets_example)

    def test_private_deployment_checklist_requires_real_privacy_acceptance_tests(self):
        self.assertIn("Google", self.private_deployment)
        self.assertIn("Authorized redirect URIs", self.private_deployment)
        self.assertIn("KFIR_TOOLBOX_ALLOWED_EMAILS", self.private_deployment)
        self.assertIn("persistent private volume at `/data`", self.private_deployment)
        self.assertIn("authenticated but non-allowlisted Google account is denied", self.private_deployment)
        self.assertIn("should not be described as private until these checks pass", self.private_deployment)

    def test_render_blueprint_uses_private_container_and_persistent_disk(self):
        self.assertIn("runtime: docker", self.render_blueprint)
        self.assertIn("rootDir: electrical-engineering/design-checker", self.render_blueprint)
        self.assertIn("healthCheckPath: /_stcore/health", self.render_blueprint)
        self.assertIn("KFIR_TOOLBOX_REQUIRE_AUTH", self.render_blueprint)
        self.assertIn("KFIR_TOOLBOX_ALLOWED_EMAILS", self.render_blueprint)
        self.assertIn("sync: false", self.render_blueprint)
        self.assertIn("mountPath: /data", self.render_blueprint)
        self.assertIn("sizeGB: 1", self.render_blueprint)

    def test_railway_config_uses_dockerfile_healthcheck_and_free_safe_restart_policy(self):
        self.assertIn('"dockerfilePath": "Dockerfile"', self.railway_config)
        self.assertIn('"healthcheckPath": "/_stcore/health"', self.railway_config)
        self.assertIn('"restartPolicyType": "ON_FAILURE"', self.railway_config)
        self.assertIn('"restartPolicyMaxRetries": 10', self.railway_config)

    def test_railway_deployment_requires_persistent_volume_and_documents_permissions(self):
        self.assertIn("/electrical-engineering/design-checker", self.railway_deployment)
        self.assertIn("RAILWAY_RUN_UID=0", self.railway_deployment)
        self.assertIn("attach it to the Toolbox service at", self.railway_deployment)
        self.assertIn("`/data`", self.railway_deployment)
        self.assertIn("0.5 GB", self.railway_deployment)
        self.assertIn("Free plan allowance", self.railway_deployment)
        self.assertIn("rather than assumed", self.railway_deployment)

    def test_persistence_supports_private_hosted_data_mount(self):
        self.assertIn("KFIR_TOOLBOX_DATA_DIR", self.persistence)
        self.assertIn("toolbox_data_root()", self.persistence)


if __name__ == "__main__":
    unittest.main()
