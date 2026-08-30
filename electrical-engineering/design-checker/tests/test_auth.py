import unittest

from src.auth import allowed_emails, authentication_required, require_authenticated_user


class _StopCalled(RuntimeError):
    pass


class _FakeUser:
    def __init__(self, logged_in=False, email=None):
        self.is_logged_in = logged_in
        self._email = email

    def to_dict(self):
        return {"email": self._email} if self._email is not None else {}


class _FakeStreamlit:
    def __init__(self, user=None):
        self.user = user
        self.login = lambda: None
        self.logout = lambda: None
        self.errors = []
        self.buttons = []

    def error(self, message):
        self.errors.append(message)

    def button(self, label, **kwargs):
        self.buttons.append((label, kwargs))
        return False

    def stop(self):
        raise _StopCalled()


class AuthTests(unittest.TestCase):
    def test_authentication_is_opt_in(self):
        self.assertFalse(authentication_required({}))
        self.assertTrue(authentication_required({"KFIR_TOOLBOX_REQUIRE_AUTH": "1"}))
        self.assertTrue(authentication_required({"KFIR_TOOLBOX_REQUIRE_AUTH": "TRUE"}))

    def test_email_allowlist_is_normalized(self):
        self.assertEqual(
            allowed_emails({"KFIR_TOOLBOX_ALLOWED_EMAILS": " One@Example.com, two@example.com "}),
            frozenset({"one@example.com", "two@example.com"}),
        )

    def test_local_mode_does_not_touch_auth_api(self):
        self.assertIsNone(require_authenticated_user(object(), {}))

    def test_private_mode_stops_anonymous_user(self):
        st = _FakeStreamlit(_FakeUser(logged_in=False))
        with self.assertRaises(_StopCalled):
            require_authenticated_user(st, {"KFIR_TOOLBOX_REQUIRE_AUTH": "1"})
        self.assertEqual(st.buttons[0][0], "Log in")

    def test_private_mode_accepts_allowlisted_email(self):
        st = _FakeStreamlit(_FakeUser(logged_in=True, email="Owner@Example.com"))
        email = require_authenticated_user(
            st,
            {
                "KFIR_TOOLBOX_REQUIRE_AUTH": "1",
                "KFIR_TOOLBOX_ALLOWED_EMAILS": "owner@example.com",
            },
        )
        self.assertEqual(email, "owner@example.com")

    def test_private_mode_rejects_authenticated_non_allowlisted_email(self):
        st = _FakeStreamlit(_FakeUser(logged_in=True, email="other@example.com"))
        with self.assertRaises(_StopCalled):
            require_authenticated_user(
                st,
                {
                    "KFIR_TOOLBOX_REQUIRE_AUTH": "1",
                    "KFIR_TOOLBOX_ALLOWED_EMAILS": "owner@example.com",
                },
            )
        self.assertIn("not authorized", st.errors[0])
        self.assertEqual(st.buttons[0][0], "Log out")


if __name__ == "__main__":
    unittest.main()
