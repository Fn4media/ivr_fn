# -*- coding: utf-8 -*-
{
    'name': 'FN4MEDIA IVR',
    'version': '1.0',
    'category': 'Tools',
	'support': "support@fn4media.in",
    'summary': 'Make calls with other users inside your system',
	'license':'LGPL-3',
    'description': """
Send sms 
=======================
    """,
    'author': 'Fn4media Technologies Pvt Ltd',
    'website': 'http://www.fn4media.in/apps',
    'data': [
        'views/ivr.xml',
    ],
	'demo': [],
    'depends': ['web','crm','bus'],
    'qweb': ['static/src/xml/*.xml'],
    'images':[
        'static/description/1.jpg',
        'static/description/2.jpg',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
