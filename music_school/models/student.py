# -*- coding: utf-8 -*-
###############################################################################
#
#    inteslar
#    Copyright (C) 2009-TODAY inteslar software trading llc(<http://www.inteslar.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DriveStudent(models.Model):
    _name = "music.student"
    _description = "Student"
    _inherits = {"res.partner": "partner_id"}

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    middle_name = fields.Char('Middle Name', size=128)
    last_name = fields.Char('Last Name', size=128)
    birth_date = fields.Date('Birth Date')
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')],
        'Blood Group')
    gender = fields.Selection(
        [('m', 'Male'), ('f', 'Female'),
         ('o', 'Other')], 'Gender')
    nationality = fields.Many2one('res.country', 'Nationality')
    emergency_contact = fields.Many2one(
        'res.partner', 'Emergency Contact')
    visa_info = fields.Char('Visa Info', size=64)
    id_number = fields.Char('ID Card Number', size=64)
    partner_id = fields.Many2one('res.partner', 'Partner', ondelete="cascade")
    lesson_ids = fields.One2many('student.lesson.track', 'student_id')
    lesson_count = fields.Float('Lesson count', compute='compute_lesson_count')
    company_id = fields.Many2one(string="Company", comodel_name='res.company', default=_get_current_company)
    # emergency_contact_phone = fields.Char('Emergency contact phone' )
    emergency_contact_phone = fields.Many2one('res.partner',string='Emergency contact phone')
    student_identifiant =  fields.Char('Student ID' )
    credit_count = fields.Float('Credit count', compute='compute_lesson_count')
    credit_ids = fields.One2many('lesson.credit', 'student_id')
    # course_detail_ids = fields.One2many('op.student.course', 'student_id',
    #                                     'Course Details')

    @api.onchange('partner_id')
    def onchange_partner_id_ref(self):
        if self.partner_id:
            # self.emergency_contact_phone = self.partner_id.phone
            self.student_identifiant = self.partner_id.ref

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date > fields.Date.today():
                raise ValidationError(_(
                    "Birth Date can't be greater than current date!"))

    def compute_lesson_count(self):
        for line in self:
            line.lesson_count = len(line.lesson_ids)
            line.credit_count = len(line.credit_ids)

    def action_view_credit(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "lesson.credit",
            "domain": [('id', 'in', self.credit_ids.ids)],
            "name": "Credits",
            'view_mode': 'tree,form',
        }
        return result
