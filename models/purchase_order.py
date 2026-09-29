from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """Receive spare parts straight into their configured sub-location (rack/shelf)."""
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        warehouse = picking.picking_type_id.warehouse_id
        if self.product_id and warehouse:
            part = self.env['fleet.spare.part'].sudo().search([
                ('product_id', '=', self.product_id.id),
                ('warehouse_id', '=', warehouse.id),
                ('location_id', '!=', False),
            ], limit=1)
            if part:
                vals['location_dest_id'] = part.location_id.id
        return vals
