from odoo import models


class SaleOrderXlsxReport(models.AbstractModel):
    _name = 'report.automotive_spareparts_management.sale_order_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Sale Order Excel Report Generator'

    def generate_xlsx_report(self, workbook, data, wizards):
        for wizard in wizards:
            sheet = workbook.add_worksheet('Sale Orders')
            bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
            cell_format = workbook.add_format({'border': 1})
            currency_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})

            sheet.merge_range('A1:D1', f'Sale Orders ({wizard.date_from} to {wizard.date_to})', bold)

            headers = ['Order Ref', 'Date', 'Customer', 'Total Amount']
            for col, header in enumerate(headers):
                sheet.write(1, col, header, bold)

            orders = wizard._get_orders()
            row = 2
            for o in orders:
                sheet.write(row, 0, o.name, cell_format)
                sheet.write(row, 1, str(o.date_order), cell_format)
                sheet.write(row, 2, o.partner_id.name or '', cell_format)
                sheet.write(row, 3, o.amount_total, currency_format)
                row += 1

            sheet.set_column('A:D', 20)