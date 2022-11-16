# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MusicSchoolSummaryReport(models.TransientModel):
    _name = 'music.school.summary.report'
    _description = 'Music School Summary Report'

    date_from = fields.Date(string='From', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(string='To', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    classes = fields.Many2many('student.class', 'summary_classes_rel', 'sum_id', 'class_id', string='Classes(s)')
    lesson_type = fields.Selection([
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('both', 'Both Started and Completed')
    ], string='Lesson Type', required=True, default='both')

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        if not data.get('classes'):
            raise UserError(_('You have to select at least one classes.'))
        classes = self.env['student.class'].browse(data['classes'])
        datas = {
            'ids': [],
            'model': 'student.class',
            'form': data
        }
        return self.env.ref('music_school.action_music_class_report').with_context(from_transient_model=True).report_action(classes, data=datas)