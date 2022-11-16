# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
import logging
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DrivingSchoolReportSummary(models.AbstractModel):
    _name = 'report.music_school.music_class_report_summary'

    def _get_header_info(self, start_date, end_date, lesson_type):
        st_date = fields.Date.from_string(start_date)
        et_date = fields.Date.from_string(end_date)
        return {
            'start_date': fields.Date.to_string(st_date),
            'end_date': fields.Date.to_string(et_date),
            'lesson_type': lesson_type
        }

    def _get_day(self, start_date, end_date):
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        total_days = (end_date - start_date).days + 1
        for x in range(0, total_days):
            color = '#ababab'
            res.append({'day_str': start_date.strftime('%a'), 'day': start_date.day , 'color': color})
            start_date = start_date + relativedelta(days=1)
        return res

    def _get_lesson_day(self, start_date, end_date, all_class, lesson_type):
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        total_days = (end_date - start_date).days + 1
        for index in range(0, total_days):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color': '', 'lesson': ''})
        if lesson_type == 'both':
            lesson_type = ['started','completed']
        else:
            lesson_type = [lesson_type]
        holidays = self.env['student.lesson.track'].search([
            ('class_id', '=', all_class.id), ('state', 'in', lesson_type),('start_date', '<=', str(end_date)),
            ('end_date', '>=', str(start_date))])
        for holiday in holidays:
            # Convert date to user timezone, otherwise the report will not be consistent with the
            # value displayed in the interface.
            date_from = fields.Datetime.from_string(holiday.start_date)
            date_from = fields.Datetime.context_timestamp(holiday, date_from).date()
            date_to = fields.Datetime.from_string(holiday.end_date)
            date_to = fields.Datetime.context_timestamp(holiday, date_to).date()
            for index in range(0, ((date_to - date_from).days + 1)):
                if date_from >= start_date and date_from <= end_date:
                    res[(date_from - start_date).days]['color'] = '#aeb2ae'
        return res

    def _get_months(self, start_date, end_date):
        # it works for geting month name between two dates.
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        while start_date <= end_date:
            last_date = start_date + relativedelta(day=1, months=+1, days=-1)
            if last_date > end_date:
                last_date = end_date
            month_days = (last_date - start_date).days + 1
            res.append({'month_name': start_date.strftime('%B'), 'days': month_days})
            start_date += relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, start_date, end_date, student_id, lesson_type, all_student_classes):
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = fields.Date.from_string(end_date)
        total_days = (end_date - start_date).days + 1
        for index in range(0, total_days):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color': '', 'lesson': ''})
        # count and get leave summary details.
        if lesson_type == 'both':
            lesson_type = ['started','completed']
        else:
            lesson_type = [lesson_type]
        holidays = self.env['student.lesson.track'].search([
            ('class_id', '=', all_student_classes.id), ('state', 'in', lesson_type),
             ('start_date', '<=', str(end_date)),
            ('end_date', '>=', str(start_date)),('student_id','=',student_id)])
        _logger.info(holidays)
        for holiday in holidays:
            # Convert date to user timezone, otherwise the report will not be consistent with the
            # value displayed in the interface.
            date_from = fields.Datetime.from_string(holiday.start_date)
            date_from = fields.Datetime.context_timestamp(holiday, date_from).date()
            date_to = fields.Datetime.from_string(holiday.end_date)
            date_to = fields.Datetime.context_timestamp(holiday, date_to).date()
            for index in range(0, ((date_to - date_from).days + 1)):
                if date_from >= start_date and date_from <= end_date:
                    if holiday.attendance == 'absent':
                        _logger.info('Coming For Absent Record')
                        _logger.info(holiday.attendance)
                        res[(date_from - start_date).days]['color'] = '#ff0000'
                        res[(date_from - start_date).days]['lesson'] = 'A'
                    if holiday.attendance == 'present':
                        _logger.info('Coming For Present Record')
                        _logger.info(holiday.attendance)
                        res[(date_from - start_date).days]['color'] = '#44e941'
                        res[(date_from - start_date).days]['lesson'] = 'P'
                    if not holiday.attendance:
                        res[(date_from - start_date).days]['color'] = ''
                date_from += timedelta(1)
        return res

    def _get_data_from_report(self, data):
        res = []
        _logger.info('Report calling >>>>>>>>>>>>>>>>>>>>>>>>>')
        if 'classes' in data:
            _logger.info('Coming for Loop before >>>>>>>>>>>>>>>>>>>>>>>>>')
            for all_student_classes in self.env['student.class'].browse(data['classes']):
                _logger.info('Coming Inside Classes >>>>>>>>>>>>>>>>>>>>>>>>>')
                res.append({'classes' : all_student_classes.name, 'data': [], 'color': self._get_lesson_day(data['date_from'], data['date_to'], all_student_classes, data['lesson_type'])})
                for student in all_student_classes.student_ids:
                    _logger.info('Coming Inside Students >>>>>>>>>>>>>>>>>>>>>>>>>')
                    res[len(res)-1]['data'].append({
                        'student': student.name,
                        'display': self._get_leaves_summary(data['date_from'],data['date_to'], student.id, data['lesson_type'], all_student_classes),
                    })
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        _logger.info('Report Is Working >>>>>>>>>>>>>>>>>>>>>>>>>')
        holidays_report = self.env['ir.actions.report']._get_report_from_name('driving_school.driving_class_report_summary')
        holidays = self.env['student.class'].browse(self.ids)
        return {
            'doc_ids': self.ids,
            'doc_model': holidays_report.model,
            'docs': holidays,
            'get_header_info': self._get_header_info(data['form']['date_from'],data['form']['date_to'], data['form']['lesson_type']),
            'get_day': self._get_day(data['form']['date_from'],data['form']['date_to']),
            'get_months': self._get_months(data['form']['date_from'], data['form']['date_to']),
            'get_data_from_report': self._get_data_from_report(data['form']),
        }