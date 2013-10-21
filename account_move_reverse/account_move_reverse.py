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

from osv import orm, osv, fields
from tools.translate import _

class AccountMove(orm.Model):

    _inherit = 'account.move'

    _columns = {
                'move_reverse_id':fields.many2one('account.move','Move Reverse'),
                }

    def copy(self, cr, uid, id, default={}, context=None):
        default.update({
            'move_reverse_id':False,
        })
        return super(AccountMove, self).copy(cr, uid, id, default, context)

    def button_cancel(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if not move.journal_id.update_posted:
                raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of this journal !\nYou should set the journal to allow cancelling entries if you want to do that.'))

            if move.move_reverse_id:
                if not move.journal_id.update_reversed:
                    raise osv.except_osv(_('Error !'), _('You can not modify a posted entry of this journal !\nYou should set the journal to allow cancelling reversed entries if you want to do that.'))
                
                move_reverse = self.browse(cr, uid, move.move_reverse_id.id, context=context)
                for line_reverse in move_reverse.line_id:
                    if line_reverse.reconcile_id:
                        self.pool.get('account.move.reconcile').unlink(cr,uid,[line_reverse.reconcile_id.id],context=context)
                cr.execute('UPDATE account_move '\
                           'SET state=%s '\
                           'WHERE id IN %s', ('draft', tuple([move_reverse.id]),))
                self.unlink(cr,uid,[move_reverse.id],context=context)

        result = super(AccountMove, self).button_cancel(cr, uid, ids, context=context)
        return True

    def reverse(self, cr, uid, ids, context=None):

        for move_original_id in ids:
            move_original = self.pool.get('account.move').browse(cr, 1, move_original_id, context=context)
            
            if move_original.move_reverse_id:
                continue

            move = {
                    'name':'Reverse: ' + move_original.name,
                    'ref':move_original.ref,
                    'journal_id':move_original.journal_id.id,
                    'period_id':move_original.period_id.id,
                    'to_check':False,
                    'partner_id':move_original.partner_id.id,
                    'date':move_original.date,
                    'narration':move_original.narration,
                    'company_id':move_original.company_id.id,
                    }
            move_id = self.pool.get('account.move').create(cr, uid, move)
                    
            self.pool.get('account.move').write(cr, uid, [move_original.id], {'move_reverse_id' : move_id})

            move_reconcile_obj = self.pool.get('account.move.reconcile')

            lines = move_original.line_id
            for line in lines:
                move_line = {
                             'name':line.name,
                             'debit':line.credit,
                             'credit':line.debit,
                             'account_id':line.account_id.id,
                             'move_id': move_id,
                             'amount_currency':line.amount_currency * -1,
                             'period_id':line.period_id.id,
                             'journal_id':line.journal_id.id,
                             'partner_id':line.partner_id.id,
                             'currency_id':line.currency_id.id,
                             'date_maturity':line.date_maturity,
                             'date':line.date,
                             'date_created':line.date_created,
                             'state':'valid',
                             'company_id':line.company_id.id,
                             }

                line_created_id = self.pool.get('account.move.line').create(cr, uid, move_line)

                if line.reconcile_id:
                    reconcile = line.reconcile_id
                    if len(reconcile.line_id) > 2:
                        reconcile_line_ids = []
                        for line_id in reconcile.line_id:
                            reconcile_line_ids.append(line_id.id)
                        self.pool.get('account.move.line').write(cr,uid,reconcile_line_ids,{'reconcile_id': False, 'reconcile_partial_id':reconcile.id})
                        self.pool.get('account.move.line').write(cr,uid,line.id,{'reconcile_partial_id': False})
                    else:
                        move_reconcile_obj.unlink(cr,uid,[reconcile.id],context=context)

                elif line.reconcile_partial_id:
                    reconcile = line.reconcile_partial_id
                    if len(reconcile.line_partial_ids) > 2:
                        self.pool.get('account.move.line').write(cr,uid,line.id,{'reconcile_partial_id': False })
                    else:
                        move_reconcile_obj.unlink(cr,uid,[reconcile.id],context=context)

                if line.account_id.reconcile:
                    reconcile_id = self.pool.get('account.move.reconcile').create(cr, uid, {'type': 'Account Reverse'})
                    cr.execute('UPDATE account_move_line '\
                               'SET reconcile_id=%s '\
                               'WHERE id IN %s', (reconcile_id, tuple([line.id]),))
                    #self.pool.get('account.move.line').write(cr,uid,[line.id],{'reconcile_id': reconcile_id})
                    self.pool.get('account.move.line').write(cr,uid,[line_created_id],{'reconcile_id': reconcile_id})

            #Posted move reverse
            self.pool.get('account.move').post(cr, 1, [move_id, move_original.id], context={})
        return True

class AccountJournal(orm.Model):
    _inherit = 'account.journal'
    
    _columns = {
        'update_reversed' : fields.boolean('Allow Cancelling Reversed Entries', help="Check this box if you want to allow the cancellation of the reversed entries related to this journal or of the invoice related to this journal"),
        }
