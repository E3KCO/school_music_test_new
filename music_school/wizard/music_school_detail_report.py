# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MusicSchoolSummaryReport(models.TransientModel):
    _name = 'music.school.detail.report'
    _description = 'Music School Detail Report'

    def _get_default_date_from(self):
        return self.env['student.class'].browse(self._context.get('active_id',False)).start_date

    def _get_default_date_to(self):
        return self.env['student.class'].browse(self._context.get('active_id',False)).end_date

    def _get_default_classes(self):
        return self.env['student.class'].browse(self._context.get('active_id',False)).ids

    def _get_default_lesson_type(self):
        if self.env['student.class'].browse(self._context.get('active_id',False)).state in ['draft','cancelled']:
            raise ValidationError(_('You cannot take report if class is in Draft or Cancelled.'))
        return self.env['student.class'].browse(self._context.get('active_id',False)).state

    date_from = fields.Date(string='From', required=True, default=_get_default_date_from)
    date_to = fields.Date(string='To', required=True, default=_get_default_date_to)
    classes = fields.Many2many('student.class', 'music_detail_classes_rel', 'detail_id', 'class_id', string='Classes(s)', default=_get_default_classes)
    lesson_type = fields.Selection([
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('both', 'Both Started and Completed')
    ], string='Lesson Type', required=True, default=_get_default_lesson_type)

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