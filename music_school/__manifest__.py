# -*- coding: utf-8 -*-
##########################################################################################
#
#    inteslar software trading llc.
#    Copyright (C) 2018-TODAY inteslar software trading llc (<https://www.inteslar.com>).
#
##########################################################################################
{
    'name': "Music School / Institute",
    'version': '1.0',
    'category': 'industries',
    'price': 699.00,
    'currency': 'EUR',
    'maintainer': 'inteslar',
    'website': "https://www.inteslar.com",
    'license': 'OPL-1',
    'author': 'inteslar',
    'summary': 'Music School / Institute Management By Inteslar',
    'live_test_url':'https://youtu.be/bqsqEzRnpJE',
    'images': ['static/images/main_screenshot.png'],
    'depends': ['resource', 'hr','calendar','product','account','base','base_setup','maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'security/music_school_security.xml',
        'report/music_class_report_summary.xml',
        'views/student_view.xml',
        'views/lesson_view.xml',
        'views/lesson_credit_view.xml',
        'wizard/postponed_wizard_view.xml',
        'wizard/music_school_summary_report_views.xml',
        'wizard/music_school_detail_report_view.xml'
    ],
    'installable': True,
    'application': True,
}