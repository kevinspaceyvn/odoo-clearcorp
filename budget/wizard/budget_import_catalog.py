# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Addons modules by CLEARCORP S.A.
#    Copyright (C) 2009-TODAY CLEARCORP S.A. (<http://clearcorp.co.cr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import errno
from osv import osv, fields
from tools.translate import _
import base64
import logging


class budget_import_catalog(osv.osv_memory):
    _name = 'budget.import.catalog'
    
    _columns = {
        'catalog_file':fields.binary('File', filters = '*.csv')
    }
    
    def get_parent_code(self,cr,uid, code):
        dot_right = code.rfind('.')
        if dot_right == -1:
            return code
        else:
            return code[0:dot_right]
        
    def get_short_code(self,cr,uid, code):
        dot_right = code.rfind('.')
        last_ind = len(code)
        if dot_right == -1:
            return code
        else:
            return code[dot_right+1:last_ind]
        
    def search_account_id(self,cr,uid,code, dict_list):
        ##params
        #code, string of the account
        #dict_list, list of dictionaries with keys id and code for each account
        ##returns id of the account or -1 if fails
        for account in dict_list:
            if account['code'] == code:
                return account['id']
        return -1
    
    def import_catalog(self, cr, uid, ids,  context=None):
        try:
            if context is None:
                context = {}
            logger = logging.getLogger('budget.import.catalog')
            account_obj= self.pool.get('budget.account')
            account_list = [ ]#list of dictionaries
            data = self.browse(cr, uid, ids, context=context)[0]
            file_str = base64.decodestring(data.catalog_file)
            line_list = file_str.split('\n')
            for line in line_list:
                account = { }
                params_list = line.split(';')
                if len(params_list) == 3:
                    logger.info("account code: %s" % params_list )
                    short_code = self.get_short_code(cr, uid, params_list[0]) 
                    parent_code = self.get_parent_code(cr, uid, params_list[0])
                    parent_id = self.search_account_id(cr, uid, parent_code, account_list)
                    if parent_id != -1:
                        account['parent_id'] = parent_id
                    else:
                        account['parent_id'] = False
                    account['code'] = short_code
                    account['name'] = params_list[1]
                    account['account_type'] = params_list[2]
                    
                    account_id = account_obj.create(cr,uid,account)
                    account['code'] = params_list[0]
                    account['id'] = account_id
                    #appending at the begining of the list to improve search timing
                    account_list.insert(0, account)
        except TypeError, err:
             raise osv.except_osv(_('Error!'), _('Please specify a .csv file'))
        except IOError, err:
            if err.errno == errno.ENAMETOOLONG:
                raise osv.except_osv(_('Error!'), _('The file name is too long'))
            else:
                raise
            
            
            
        
    