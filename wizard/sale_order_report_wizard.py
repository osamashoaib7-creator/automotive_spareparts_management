import base64
import csv
from datetime import datetime, time
import io
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderReportWizard(models.TransientModel):
    _name = 'sale.order.report.wizard'
    _description = 'Sale Order Report Wizard'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_("From Date cannot be after To Date."))

    def _get_orders(self):
        self.ensure_one()
        # Date range filtering with full day coverage
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        start = tz.localize(datetime.combine(self.date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        end = tz.localize(datetime.combine(self.date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)

        return self.env['sale.order'].search([
            ('date_order', '>=', start),
            ('date_order', '<=', end),
        ], order='date_order desc, id desc')

    def action_view_orders(self):
        self.ensure_one()
        orders = self._get_orders()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
        }

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('automotive_spareparts_management.action_report_sale_order_pdf').report_action(self)

    def action_export_excel(self):
        self.ensure_one()
        orders = self._get_orders()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Header Row
        writer.writerow(['Order Ref', 'Date', 'Customer', 'Total Amount'])

        # Data Rows
        for o in orders:
            writer.writerow([
                o.name or '',
                str(o.date_order) if o.date_order else '',
                o.partner_id.name or '',
                o.amount_total or 0.0
            ])

        csv_data = output.getvalue().encode('utf-8')

        # Temporary Attachment Create Karein
        attachment = self.env['ir.attachment'].create({
            'name': f'Sale_Orders_{self.date_from}_to_{self.date_to}.csv',
            'datas': base64.b64encode(csv_data),
            'mimetype': 'text/csv',
            'res_model': self._name,
            'res_id': self.id,
        })

        # Browser Download URL Trigger Karein
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }