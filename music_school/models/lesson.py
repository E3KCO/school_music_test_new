# -*- coding: utf-8 -*-

###############################################################################

import logging
from odoo.exceptions import Warning
from odoo import models, fields, api, _
from datetime import datetime
from datetime import time as datetime_time
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from datetime import timedelta
from re import findall as regex_findall
from re import split as regex_split
_logger = logging.getLogger(__name__)

class CustomerInvoice(models.Model):
    _inherit = 'account.move'

    class_id = fields.Many2one('student.class', string='Driving Class')

class Employee(models.Model):
    _inherit = 'hr.employee'

    is_teacher = fields.Boolean(string='Is a Teacher')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_teacher = fields.Boolean(string='Is a Teacher')

class StudentClass(models.Model):
    _name = 'student.class'
    _description = 'Student Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    equipment_id = fields.Many2one('maintenance.equipment', 'Instrument')
    color = fields.Integer(string='Color Index', help='This color will be used in the kanban view.', track_visibility='onchange')
    start_date = fields.Datetime(string="Start Date", track_visibility='onchange')
    end_date = fields.Datetime(string="End Date", track_visibility='onchange')
    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company, track_visibility='onchange')
    name = fields.Char('Name', required=True, track_visibility='onchange')
    # instructor = fields.Many2one('hr.employee', string='Teacher', track_visibility='onchange')
    partner_instructor = fields.Many2one('res.partner', string='Teacher Partner',track_visibility='onchange')
    service_id = fields.Many2one('product.product', string="Service", track_visibility='onchange', domain="[('type','=','service')]")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('started', 'Started'),('completed', 'completed'),('cancelled', 'Cancelled')], 'status', default='draft', required=True, track_visibility='onchange')
    lesson_ids = fields.One2many('student.lesson','class_id', string="Class IDs")
    location = fields.Many2one('music.location', string="Location", track_visibility='onchange')
    available_spaces = fields.Char('Available Spaces', track_visibility='onchange')
    repeat = fields.Selection([('daily', 'Daily'),('weekly', 'Weekly'),('monthly', 'Monthly')], 'Repeats',default="daily", required=True, track_visibility='onchange')
    repeat_ends = fields.Selection([('on', 'on')],default="on",string='Repeat Ends', required=True, track_visibility='onchange')
    end_date = fields.Datetime(string="End Date", required=True)
    sunday = fields.Boolean('Sunday')
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    monthly_dates = fields.One2many('month.days', 'class_id')
    invoice_ids = fields.One2many('account.move', 'class_id')
    invoice_count = fields.Float('Invoice count', compute='compute_lesson_count')
    lesson_count = fields.Float('Lesson ount', compute='compute_lesson_count')
    student_ids = fields.Many2many('music.student', 'music_student_class_info_rel', 'class_id', 'student_id', 'Students')



    def write(self, vals):
        res = super(StudentClass, self).write(vals)
        # if 'available_spaces' in vals or self.available_spaces:
        #     print('len(self.student_ids)',len(self.student_ids))
        #     print('int(self.available_spaces)',int(self.available_spaces))
        #     if  len(self.student_ids) > int(self.available_spaces) :
        #         raise UserError('la capacité maximale des places est atteinte')
        if 'student_ids' in vals:
            self.update_students_ids()
        return res

    @api.onchange('student_ids')
    def check_available_places(self):
        if self.available_spaces:
            if  len(self.student_ids) > int(self.available_spaces) :
                raise UserError('la capacité maximale des places est atteinte')


    def update_students_ids(self):

        filtered_lesson = self.lesson_ids.filtered(lambda r:r.state not in ['started','completed', 'cancelled'])
        student_in_lesson = filtered_lesson.mapped('student_ids').ids
        list_difference = [element for element in self.student_ids.ids if element not in student_in_lesson]
        student_to_delete_from_lesson = [element for element in student_in_lesson if element not in self.student_ids.ids]
        if student_to_delete_from_lesson:
            for lesson in filtered_lesson:
                for std in student_to_delete_from_lesson:
                    student_obj = self.env['music.student'].browse(std)
                    lesson._origin.student_ids -= student_obj
                    track_to_delete = self.env['student.lesson.track'].search([('student_id','=',std),('lesson_id','=',lesson._origin.id)])
                    track_to_delete.unlink()

        for lesson in filtered_lesson:
            for diff in list_difference:
                if diff not in lesson.student_ids.ids:
                    student_obj = self.env['music.student'].browse(diff)
                    lesson._origin.student_ids += student_obj
                    track =self.env['student.lesson.track'].create({
                        'name': lesson._origin.name,
                        'start_date': lesson._origin.start_date,
                        'end_date': lesson._origin.end_date,
                        # 'instructor': class_info.instructor.id,
                        'partner_instructor': lesson._origin.partner_instructor.id,
                        'service_id': lesson._origin.service_id.id,
                        'state': 'draft',
                        'student_id':diff,
                        'class_id': lesson._origin.class_id.id,
                        'lesson_id': lesson._origin.id,
                    })

    def lesson_complete(self):
        self.write({'state':'completed'})

    def lesson_start(self):
        self.write({'state':'started'})
        for lesson in self.lesson_ids:
            lesson.confirm_lesson()

    def lesson_cancel(self):
        self.write({'state':'cancelled'})

    def create_invoice(self):
        for student in self.student_ids:
            line = []
            if self.service_id.property_account_income_id.id:
                income_account = self.service_id.property_account_income_id.id
            elif self.service_id.categ_id.property_account_income_categ_id.id:
                income_account = self.service_id.categ_id.property_account_income_categ_id.id
            else:
                raise UserError(_('Please define income '
                                  'account for this product: "%s" (id:%d).')
                                % (self.service_id.name, self.service_id.id))
            line.append((0, 0, {'name': str(self.lesson_count) +' '+self.service_id.name,
                                # 'origin': self.name,
                                'account_id': income_account,
                                'quantity': self.lesson_count,
                                'price_unit': self.service_id.lst_price,
                                'product_id': self.service_id.id,
                                'price_subtotal': self.lesson_count * self.service_id.lst_price,
                                }))

            self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': student.partner_id.id,
                # 'account_id': student.partner_id.property_account_receivable_id.id,
                'invoice_line_ids': line,
                'class_id': self.id,
            })

        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', self.invoice_ids.ids)],
            "name": "Customer Invoices",
            'view_mode': 'tree,form',
        }
        return result

    def view_lesson(self):
        return {
            'name': _('Lessons'),
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'res_model': 'student.lesson',
            'domain': [('id', 'in', self.lesson_ids.ids)],
        }

    def button_customer_invoices(self):
        invoices = self.env['account.move'].sudo().search([('class_id', '=', self.id), ('move_type', '=', 'out_invoice')])
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def compute_lesson_count(self):
        for line in self:
            payment_count = 0
            line.lesson_count = len(line.lesson_ids)
            line.invoice_count = len(line.invoice_ids)

