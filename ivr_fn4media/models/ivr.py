# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
from datetime import datetime
import logging
import random
import threading

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

IVR_BUSINESS_MODELS = [
    'crm.lead',
    'event.registration',
    'hr.applicant',
    'res.partner',
    'event.track',
    'sale.order',
    'ivr.list',
]

class IvrTag(models.Model):
    """Model of categories of mass mailing, i.e. marketing, newsletter, ... """
    _name = 'ivr.tag'
    _description = 'IVR Tag'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IvrCall(models.Model):
    """Model of a contact list. """
    _name = 'ivr.call'
    _order = 'create_date'
    _description = 'Call Log'

    create_date = fields.Datetime(string='Date')
    caller = fields.Char(string='Caller')
    click_to_call = fields.Char(string='Click To Call')
    sr_number = fields.Char(string='Sr Number')
    action = fields.Char(string='Action')
    call_status = fields.Char(string='Call Status')
    duration = fields.Char(string='Duration')
    recordings = fields.Char(string='Recordings')
    downlod	= fields.Char(string='Downlod')
	
class IvrList(models.Model):
    """Model of a contact list. """
    _name = 'ivr.list'
    _order = 'name'
    _description = 'Ivr List'

    name = fields.Char(string='IVR Number List', required=True)
    active = fields.Boolean(default=True)
    create_date = fields.Datetime(string='Creation Date')
    contact_nbr = fields.Integer(compute="_compute_contact_nbr", string='Agents of Contacts')

    # Compute number of contacts non opt-out for a mailing list
    def _compute_contact_nbr(self):
        self.env.cr.execute('''
            select
                list_id, count(*)
            from
                ivr_contact_list_rel r 
                left join ivr_contact c on (r.contact_id=c.id)
            where
                c.opt_out <> true
            group by
                list_id
        ''')
        data = dict(self.env.cr.fetchall())
        for ivr_list in self:
            ivr_list.contact_nbr = data.get(ivr_list.id, 0)

