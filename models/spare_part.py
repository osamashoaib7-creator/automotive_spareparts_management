from odoo import models, fields

class FleetSparePart(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'fleet.spare.part'
    _description = 'Fleet Spare Part Details'

    name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number', required=True)
    price = fields.Float(string='Unit Price')
    quantity = fields.Integer(string='Quantity', default=1)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Assigned Vehicle', ondelete='cascade')