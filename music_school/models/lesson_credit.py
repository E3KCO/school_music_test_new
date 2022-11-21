# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LessonCredit(models.Model):
    _name = "lesson.credit"
    _description = "Credit"

    name = fields.Char('name')
    class_id = fields.Many2one('student.class', string="Class ID")
    lesson_id = fields.Many2one('student.lesson', string="Lesson")
    student_id = fields.Many2one('music.student',string="Student")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    reported_start_date = fields.Datetime(string="Reported Start Date")
    reported_end_date = fields.Datetime(string="Reported End Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_repay', 'To repay'),
        ('postponed', 'Postponed'),
        ('refunded', 'Refunded')],
        'State',default='draft')


    def action_postponed(self):

        return {
            'name': _("Postponed Credit"),
            'view_mode': 'form',
            'view_id': self.env.ref('music_school.view_postponed_credit').id,
            'view_type': 'form',
            'res_model': 'postponed.credit',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_credit_id':self.id}
        }

    def action_to_repay(self):

        self.write({'state':'to_repay'})

    def action_refunded(self):
        self.write({'state': 'refunded'})