import json

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError


class SmiUserController(http.Controller):

    DEMO_PASSWORDS = {
        "admin_smi": "admin123",
        "rina_admin": "rina123",
        "kepala": "kepala123",
        "budi_kepala": "budi123",
        "staf1": "staf123",
        "andi_staf": "andi123",
        "sari_staf": "sari123",
        "dewi_staf": "dewi123",
        "rizal_staf": "rizal123",
        "direktur": "direktur123",
        "hendra_dir": "hendra123",
        "admin": "admin",
    }

    ROLE_GROUPS = [
        ("inventory_smi.group_admin", "Admin"),
        ("inventory_smi.group_kepala_produksi", "Kepala Produksi"),
        ("inventory_smi.group_staf_produksi", "Staf Produksi"),
        ("inventory_smi.group_direktur", "Direktur"),
    ]

    @http.route("/smi/pengguna", type="http", auth="user", website=False)
    def pengguna_page(self, search="", **kwargs):
        user = request.env.user
        if not user.has_group("inventory_smi.group_admin"):
            return request.redirect("/smi/dashboard")

        domain = [("share", "=", False), ("active", "=", True)]
        if search:
            domain.append(("name", "ilike", search))

        users = request.env["res.users"].search(domain, order="name asc")

        def get_role(u):
            for xml_id, label in self.ROLE_GROUPS:
                try:
                    if u.has_group(xml_id):
                        return label
                except Exception:
                    pass
            return "-"

        users_data = []
        for u in users:
            role = get_role(u)
            plain_pwd = u.sudo().smi_plain_password
            if not plain_pwd:
                plain_pwd = self.DEMO_PASSWORDS.get(u.login)
            password_missing = not bool(plain_pwd)
            users_data.append(
                {
                    "user": u,
                    "role": role,
                    "password": plain_pwd or "",
                    "password_missing": password_missing,
                }
            )

        values = {
            "users_data": users_data,
            "search": search,
            "is_direktur": user.has_group("inventory_smi.group_direktur"),
            "is_kepala": user.has_group("inventory_smi.group_kepala_produksi"),
            "is_admin": user.has_group("inventory_smi.group_admin"),
            "current_user": user,
            "active_menu": "pengguna",
            "page_title": "Manajemen Pengguna",
            "role_choices": [label for _, label in self.ROLE_GROUPS],
        }
        return request.render("inventory_smi.pengguna_page", values)

    @http.route(
        "/smi/pengguna/change_role",
        type="http",
        auth="user",
        methods=["POST"],
        website=False,
    )
    def change_role(self, **kwargs):
        user = request.env.user
        if not user.has_group("inventory_smi.group_admin"):
            raise AccessError("Hanya admin yang dapat mengubah role.")

        user_id = int(kwargs.get("user_id", 0))
        new_role = kwargs.get("new_role", "")

        if not user_id or not new_role:
            return request.redirect("/smi/pengguna")

        target_user = request.env["res.users"].sudo().browse(user_id)
        if not target_user.exists():
            return request.redirect("/smi/pengguna")

        if target_user.id == request.env.uid:
            return request.redirect("/smi/pengguna")

        group_xml_id = None
        for xml_id, label in self.ROLE_GROUPS:
            if label == new_role:
                group_xml_id = xml_id
                break

        if not group_xml_id:
            return request.redirect("/smi/pengguna")

        all_group_xml_ids = [xml_id for xml_id, _ in self.ROLE_GROUPS]
        target_groups = request.env["res.groups"].sudo()
        for gid in all_group_xml_ids:
            group = request.env.ref(gid)
            target_groups |= group

        smi_category = request.env.ref("inventory_smi.module_category_smi")
        current_smi_groups = target_user.groups_id.filtered(
            lambda g: g.category_id.id == smi_category.id
        )

        new_group = request.env.ref(group_xml_id)

        target_user.sudo().write(
            {
                "groups_id": [(3, gid.id) for gid in current_smi_groups]
                + [(4, new_group.id)],
            }
        )

        return request.redirect("/smi/pengguna")
