from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied
from odoo.tests.common import TransactionCase


class TestLoginLockout(TransactionCase):

    def setUp(self):
        super().setUp()
        # Unique login per test to avoid cross-test collisions
        self.test_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Test Lockout User',
            'login': f'test_lockout_{self._testMethodName}',
            'password': 'TestPass123!',
            'groups_id': [
                (4, self.env.ref('inventory_smi.group_staf_produksi').id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def _user(self):
        return self.test_user.sudo()

    # --- Counter mechanics ---

    def test_record_failed_login_increments_counter(self):
        self._user()._smi_record_failed_login()
        self.assertEqual(self._user().smi_login_fail_count, 1)

    def test_record_failed_called_multiple_times(self):
        for _ in range(3):
            self._user()._smi_record_failed_login()
        self.assertEqual(self._user().smi_login_fail_count, 3)

    def test_4_failed_logins_no_lock(self):
        for _ in range(4):
            self._user()._smi_record_failed_login()
        self.assertFalse(self._user()._smi_is_locked())

    def test_5_failed_logins_locks_account(self):
        for _ in range(5):
            self._user()._smi_record_failed_login()
        self.assertTrue(self._user()._smi_is_locked())

    def test_5_failed_logins_sets_lock_until(self):
        for _ in range(5):
            self._user()._smi_record_failed_login()
        self.assertIsNotNone(self._user().smi_login_lock_until)

    def test_lock_until_is_approximately_10_minutes_from_now(self):
        for _ in range(5):
            self._user()._smi_record_failed_login()
        lock_until = self._user().smi_login_lock_until
        now = fields.Datetime.now()
        delta = lock_until - now
        # Should be between 9 and 11 minutes
        self.assertGreater(delta.total_seconds(), 9 * 60)
        self.assertLess(delta.total_seconds(), 11 * 60)

    # --- Lockout check ---

    def test_active_lock_returns_true(self):
        self._user().smi_login_lock_until = fields.Datetime.now() + timedelta(minutes=9)
        self.assertTrue(self._user()._smi_is_locked())

    def test_expired_lock_returns_false(self):
        self._user().smi_login_lock_until = fields.Datetime.now() - timedelta(seconds=1)
        self.assertFalse(self._user()._smi_is_locked())

    def test_no_lock_set_returns_false(self):
        self.assertFalse(self._user()._smi_is_locked())

    # --- Reset ---

    def test_reset_clears_fail_counter(self):
        for _ in range(3):
            self._user()._smi_record_failed_login()
        self._user()._smi_reset_login_fail()
        self.assertEqual(self._user().smi_login_fail_count, 0)

    def test_reset_clears_lock_until(self):
        for _ in range(5):
            self._user()._smi_record_failed_login()
        self._user()._smi_reset_login_fail()
        self.assertFalse(self._user().smi_login_lock_until)

    def test_reset_makes_not_locked(self):
        for _ in range(5):
            self._user()._smi_record_failed_login()
        self._user()._smi_reset_login_fail()
        self.assertFalse(self._user()._smi_is_locked())

    # --- _check_credentials integration ---

    def test_locked_user_raises_access_denied_before_password_check(self):
        """Even correct password is rejected while account is locked."""
        self._user().smi_login_lock_until = fields.Datetime.now() + timedelta(minutes=5)
        with self.assertRaises(AccessDenied):
            self.test_user._check_credentials('TestPass123!', {})

    def test_wrong_password_increments_fail_count(self):
        initial = self._user().smi_login_fail_count
        try:
            self.test_user._check_credentials('WrongPassword!', {})
        except AccessDenied:
            pass
        self._user().invalidate_recordset()
        self.assertEqual(self._user().smi_login_fail_count, initial + 1)

    def test_correct_password_resets_fail_count(self):
        """_check_credentials resets fail count when the parent succeeds.
        Patched because Odoo 17's password field returns '' in ORM context."""
        from unittest.mock import patch
        from odoo.addons.base.models import res_users as base_res_users
        self._user().smi_login_fail_count = 3
        with patch.object(base_res_users.Users, '_check_credentials', return_value=None):
            self.test_user._check_credentials('TestPass123!', {})
        self._user().invalidate_recordset()
        self.assertEqual(self._user().smi_login_fail_count, 0)


class TestPasswordExpiry(TransactionCase):

    def setUp(self):
        super().setUp()
        self.test_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Test Expiry User',
            'login': f'test_expiry_{self._testMethodName}',
            'password': 'TestPass123!',
            'groups_id': [
                (4, self.env.ref('inventory_smi.group_staf_produksi').id),
                (4, self.env.ref('base.group_user').id),
            ],
        })

    def _user(self):
        return self.test_user.sudo()

    def test_password_last_changed_set_on_create(self):
        self.assertIsNotNone(self._user().smi_password_last_changed)

    def test_fresh_password_not_expired(self):
        """User created just now should not need password change."""
        self.assertFalse(self._user().must_change_password)

    def test_password_at_89_days_not_expired(self):
        self._user().smi_password_last_changed = fields.Datetime.now() - timedelta(days=89)
        self.assertFalse(self._user().must_change_password)

    def test_password_at_90_days_is_expired(self):
        self._user().smi_password_last_changed = fields.Datetime.now() - timedelta(days=90)
        self.assertTrue(self._user().must_change_password)

    def test_password_at_91_days_is_expired(self):
        self._user().smi_password_last_changed = fields.Datetime.now() - timedelta(days=91)
        self.assertTrue(self._user().must_change_password)

    def test_must_change_password_false_when_recently_changed(self):
        self._user().smi_password_last_changed = fields.Datetime.now() - timedelta(days=30)
        self.assertFalse(self._user().must_change_password)


class TestLoginTemplate(TransactionCase):
    """Verify the login QWeb template has correct Indonesian content.
    Uses ORM-level template check to avoid port conflicts with the
    running Odoo web server during test execution.
    """

    def _get_template_arch(self):
        template = self.env.ref('inventory_smi.login_page')
        return template.arch or ''

    def test_login_template_exists(self):
        """Template inventory_smi.login_page is installed."""
        template = self.env.ref('inventory_smi.login_page', raise_if_not_found=False)
        self.assertIsNotNone(template)

    def test_login_template_has_indonesian_submit_button(self):
        """Template contains 'Masuk' as the submit button label."""
        self.assertIn('Masuk', self._get_template_arch())

    def test_login_template_has_smi_title(self):
        """Template contains the full system name in Indonesian."""
        self.assertIn('Sistem Manajemen Inventaris', self._get_template_arch())

    def test_login_template_has_login_input(self):
        """Template has an input field named 'login'."""
        self.assertIn('name="login"', self._get_template_arch())

    def test_login_template_has_password_input(self):
        """Template has an input field named 'password'."""
        self.assertIn('name="password"', self._get_template_arch())

    def test_login_template_has_csrf_token(self):
        """Template includes CSRF token for form security."""
        self.assertIn('csrf_token', self._get_template_arch())

    def test_login_template_posts_to_web_login(self):
        """Form action points to /web/login."""
        self.assertIn('/web/login', self._get_template_arch())
