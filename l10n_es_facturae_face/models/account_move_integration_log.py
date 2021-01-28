# © 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


import base64
import logging

from odoo import models

from .wsse_signature import MemorySignature

try:
    from OpenSSL import crypto
    from zeep import Client
except (ImportError, IOError) as err:
    logging.info(err)

ns = "https://ssweb.seap.minhap.es/web-service-test-face/sspp"


class AccountMoveIntegration(models.Model):
    _inherit = "account.move.integration.log"

    def update_method(self):
        if self.integration_id.method_id == self.env.ref(
            "l10n_es_facturae_face.integration_face"
        ):
            move = self.integration_id.move_id
            cert = crypto.load_pkcs12(
                base64.b64decode(move.company_id.facturae_cert),
                move.company_id.facturae_cert_password,
            )
            cert.set_ca_certificates(None)
            client = Client(
                wsdl=self.env["ir.config_parameter"]
                .sudo()
                .get_param("account.move.face.server", default=None),
                wsse=MemorySignature(
                    cert.export(),
                    base64.b64decode(
                        self.env.ref("l10n_es_facturae_face.face_certificate").datas
                    ),
                ),
            )
            response = client.service.consultarFactura(
                self.integration_id.register_number
            )
            self.result_code = response.resultado.codigo
            self.log = response.resultado.descripcion
            if self.result_code == "0":
                self.state = "sent"
                factura = response.factura
                integ = self.integration_id
                integ.integration_status = "face-" + factura.tramitacion.codigo
                integ.integration_description = factura.tramitacion.motivo
                integ.cancellation_status = "face-" + factura.anulacion.codigo
                integ.cancellation_description = factura.anulacion.motivo
                if integ.cancellation_status != "face-4100":
                    integ.can_cancel = False
            else:
                self.state = "failed"
            return
        return super(AccountMoveIntegration, self).update_method()

    def cancel_method(self):
        if self.integration_id.method_id == self.env.ref(
            "l10n_es_facturae_face.integration_face"
        ):
            move = self.integration_id.move_id
            cert = crypto.load_pkcs12(
                base64.b64decode(move.company_id.facturae_cert),
                move.company_id.facturae_cert_password,
            )
            cert.set_ca_certificates(None)
            client = Client(
                wsdl=self.env["ir.config_parameter"]
                .sudo()
                .get_param("account.move.face.server", default=None),
                wsse=MemorySignature(
                    cert.export(),
                    base64.b64decode(
                        self.env.ref("l10n_es_facturae_face.face_certificate").datas
                    ),
                ),
            )
            response = client.service.anularFactura(
                self.integration_id.register_number, self.cancellation_motive
            )
            self.result_code = response.resultado.codigo
            self.log = response.resultado.descripcion
            if self.result_code == "0":
                self.state = "sent"
                self.integration_id.state = "cancelled"
                self.integration_id.can_cancel = False
            else:
                self.state = "failed"
            return
        return super(AccountMoveIntegration, self).cancel_method()

    def send_method(self):
        if self.integration_id.method_id == self.env.ref(
            "l10n_es_facturae_face.integration_face"
        ):
            move = self.integration_id.move_id
            cert = crypto.load_pkcs12(
                base64.b64decode(move.company_id.facturae_cert),
                move.company_id.facturae_cert_password,
            )
            cert.set_ca_certificates(None)
            client = Client(
                wsdl=self.env["ir.config_parameter"]
                .sudo()
                .get_param("account.move.face.server", default=None),
                wsse=MemorySignature(
                    cert.export(),
                    base64.b64decode(
                        self.env.ref("l10n_es_facturae_face.face_certificate").datas
                    ),
                ),
            )
            move_file = client.get_type("ns0:FacturaFile")(
                self.integration_id.attachment_id.datas,
                self.integration_id.attachment_id.store_fname,
                self.integration_id.attachment_id.mimetype,
            )
            anexos_list = []
            if self.integration_id.attachment_ids:
                for attachment in self.integration_id.attachment_ids:
                    anexo = client.get_type("ns0:AnexoFile")(
                        attachment.datas, attachment.store_fname, attachment.mimetype
                    )
                    anexos_list.append(anexo)
            anexos = client.get_type("ns0:ArrayOfAnexoFile")(anexos_list)
            move_call = client.get_type("ns0:EnviarFacturaRequest")(
                move.company_id.face_email, move_file, anexos
            )
            response = client.service.enviarFactura(move_call)
            self.result_code = response.resultado.codigo
            self.log = response.resultado.descripcion
            if self.result_code == "0":
                self.state = "sent"
                integ = self.integration_id
                integ.register_number = response.factura.numeroRegistro
                integ.state = "sent"
                integ.can_cancel = True
                integ.can_update = True
                integ.can_send = False
            else:
                self.integration_id.state = "failed"
                self.state = "failed"
            return
        return super(AccountMoveIntegration, self).send_method()
