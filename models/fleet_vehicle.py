from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    spare_part_ids = fields.One2many(comodel_name='fleet.spare.part', inverse_name='vehicle_id', string='Spare Parts')
    spare_part_count = fields.Integer(compute='_compute_spare_part_count')
    sale_order_ids = fields.One2many('sale.order', 'fleet_vehicle_id', string='Spare Part Quotations')
    sale_order_count = fields.Integer(compute='_compute_sale_order_count')

    @api.depends('spare_part_ids')
    def _compute_spare_part_count(self):
        for rec in self:
            rec.spare_part_count = len(rec.spare_part_ids)

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = len(rec.sale_order_ids)

    def action_create_spare_part_quotation(self):
        """Quotation for the vehicle's driver/customer with all assigned spare parts."""
        self.ensure_one()
        parts = self.spare_part_ids.filtered(lambda p: p.quantity > 0 and p.product_id)
        if not parts:
            raise UserError(_("This vehicle has no spare parts to quote."))
        partner = self.driver_id or self.future_driver_id
        if not partner:
            raise UserError(_("Set a Driver on the vehicle: the quotation is addressed to the driver."))
        warehouse = parts[:1].warehouse_id
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'fleet_vehicle_id': self.id,
            'warehouse_id': warehouse.id or False,
            'order_line': [(0, 0, {
                'product_id': p.product_id.id,
                'product_uom_qty': p.quantity,
                'price_unit': p.price,
            }) for p in parts],
        })
        return {
            'type': 'ir.actions.act_window', 'name': _('Quotation'),
            'res_model': 'sale.order', 'res_id': order.id, 'view_mode': 'form',
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Quotations'),
            'res_model': 'sale.order', 'view_mode': 'list,form',
            'domain': [('fleet_vehicle_id', '=', self.id)],
        }