class StudentLesson(models.Model):
    _name = 'student.lesson'
    _description = 'Student Lesson'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    student_ids = fields.Many2many('music.student', 'music_student_lesson_rel', 'class_id', 'student_id', 'Students',track_visibility='onchange')
    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    start_date = fields.Datetime(string="Start Time", required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    end_date = fields.Datetime(string="End Time", required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    # instructor = fields.Many2one('hr.employee', string='Teacher', readonly=True, required=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('started', 'Started'),

        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')],
        'State', default='draft', required=True, track_visibility='onchange')
    class_id = fields.Many2one('student.class', string="Class ID")
    service_id = fields.Many2one('product.product', string="Service", readonly=True, required=True,  domain="[('type','=','service')]", states={'draft': [('readonly', False)]}, track_visibility='onchange')
    color = fields.Integer(string='Color Index', help='This color will be used in the kanban view.')
    attendance_ids = fields.One2many('lesson.attendance', 'lesson_id', string="Attendance", readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    track_ids = fields.One2many('student.lesson.track','lesson_id', track_visibility='onchange')
    number_of_days = fields.Float(string='Number of Days')
    equipment_id = fields.Many2one('maintenance.equipment', 'Instrument')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)
    lesson_duration = fields.Float('lesson duration' ,compute='_get_lesson_duration')
    partner_instructor = fields.Many2one('res.partner', string='Teacher Partner', readonly=True, required=True, states={'draft': [('readonly', False)]},track_visibility='onchange')
    duration = fields.Float('Duration (h)' ,compute='_get_lesson_duration')

    def start_lesson_by_lots(self):
        for rec in self:
            rec.lesson_start()

    def cancel_lesson_by_lots(self):
        for rec in self:
            rec.lesson_cancel()

    def complete_lesson_by_lots(self):
        for rec in self:
            rec.lesson_complete()

    def _get_lesson_duration(self):
        for rec in self:
            rec.lesson_duration = 0.0
            diff_of_date = (rec.end_date - rec.start_date).total_seconds() / 60.0
            rec.lesson_duration = diff_of_date
            rec.duration = diff_of_date / 60

    def confirm_lesson(self):
        self.write({'state': 'confirmed'})

    def lesson_start(self):
        for line in self.student_ids:
            _logger.info(line.id)
            self.env['lesson.attendance'].create({'student_id':line.id, 'lesson_id':self.id})
            tracks = self.env['student.lesson.track'].search([('student_id','=',line.id),('lesson_id','=',self.id)])
            tracks.write({'attendance':'present'})
        self.write({'state':'started'})
        self.track_ids.write({'state':'started'})
        self.attendance_ids.write({'state':'started'})

    def lesson_complete(self):
        self.write({'state':'completed'})
        self.track_ids.write({'state':'completed'})
        self.attendance_ids.write({'state':'completed'})

    def lesson_cancel(self):
        self.write({'state':'cancelled'})
        self.track_ids.write({'state':'cancelled'})
        self.attendance_ids.write({'state':'cancelled'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("you can delete a lesson only in draft state")
            else:
                record.track_ids.unlink()
        res = super(StudentLesson, self).unlink()
        return res

class LessonAttendance(models.Model):
    _name = 'lesson.attendance'
    _description = 'Lesson Attendance'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    lesson_id = fields.Many2one('student.lesson', string="Lesson")
    student_id = fields.Many2one('music.student', string="Student")
    attendance = fields.Selection([
        ('present','Present'),
        ('absent', 'Absent')], 'Attendance', default='present', required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('started', 'Started'), ('completed', 'Completed'),('cancelled', 'Cancelled')], 'State')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)
    to_credit = fields.Boolean(string ="To Credit" , default=False)



    @api.onchange("to_credit")
    def create_lesson_credit(self):
        check_credit = self.env['lesson.credit'].search([('lesson_id','=',self.lesson_id._origin.id),('student_id','=',self.student_id.id)])
        if self.lesson_id._origin.state in ['confirmed','completed','canceled'] and self.to_credit :
            credit_obj = self.env['lesson.credit'].create({
                'name': self.student_id.name,
                'lesson_id':self.lesson_id._origin.id,
                'class_id':self.lesson_id.class_id.id,
                'student_id': self.lesson_id.id,
                'student_id':self.student_id.id,
                'start_date':self.lesson_id._origin.start_date,
                'end_date':self.lesson_id._origin.end_date,
                'state':'draft',
            })



    def confirm_student(self):
        self.write({'attendance':'present'})
        tracks = self.env['student.lesson.track'].search([('student_id', '=', self.student_id.id), ('lesson_id', '=', self.lesson_id.id)])
        tracks.write({'attendance': 'present'})

    def cancel_student(self):
        self.write({'attendance':'absent'})
        tracks = self.env['student.lesson.track'].search([('student_id', '=', self.student_id.id), ('lesson_id', '=', self.lesson_id.id)])
        tracks.write({'attendance': 'absent'})

class StudentLessonTrack(models.Model):
    _name = 'student.lesson.track'
    _description = 'Student Lesson Track'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    lesson_id = fields.Many2one('student.lesson', string="Lesson",ondelete='cascade')
    student_id = fields.Many2one('music.student','Students')
    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    start_date = fields.Datetime(string="Start Time", required=True, readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Datetime(string="End Time", required=True, readonly=True, states={'draft': [('readonly', False)]})
    # instructor = fields.Many2one('hr.employee', string='Teacher', readonly=True, required=True, states={'draft': [('readonly', False)]})
    partner_instructor = fields.Many2one('res.partner', string='Teacher Partner', readonly=True, required=True, states={'draft': [('readonly', False)]},track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('started', 'Started'),('completed', 'Completed'),('cancelled', 'Cancelled')], 'State', realted='lesson_id.state', required=True)
    service_id = fields.Many2one('product.product', string="Service", readonly=True, required=True, domain="[('type','=','service')]", states={'draft': [('readonly', False)]})
    color = fields.Integer(string='Color Index', help='This color will be used in the kanban view.')
    class_id = fields.Many2one('student.class', string="Class ID")
    attendance = fields.Selection([
        ('present','Present'),
        ('absent', 'Absent')], 'Attendance', readonly=True)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)

    def check_delete_track(self):
        if not self.lesson_id:
            self.sudo().unlink()

