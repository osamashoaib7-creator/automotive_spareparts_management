from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', copy=False, index='btree_not_null')
