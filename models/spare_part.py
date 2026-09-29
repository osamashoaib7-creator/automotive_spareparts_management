from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class FleetSparePart(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'fleet.spare.part'
    _description = 'Fleet Spare Part Details'

    name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number', required=True)
    price = fields.Float(string='Unit Price')
    quantity = fields.Integer(string='Quantity', default=1)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Assigned Vehicle', ondelete='cascade')

    # --- Inventory / procurement integration ---
    product_id = fields.Many2one(
        'product.product', string='Product', copy=False, index=True,
        help="Storable product behind this spare part. Created automatically if left empty.")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1))
    location_id = fields.Many2one(
        'stock.location', string='Storage Location',
        domain="[('usage', '=', 'internal'), ('warehouse_id', '=', warehouse_id)]",
        help="Sub-location inside the warehouse (rack / shelf / bin).")
    vendor_id = fields.Many2one('res.partner', string='Preferred Vendor')
    on_hand_qty = fields.Float(
        string='On Hand', compute='_compute_on_hand_qty', digits='Product Unit')
    available_qty = fields.Float(
        string='Available', compute='_compute_on_hand_qty', digits='Product Unit')

    _part_number_company_uniq = models.Constraint(
        'unique(part_number, company_id)',
        'Part number must be unique per company.')

    # ------------------------------------------------------------------
    @api.constrains('warehouse_id', 'location_id')
    def _check_location_in_warehouse(self):
        for rec in self:
            if rec.location_id and rec.warehouse_id:
                view = rec.warehouse_id.view_location_id
                if not rec.location_id.parent_path.startswith(view.parent_path):
                    raise ValidationError(_(
                        "Location %(loc)s is not inside warehouse %(wh)s.",
                        loc=rec.location_id.complete_name, wh=rec.warehouse_id.name))

    @api.constrains('quantity')
    def _check_quantity(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError(_("Quantity cannot be negative."))

    @api.depends('product_id', 'warehouse_id', 'location_id')
    def _compute_on_hand_qty(self):
        for rec in self:
            rec.on_hand_qty = rec.available_qty = 0.0
            if not rec.product_id:
                continue
            location = rec.location_id or rec.warehouse_id.lot_stock_id
            if not location:
                continue
            # stock figures are informational: fleet users have no stock access rights
            product = rec.product_id.sudo()
            if rec.warehouse_id:
                product = product.with_context(warehouse_id=rec.warehouse_id.id)
            product = product.with_context(location=location.id)
            rec.on_hand_qty = product.qty_available
            rec.available_qty = product.free_qty

    # ------------------------------------------------------------------
    def _prepare_product_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'default_code': self.part_number,
            'type': 'consu',
            'is_storable': True,
            'list_price': self.price,
            'standard_price': self.price,
            'sale_ok': True,
            'purchase_ok': True,
            'company_id': self.company_id.id or False,
        }

    def _link_or_create_product(self):
        Product = self.env['product.product'].sudo().with_context(active_test=False)
        for rec in self.filtered(lambda r: not r.product_id):
            product = Product.search([
                ('default_code', '=', rec.part_number),
                ('company_id', 'in', [False, rec.company_id.id]),
            ], limit=1)
            rec.product_id = product or self.env['product.product'].sudo().create(rec._prepare_product_vals())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._link_or_create_product()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'price' in vals:
            for rec in self.filtered('product_id'):
                upd = {}
                if 'name' in vals:
                    upd['name'] = rec.name
                if 'price' in vals:
                    upd['list_price'] = rec.price
                rec.product_id.sudo().write(upd)
        return res

    # ------------------------------------------------------------------
    def action_create_purchase_order(self):
        """One RFQ per preferred vendor for the selected parts, receiving into the part's warehouse."""
        parts = self.filtered(lambda p: p.quantity > 0)
        if not parts:
            raise UserError(_("Nothing to order."))
        missing = parts.filtered(lambda p: not p.vendor_id)
        if missing:
            raise UserError(_("Set a Preferred Vendor on: %s", ', '.join(missing.mapped('name'))))
        orders = self.env['purchase.order']
        for (vendor, warehouse), group in self._group_parts(parts, 'vendor_id'):
            picking_type = warehouse.in_type_id
            order = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'picking_type_id': picking_type.id,
                'order_line': [(0, 0, {
                    'product_id': p.product_id.id,
                    'name': p.name,
                    'product_qty': p.quantity,
                    'price_unit': p.price,
                }) for p in group],
            })
            orders |= order
        return self._open_records(orders, _('Requests for Quotation'))

    def _group_parts(self, parts, key):
        groups = {}
        for p in parts:
            groups.setdefault((p[key], p.warehouse_id), self.browse())
            groups[(p[key], p.warehouse_id)] |= p
        return groups.items()

    @api.model
    def _open_records(self, records, title):
        action = {
            'type': 'ir.actions.act_window', 'name': title,
            'res_model': records._name, 'domain': [('id', 'in', records.ids)],
            'view_mode': 'list,form',
        }
        if len(records) == 1:
            action.update(view_mode='form', res_id=records.id, domain=[])
        return action
