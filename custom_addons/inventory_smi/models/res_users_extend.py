from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessDenied


class ResUsersExtend(models.Model):
    _inherit = 'res.users'

    smi_login_fail_count = fields.Integer(
        string='Jumlah Gagal Login', default=0, copy=False
    )
    smi_login_lock_until = fields.Datetime(
        string='Dikunci Sampai', copy=False
    )
    smi_password_last_changed = fields.Datetime(
        string='Password Terakhir Diganti',
        default=fields.Datetime.now,
        copy=False,
    )
    must_change_password = fields.Boolean(
        string='Wajib Ganti Password',
        compute='_compute_must_change_password',
    )

    @api.depends('smi_password_last_changed')
    def _compute_must_change_password(self):
        threshold = timedelta(days=90)
        now = fields.Datetime.now()
        for user in self:
            if not user.smi_password_last_changed:
                user.must_change_password = True
            else:
                user.must_change_password = (now - user.smi_password_last_changed) >= threshold

    # ------------------------------------------------------------------
    # Lockout helpers
    # ------------------------------------------------------------------

    def _smi_record_failed_login(self):
        """Increment fail counter; lock account at 5 failures."""
        self.ensure_one()
        self.smi_login_fail_count += 1
        if self.smi_login_fail_count >= 5:
            self.smi_login_lock_until = fields.Datetime.now() + timedelta(minutes=10)

    def _smi_reset_login_fail(self):
        """Clear fail counter and lock after successful login."""
        self.ensure_one()
        self.smi_login_fail_count = 0
        self.smi_login_lock_until = False

    def _smi_is_locked(self):
        """Return True if account is currently within the lockout window."""
        self.ensure_one()
        if self.smi_login_lock_until:
            return fields.Datetime.now() < self.smi_login_lock_until
        return False

    # ------------------------------------------------------------------
    # Override _check_credentials to enforce lockout only
    # Failure tracking is done in the controller (auth.py) so writes
    # are not rolled back by Odoo's authenticate() cursor management.
    # ------------------------------------------------------------------

    def _check_credentials(self, password, env):
        user_sudo = self.sudo()
        if user_sudo._smi_is_locked():
            raise AccessDenied()
        return super()._check_credentials(password, env)

    # ------------------------------------------------------------------
    # Track password change date
    # ------------------------------------------------------------------

    def write(self, vals):
        result = super().write(vals)
        # When password field is changed via write, update our timestamp
        if 'password' in vals:
            self.sudo().smi_password_last_changed = fields.Datetime.now()
        return result
