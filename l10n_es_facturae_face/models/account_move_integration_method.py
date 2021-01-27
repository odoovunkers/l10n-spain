# © 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import base64

from odoo import _, exceptions, models


class AccountMoveIntegrationMethod(models.Model):
    _inherit = "account.move.integration.method"

    # Default values for integration. It could be extended
    def integration_values(self, move):
        res = super(AccountMoveIntegrationMethod, self).integration_values(move)
        if self.code == "FACe":
            if not move.company_id.facturae_cert:
                raise exceptions.UserError(_("Certificate must be added for company"))
            if not move.company_id.facturae_cert_password:
                raise exceptions.UserError(
                    _("Certificate password must be added for company")
                )
            move_file, file_name = move.get_facturae(True)
            attachment = (
                self.env["ir.attachment"]
                .sudo()
                .create(
                    {
                        "name": file_name,
                        "datas": base64.b64encode(move_file),
                        "store_fname": file_name,
                        "res_model": "account.move",
                        "res_id": move.id,
                        "mimetype": "application/xml",
                    }
                )
            )
            res["attachment_id"] = attachment.id
        return res