class MonthDays(models.Model):
    _name = 'month.days'
    _description = 'Generate lessons for all selected students'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    date = fields.Date('Date')
    class_id = fields.Many2one('student.class', 'Month Days')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)

class musicLocation(models.Model):
    _name = 'music.location'
    _description = 'music Location'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    name = fields.Char('Name')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)

class AddLessons(models.TransientModel):
    _name = 'add.lessons'
    _description = 'Generate lessons for all selected students'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    def _get_default_students(self):
        active_id = self.env.context.get('active_id')
        class_info = self.env['student.class'].browse(active_id)
        return class_info.student_ids.ids

    lesson_name = fields.Char('lesson name' ,required=True,)
    student_ids = fields.Many2many('music.student', 'music_student_group_class_rel', 'class_id', 'student_id', 'Students' , default =_get_default_students)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)



    def test(self,nbr):
        sequence_names = []
        initial_number = self.lesson_name[-1]
        padding = len(initial_number)
        # We split the serial number to get the prefix and suffix.
        splitted = regex_split(initial_number, self.lesson_name)
        # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        text_name = ('%s%s %s') % ((
            prefix,
            str(nbr).zfill(padding),
            suffix
        ))

        return text_name



    def compute_sheet(self):
        lesson = self.env['student.lesson']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        class_info = self.env['student.class'].browse(active_id)
        if not data['student_ids']:
            raise UserError(_("You must select student(s) to generate lessons(s)."))
        name_of_lesson = self.lesson_name
        # Add 1 day.
        day=0
        class_info.with_context().write({'student_ids': [(6, 0, self.student_ids.ids)]})
        caught_initial_number = regex_findall("\d+", name_of_lesson)

        if not caught_initial_number:
            # raise UserError(_('The name of the lesson must contain at least one digit.'))
            name_of_lesson = name_of_lesson + '1'
        cpt_t = int(name_of_lesson[-1])

        if class_info.repeat == 'daily':
            while class_info.end_date >= class_info.start_date:
                result = class_info.start_date + timedelta(days=day)
                day+=1
                end_time = datetime.strptime(str(class_info.end_date), "%Y-%m-%d %H:%M:%S")
                day_end = datetime.strptime(str(result), "%Y-%m-%d %H:%M:%S")
                # convert into datetime fromat
                end_time_value = datetime.strftime(end_time, "%H:%M:%S")
                day_end_value = datetime.strftime(day_end, "%Y-%m-%d")
                final_time = datetime.strptime(day_end_value+' '+end_time_value, "%Y-%m-%d %H:%M:%S")
                name_lesson = self.test(cpt_t)

                lesson_id = lesson.create({
                    'name':name_lesson,
                    'start_date':result,
                    'end_date':final_time,
                    # 'instructor':class_info.instructor.id,
                    'partner_instructor':class_info.partner_instructor.id,
                    'service_id':class_info.service_id.id,
                    'state':class_info.state,
                    'student_ids':[(6, 0, self.student_ids.ids)],
                    'class_id':class_info.id,
                    'equipment_id':class_info.equipment_id.id
                })
                for student in self.env['music.student'].browse(data['student_ids']):
                # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                    self.env['student.lesson.track'].create({
                                    'name':name_lesson,
                                    'start_date':result,
                                    'end_date':final_time,
                                    # 'instructor':class_info.instructor.id,
                                    'partner_instructor':class_info.partner_instructor.id,
                                    'service_id':class_info.service_id.id,
                                    'state':class_info.state,
                                    'student_id':student.id,
                                    'class_id': class_info.id,
                                    'lesson_id': lesson_id.id,
                    })
                cpt_t+=1
                if final_time == class_info.end_date:
                    break
        elif class_info.repeat == 'weekly':
            while class_info.end_date >= class_info.start_date:
                result = class_info.start_date + timedelta(days=day)
                day+=1
                week_day = result.weekday()
                end_time = datetime.strptime(str(class_info.end_date), "%Y-%m-%d %H:%M:%S")
                day_end = datetime.strptime(str(result), "%Y-%m-%d %H:%M:%S")
                # convert into datetime fromat
                end_time_value = datetime.strftime(end_time, "%H:%M:%S")
                day_end_value = datetime.strftime(day_end, "%Y-%m-%d")
                final_time = datetime.strptime(day_end_value + ' ' + end_time_value, "%Y-%m-%d %H:%M:%S")
                name_lesson = self.test(cpt_t)
                if class_info.monday:
                    if week_day == 0:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                        # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({
                                            'name':name_lesson,
                                            'start_date':result,
                                            'end_date':final_time,
                                            # 'instructor':class_info.instructor.id,
                                            'partner_instructor':class_info.partner_instructor.id,
                                            'service_id':class_info.service_id.id,
                                            'state':class_info.state,
                                            'student_id':student.id,
                                            'class_id': class_info.id,
                                            'lesson_id': lesson_id.id,
                            })
                        cpt_t+=1
                if class_info.tuesday:
                    if week_day == 1:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                        # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({
                                            'name':name_lesson,
                                            'start_date':result,
                                            'end_date':final_time,
                                            # 'instructor':class_info.instructor.id,
                                            'partner_instructor':class_info.partner_instructor.id,
                                            'service_id':class_info.service_id.id,
                                            'state':class_info.state,
                                            'student_id':student.id,
                                            'class_id': class_info.id,
                                            'lesson_id': lesson_id.id,
                            })
                        cpt_t += 1
                if class_info.wednesday:
                    if week_day == 2:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({'name': name_lesson,'start_date': result,
                                'end_date': final_time,
                                # 'instructor': class_info.instructor.id,
                                'partner_instructor':class_info.partner_instructor.id,
                                'service_id': class_info.service_id.id,
                                'state': class_info.state,
                                'student_id': student.id,
                                'class_id': class_info.id,
                                'lesson_id': lesson_id.id,
                                })
                        cpt_t += 1

                if class_info.thursday:
                    if week_day == 3:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({
                                'name': name_lesson,
                                'start_date': result,
                                'end_date': final_time,
                                # 'instructor': class_info.instructor.id,
                                'partner_instructor':class_info.partner_instructor.id,
                                'service_id': class_info.service_id.id,
                                'state': class_info.state,
                                'student_id': student.id,
                                'class_id': class_info.id,
                                'lesson_id': lesson_id.id,
                            })
                        cpt_t += 1
                if class_info.friday:
                    if week_day == 4:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({
                                'name': name_lesson,
                                'start_date': result,
                                'end_date': final_time,
                                # 'instructor': class_info.instructor.id,
                                'partner_instructor':class_info.partner_instructor.id,
                                'service_id': class_info.service_id.id,
                                'state': class_info.state,
                                'student_id': student.id,
                                'class_id': class_info.id,
                                'lesson_id': lesson_id.id,
                            })
                        cpt_t += 1
                if class_info.saturday:
                    if week_day == 5:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            # end_value = datetime.combine(datetime.datetime(day_end_value), datetime.time(end_time_value))
                            self.env['student.lesson.track'].create({
                                'name': name_lesson,
                                'start_date': result,
                                'end_date': final_time,
                                # 'instructor': class_info.instructor.id,
                                'partner_instructor':class_info.partner_instructor.id,
                                'service_id': class_info.service_id.id,
                                'state': class_info.state,
                                'student_id': student.id,
                                'class_id': class_info.id,
                                'lesson_id': lesson_id.id,
                            })
                        cpt_t += 1
                if class_info.sunday:
                    if week_day == 6:
                        lesson_id = lesson.create({
                            'name': name_lesson,
                            'start_date': result,
                            'end_date': final_time,
                            # 'instructor': class_info.instructor.id,
                            'partner_instructor':class_info.partner_instructor.id,
                            'service_id': class_info.service_id.id,
                            'state': class_info.state,
                            'student_ids': [(6, 0, self.student_ids.ids)],
                            'class_id': class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            self.env['student.lesson.track'].create({
                                'name': name_lesson,
                                'start_date': result,
                                'end_date': final_time,
                                # 'instructor': class_info.instructor.id,
                                'partner_instructor': class_info.partner_instructor.id,
                                'service_id': class_info.service_id.id,
                                'state': class_info.state,
                                'student_id': student.id,
                                'class_id': class_info.id,
                                'lesson_id': lesson_id.id,
                            })
                        cpt_t += 1

                if final_time == class_info.end_date:
                    break
            # raise UserError('fdfdf')
        elif class_info.repeat == 'monthly':
            while class_info.end_date >= class_info.start_date:
                result = class_info.start_date + timedelta(days=day)
                day+=1
                end_time = datetime.strptime(str(class_info.end_date), "%Y-%m-%d %H:%M:%S")
                day_end = datetime.strptime(str(result), "%Y-%m-%d %H:%M:%S")
                # convert into datetime fromat
                end_time_value = datetime.strftime(end_time, "%H:%M:%S")
                day_end_value = datetime.strftime(day_end, "%Y-%m-%d")
                final_time = datetime.strptime(day_end_value+' '+end_time_value, "%Y-%m-%d %H:%M:%S")
                name_lesson = self.test(cpt_t)
                for line in class_info.monthly_dates:
                    day_value = datetime.strptime(str(line.date), "%Y-%m-%d")
                    repeat_date = str(line.date)
                    repeat_date_value = repeat_date[8:10]
                    day_end_value_repaet = day_end_value[8:10]
                    _logger.info(repeat_date_value)
                    _logger.info(day_end_value_repaet)
                    if repeat_date_value == day_end_value_repaet:
                        lesson_id = lesson.create({
                            'name':name_lesson,
                            'start_date':result,
                            'end_date':final_time,
                            # 'instructor':class_info.instructor.id,
                            'partner_instructor': class_info.partner_instructor.id,
                            'service_id':class_info.service_id.id,
                            'state':class_info.state,
                            'student_ids':[(6, 0, self.student_ids.ids)],
                            'class_id':class_info.id,
                            'equipment_id': class_info.equipment_id.id
                        })
                        for student in self.env['music.student'].browse(data['student_ids']):
                            self.env['student.lesson.track'].create({
                                            'name':name_lesson,
                                            'start_date':result,
                                            'end_date':final_time,
                                            # 'instructor':class_info.instructor.id,
                                            'partner_instructor': class_info.partner_instructor.id,
                                            'service_id':class_info.service_id.id,
                                            'state':class_info.state,
                                            'student_id':student.id,
                                            'class_id': class_info.id,
                                            'lesson_id': lesson_id.id,
                            })
                cpt_t += 1
                if final_time == class_info.end_date:
                    break