class IvrContact(models.Model):
    """Model of a contact. This model is different from the partner model
    because it holds only some basic information: name, email. The purpose is to
    be able to deal with large contact list to email without bloating the partner
    base."""
    _name = 'ivr.contact'
    _description = 'IVR Agents Contact'
    _order = 'email'
    _rec_name = 'email'

    name = fields.Char()
    company_name = fields.Char(string='Company Name')
    title_id = fields.Many2one('res.partner.title', string='Title')
    email = fields.Char(required=True)
    create_date = fields.Datetime(string='Creation Date')
    list_ids = fields.Many2many(
        'ivr.list', 'ivr_contact_list_rel',
        'contact_id', 'list_id', string='Agents Lists')
    opt_out = fields.Boolean(string='Opt Out', help='The contact has chosen not to receive mails anymore from this list')
    unsubscription_date = fields.Datetime(string='Unsubscription Date')
    message_bounce = fields.Integer(string='Bounced', help='Counter of the number of bounced emails for this contact.', default=0)
    country_id = fields.Many2one('res.country', string='Country')
    tag_ids = fields.Many2many('res.partner.category', string='Tags')

    @api.model
    def create(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(IvrContact, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'opt_out' in vals:
            vals['unsubscription_date'] = vals['opt_out'] and fields.Datetime.now()
        return super(IvrContact, self).write(vals)

    def get_name_email(self, name):
        name, email = self.env['res.partner']._parse_partner_name(name)
        if name and not email:
            email = name
        if email and not name:
            name = email
        return name, email

    @api.model
    def name_create(self, name):
        name, email = self.get_name_email(name)
        contact = self.create({'name': name, 'email': email})
        return contact.name_get()[0]

    @api.model
    def add_to_list(self, name, list_id):
        name, email = self.get_name_email(name)
        contact = self.create({'name': name, 'email': email, 'list_ids': [(4, list_id)]})
        return contact.name_get()[0]

    @api.multi
    def message_get_default_recipients(self):
        return dict((record.id, {'partner_ids': [], 'email_to': record.email, 'email_cc': False}) for record in self)
		
class IvrSettings(models.Model):
    """Model of a contact list. """
    _name = 'ivr.settings'
    _order = 'app_description'
    _description = 'Settings'

    create_date = fields.Datetime(string='Creation Date')
    app_description = fields.Char(string='App Description', required=True)
    organisation_name = fields.Char(string='Organisation name', required=True)
    category = fields.Char(string='Category', required=True)
    Channel = fields.Char(string='Channel', required=True)
    access_key = fields.Char(string='Access Key', required=True)
    authorization_key = fields.Char(string='Authorization Key', required=True)
    website = fields.Char(string='website', required=True)
    client_key = fields.Char(string='Client Key', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)

class MissedcallApis(models.Model):
    """Model of a contact list. """
    _name = 'missedcall.apis'
    _order = 'create_date'
    _description = 'Missed Call API'

    create_date = fields.Datetime(string='Date')
    name = fields.Char(string='Name', required=True)
    api = fields.Char(string='API', required=True)
    model = fields.Char(string='Model', required=True)
 
	
class MissedcallCall(models.Model):
    """Model of a contact list. """
    _name = 'missedcall.call'
    _order = 'create_date'
    _description = 'Missed Call Log'

    create_date = fields.Datetime(string='Date')
    caller = fields.Char(string='Caller')
    sr_number = fields.Char(string='Missed Number')

class MissedcallSettings(models.Model):
    """Model of a contact list. """
    _name = 'missedcall.settings'
    _order = 'user_name'
    _description = 'Settings'

    create_date = fields.Datetime(string='Creation Date')
    ex_date = fields.Datetime(string='Expiry Date')
    user_name = fields.Char(string='User Name', required=True)
    password = fields.Char(string='Password', required=True)
    number_id = fields.Char(string='Number Id', required=True)
    website = fields.Char(string='website', required=True)
	
class ShortApis(models.Model):
    """Model of a contact list. """
    _name = 'short.apis'
    _order = 'create_date'
    _description = 'Short Code API'

    create_date = fields.Datetime(string='Date')
    name = fields.Char(string='Name', required=True)
    api = fields.Char(string='API', required=True)
    model = fields.Char(string='Model', required=True)
	
class ShortCall(models.Model):
    """Model of a contact list. """
    _name = 'short.call'
    _order = 'create_date'
    _description = 'Short Code Log'

    create_date = fields.Datetime(string='Date')
    caller = fields.Char(string='Caller')
    sr_number = fields.Char(string='Short Code')
    keyword = fields.Char(string='KeyWord')
	
class ShortSettings(models.Model):
    """Model of a contact list. """
    _name = 'short.settings'
    _order = 'user_name'
    _description = 'Settings'

    create_date = fields.Datetime(string='Creation Date')
    ex_date = fields.Datetime(string='Expiry Date')
    user_name = fields.Char(string='User Name', required=True)
    password = fields.Char(string='Password', required=True)
    number_id = fields.Char(string='Number Id', required=True)
    website = fields.Char(string='website', required=True)

class LongCall(models.Model):
    """Model of a contact list. """
    _name = 'long.call'
    _order = 'create_date'
    _description = 'Long Code Log'

    create_date = fields.Datetime(string='Date')
    caller = fields.Char(string='Caller')
    sr_number = fields.Char(string='Long Code')
    keyword = fields.Char(string='KeyWord')
	
class LongApis(models.Model):
    """Model of a contact list. """
    _name = 'long.apis'
    _order = 'create_date'
    _description = 'Long Code API'

    create_date = fields.Datetime(string='Date')
    name = fields.Char(string='Name', required=True)
    api = fields.Char(string='API', required=True)
    model = fields.Char(string='Model', required=True)
    

class LongSettings(models.Model):
    """Model of a contact list. """
    _name = 'long.settings'
    _order = 'user_name'
    _description = 'Settings'

    create_date = fields.Datetime(string='Creation Date')
    ex_date = fields.Datetime(string='Expiry Date')
    user_name = fields.Char(string='User Name', required=True)
    password = fields.Char(string='Password', required=True)
    number_id = fields.Char(string='Number Id', required=True)
    website = fields.Char(string='website', required=True)