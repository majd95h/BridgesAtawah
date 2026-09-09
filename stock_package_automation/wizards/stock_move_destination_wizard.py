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
        readonly=True
    )
    
    new_location_dest_id = fields.Many2one(
        'stock.location',
        string='New Destination',
        required=False
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
                    # الحصول على الموقع الحالي
                    current_location = move_line.location_dest_id
                    new_location = move_line.location_dest_id or picking.location_dest_id
                    
                    wizard_lines.append((0, 0, {
                        'move_line_id': move_line.id,
                        'location_dest_id': current_location.id if current_location else None,
                        'new_location_dest_id': new_location.id if new_location else None,
                    }))
            
            result['wizard_line_ids'] = wizard_lines
        
        return result

    def action_apply_changes(self):
        """
        تطبيق التغييرات على وجهات المنتجات و packages
        """
        if not self.wizard_line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تنبيه',
                    'message': 'لا توجد عناصر للتحديث',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        count = 0
        for line in self.wizard_line_ids:
            try:
                if not line.move_line_id:
                    continue
                
                if not line.new_location_dest_id:
                    continue
                
                # تحديث location_dest_id
                line.move_line_id.write({
                    'location_dest_id': line.new_location_dest_id.id,
                })
                
                # إنشاء/تحديث package بناءً على الموقع الجديد
                location_name = line.new_location_dest_id.name or 'pkg'
                new_package_name = f"pkg_{location_name.replace(' ', '_')}_{line.move_line_id.id}"
                
                existing_package = self.env['stock.package'].search(
                    [('name', '=', new_package_name)],
                    limit=1
                )
                
                if not existing_package:
                    new_package = self.env['stock.package'].create({
                        'name': new_package_name,
                    })
                else:
                    new_package = existing_package
                
                # تحديث result_package_id
                line.move_line_id.write({
                    'result_package_id': new_package.id,
                    'location_dest_id': line.new_location_dest_id.id,
                })
                
                # تحديث move إذا وجد
                if line.move_line_id.move_id:
                    line.move_line_id.move_id.write({
                        'location_dest_id': line.new_location_dest_id.id,
                    })
                
                count += 1
                _logger.info(f"Updated move line {line.move_line_id.id} with package {new_package_name}")
                
            except Exception as e:
                _logger.error(f"Error updating line: {str(e)}")
                continue
        
        message = f"تم تحديث {count} عنصر بنجاح"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم التحديث',
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }