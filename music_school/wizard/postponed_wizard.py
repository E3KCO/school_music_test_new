# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MusicSchoolSummaryReport(models.TransientModel):
    _name = 'postponed.credit'
    _description = 'Postponed Credit'

    credit_id = fields.Many2one('lesson.credit' , string="credit Id")
    next_start_date = fields.Datetime(string="Start Date")
    next_end_date = fields.Datetime(string="End Date")



    def action_create_new_lesson(self):
        print('action_create_new_lesson')
        lesson_copy = self.credit_id.lesson_id.copy()
        lesson_copy.write({'name':lesson_copy.name + 'Reporté',
                           'start_date':self.next_start_date,
                           'end_date':self.next_end_date,
                           'state':'draft'})
        self.credit_id.state = 'postponed'
        return {
            'name': _('Lessons'),
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_id': lesson_copy.id,
            'res_model': 'student.lesson',
            'views': [(False, "form")],

        }