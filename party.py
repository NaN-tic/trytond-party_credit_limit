# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from sql import Literal
from sql.aggregate import Sum
from sql.conditionals import Coalesce, Case

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Party']


class Party:
    __name__ = 'party.party'
    __metaclass__ = PoolMeta

    unpayed_amount = fields.Function(fields.Numeric('Unpayed amount'),
        'get_accounting_amount')
    pending_amount = fields.Function(fields.Numeric('Pending amount'),
        'get_accounting_amount')
    draft_invoices_amount = fields.Function(fields.Numeric(
            'Draft invoices amount'),
        'get_draft_invoices_amount')
    uninvoiced_amount = fields.Function(fields.Numeric('Uninvoiced amount'),
        'get_uninvoiced_amount')
    amount_to_limit = fields.Function(fields.Numeric('Amount to limit'),
        'get_amounts')
    limit_percent = fields.Function(fields.Numeric('% Limit'),
        'get_amounts')

    @classmethod
    def get_accounting_amount(cls, parties, names):
        res = {}
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        Account = pool.get('account.account')
        Date = pool.get('ir.date')
        User = pool.get('res.user')

        for name in names:
            if name not in ('unpayed_amount', 'pending_amount'):
                raise Exception('Bad argument')
            res[name] = dict((p.id, Decimal('0.0')) for p in parties)

        line = MoveLine.__table__()
        account = Account.__table__()
        today = Date.today()
        transaction = Transaction()
        cursor = transaction.connection.cursor()
        line_query, _ = MoveLine.query_get(line)

        user_id = transaction.user
        if user_id == 0 and 'user' in Transaction().context:
            user_id = transaction.context['user']
        user = User(user_id)
        if not user.company:
            return res
        company_id = user.company.id

        amount = Coalesce(line.debit, 0) - Coalesce(line.credit, 0)
        cursor.execute(*line.join(account,
                condition=account.id == line.account
            ).select(line.party,
                Sum(Case((line.maturity_date < today, amount),
                        else_=Literal(0))).as_('unpayed_amount'),
                Sum(Case((line.maturity_date == None or
                            line.maturity_date >= today, amount),
                        else_=Literal(0))).as_('pending_amount'),
            where=account.active
            & (account.kind == 'receivable')
            & (line.reconciliation == None)
            & (account.company == company_id)
            & line_query,
            group_by=(line.party)))
        for party_id, unpayed, pending in cursor.fetchall():
            for name, value in (('unpayed_amount', unpayed),
                    ('pending_amount', pending)):
                if name not in names:
                    continue
                # SQLite uses float for SUM
                if not isinstance(value, Decimal):
                    value = Decimal(str(value))
                res[name][party_id] = value
        return res

    @classmethod
    def get_draft_invoices_amount(cls, parties, name):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        res = {}.fromkeys([p.id for p in parties], Decimal('0.0'))
        without_sales = Transaction().context.get('without_sales', False)
        domain = [
            ('type', '=', ('out')),
            ('party', 'in', [p.id for p in parties]),
            ('state', 'in', ['draft', 'validated']),
            ]
        for invoice in Invoice.search(domain):
            if without_sales and invoice.sales:
                continue
            res[invoice.party.id] += invoice.untaxed_amount
        return res

    @classmethod
    def get_uninvoiced_amount(cls, parties, name):
        pool = Pool()
        Sale = pool.get('sale.sale')
        Currency = pool.get('currency.currency')
        User = pool.get('res.user')

        amounts = {}.fromkeys([p.id for p in parties], Decimal('0.0'))
        sales = Sale.search([
                ('party', 'in', [p.id for p in parties]),
                ('state', '=', 'processing'),
                ])

        user = User(Transaction().user)
        if not user.company:
            return amounts
        currency = user.company.currency
        for sale in sales:
            amount = 0
            for line in sale.lines:
                amount += Currency.compute(sale.currency, line.amount,
                    currency, round=False)
                for invoice_line in line.invoice_lines:
                    invoice = invoice_line.invoice
                    if invoice:
                        amount -= Currency.compute(invoice.currency,
                            invoice_line.amount, currency)
            amounts[sale.party.id] += amount
        return amounts

    @classmethod
    def get_amounts(cls, parties, names):
        res = {}
        for name in names:
            if name not in ('amount_to_limit', 'limit_percent'):
                raise Exception('Bad argument')
            res[name] = {}.fromkeys([p.id for p in parties],
                Decimal('100.0') if name == 'limit_percent'
                else Decimal('0.0'))
        for party in parties:
            if 'amount_to_limit' in names:
                limit_amount = party.credit_limit_amount or Decimal('0.0')
                res['amount_to_limit'][party.id] = (
                    limit_amount - party.credit_amount)
            if party.credit_limit_amount and 'limit_percent' in names:
                res['limit_percent'][party.id] = (Decimal('100.0') *
                    party.credit_amount / party.credit_limit_amount)

        for key in res.keys():
            if key not in names:
                del res[key]
        return res

    @classmethod
    def get_credit_amount(cls, parties, name):
        amounts = super(Party, cls).get_credit_amount(parties, name)
        with Transaction().set_context(without_sales=True):
            uninvoiced = cls.get_draft_invoices_amount(parties, name)
            for party, value in uninvoiced.iteritems():
                amounts[party] += value
        return amounts

    @classmethod
    def _credit_limit_to_lock(cls):
        models = super(Party, cls)._credit_limit_to_lock()
        return models + ['account.invoice', 'sale.sale']
