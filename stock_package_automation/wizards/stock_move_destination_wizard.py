from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMoveDestinationWizardLine(models.TransientModel):
    _name = 'stock.move.destination.wizard.line'
    _description = 'Stock Move Destination Wizard Line'

    wizard_id = fields.Many2one(
        'stock.move.destination.wizard',
        string='Wizard',
        ondelete='cascade'
    )
    
    move_line_id = fields.Many2one(
        'stock.move.line',
        string='Move Line',
        readonly=True
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True,
        related='move_line_id.product_id'
    )
    
    quantity = fields.Float(
        string='Quantity',
        readonly=True,
        related='move_line_id.quantity'
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        readonly=True,
        related='move_line_id.product_uom_id'
    )
    
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Current Destination',
        required=True
    )
    
    new_location_dest_id = fields.Many2one(
        'stock.location',
        string='New Destination',
        required=True
    )


class StockMoveDestinationWizard(models.TransientModel):
    _name = 'stock.move.destination.wizard'
    _description = 'Stock Move Destination Wizard'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        readonly=True
    )
    
    wizard_line_ids = fields.One2many(
        'stock.move.destination.wizard.line',
        'wizard_id',
        string='Items'
    )

    @api.model
    def default_get(self, fields_list):
        """
        تحضير البيانات الافتراضية للـ wizard من الـ picking المختار
        """
        result = super().default_get(fields_list)
        
        # الحصول على الـ picking من السياق
        picking_id = self.env.context.get('active_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            result['picking_id'] = picking_id
            
            # إنشاء lines للـ wizard من move lines الـ picking
            wizard_lines = []
            for move_line in picking.move_line_ids:
                if move_line.product_id:
                    wizard_lines.append((0, 0, {
                        'move_line_id': move_line.id,
                        'location_dest_id': move_line.location_dest_id.id,
                        'new_location_dest_id': move_line.location_dest_id.id,
                    }))
            
            result['wizard_line_ids'] = wizard_lines
        
        return result

    def action_apply_changes(self):
        """
        تطبيق التغييرات على وجهات المنتجات
        """
        for line in self.wizard_line_ids:
            if line.move_line_id and line.new_location_dest_id:
                # تحديث location_dest_id للـ move line
                line.move_line_id.location_dest_id = line.new_location_dest_id.id
                
                # إذا كان لدينا move مرتبط، نحدثه أيضاً
                if line.move_line_id.move_id:
                    line.move_line_id.move_id.location_dest_id = line.new_location_dest_id.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم تحديث الوجهات',
                'message': 'تم تحديث وجهات المنتجات بنجاح',
                'type': 'success',
                'sticky': False,
            }
        }
