#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import datetime
from dateutil.relativedelta import relativedelta
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    'Test module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('party_credit_limit')
        self.account = POOL.get('account.account')
        self.invoice = POOL.get('account.invoice')
        self.journal = POOL.get('account.journal')
        self.field = POOL.get('ir.model.field')
        self.move = POOL.get('account.move')
        self.party = POOL.get('party.party')
        self.payment_term = POOL.get('account.invoice.payment_term')
        self.period = POOL.get('account.period')
        self.property = POOL.get('ir.property')
        self.product = POOL.get('product.product')
        self.sale = POOL.get('sale.sale')
        self.tax = POOL.get('account.tax')
        self.tax_code = POOL.get('account.tax.code')
        self.template = POOL.get('product.template')
        self.uom = POOL.get('product.uom')

    def test0005views(self):
        'Test views'
        test_view('party_credit_limit')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0010check_credit_limit(self):
        'Test check_credit_limit'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            account_tax, = self.account.search([
                    ('kind', '=', 'other'),
                    ('name', '=', 'Main Tax'),
                    ])
            journal, = self.journal.search([], limit=1)
            period, = self.period.search([], limit=1)
            party, = self.party.create([{
                        'name': 'Party',
                        'addresses': [('create', [{}])],
                        'account_receivable': receivable.id,
                        }])

            self.assertEqual(party.credit_amount, Decimal('0.0'))
            self.assertEqual(party.unpayed_amount, Decimal('0.0'))
            self.assertEqual(party.pending_amount, Decimal('0.0'))
            self.assertEqual(party.draft_invoices_amount, Decimal('0.0'))
            self.assertEqual(party.uninvoiced_amount, Decimal('0.0'))
            self.assertEqual(party.limit_percent, Decimal('100.0'))
            self.assertEqual(party.amount_to_limit, Decimal('0.0'))

            party.credit_limit_amount = Decimal('1000.0')
            party.save()

            self.assertEqual(party.credit_amount, Decimal('0.0'))
            self.assertEqual(party.unpayed_amount, Decimal('0.0'))
            self.assertEqual(party.pending_amount, Decimal('0.0'))
            self.assertEqual(party.draft_invoices_amount, Decimal('0.0'))
            self.assertEqual(party.uninvoiced_amount, Decimal('0.0'))
            self.assertEqual(party.limit_percent, Decimal('0.0'))
            self.assertEqual(party.amount_to_limit, Decimal('1000.0'))

            party = self.party(party.id)

            term, = self.payment_term.create([{
                        'name': 'Payment term',
                        'lines': [
                            ('create', [{
                                        'sequence': 0,
                                        'type': 'remainder',
                                        'days': 0,
                                        'months': 0,
                                        'weeks': 0,
                                        }])]
                        }])

            tx = self.tax_code.create([{
                            'name': 'invoice base',
                            },
                        {
                            'name': 'invoice tax',
                            },
                        {
                            'name': 'credit note base',
                            },
                        {
                            'name': 'credit note tax',
                        }])
            invoice_base, invoice_tax, credit_note_base, credit_note_tax = tx
            tax, = self.tax.create([{
                        'name': 'Tax 1',
                        'description': 'Tax 1',
                        'type': 'percentage',
                        'rate': Decimal('.10'),
                        'invoice_account': account_tax.id,
                        'credit_note_account': account_tax.id,
                        'invoice_base_code': invoice_base.id,
                        'invoice_tax_code': invoice_tax.id,
                        'credit_note_base_code': credit_note_base.id,
                        'credit_note_tax_code': credit_note_tax.id,
                        }])
            field, = self.field.search([
                    ('name', '=', 'account_revenue'),
                    ('model.model', '=', 'product.template'),
                    ])

            self.property.create([{
                        'value': 'account.account,%d' % revenue.id,
                        'field': field.id,
                        'res': None,
                        }])
            today = datetime.date.today()
            yesterday = today - relativedelta(days=1)
            self.move.create([{
                        'journal': journal.id,
                        'period': period.id,
                        'date': period.start_date,
                        'lines': [
                            ('create', [{
                                        'debit': Decimal(100),
                                        'account': receivable.id,
                                        'party': party.id,
                                        'maturity_date': yesterday,
                                        }, {
                                        'credit': Decimal(100),
                                        'account': revenue.id,
                                        }]),
                            ],
                        }, {
                        'journal': journal.id,
                        'period': period.id,
                        'date': period.start_date,
                        'lines': [
                            ('create', [{
                                        'debit': Decimal(200),
                                        'account': receivable.id,
                                        'party': party.id,
                                        }, {
                                        'credit': Decimal(200),
                                        'account': revenue.id,
                                        }]),
                            ],
                        }])

            kg, = self.uom.search([('name', '=', 'Kilogram')])
            template, = self.template.create([{
                        'name': 'Test credit limit',
                        'type': 'goods',
                        'list_price': Decimal(20),
                        'cost_price': Decimal(10),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        'salable': True,
                        'sale_uom': kg.id,
                        'delivery_time': 0,
                        }])
            product, = self.product.create([{
                        'template': template.id,
                        }])
            sales = self.sale.create([{
                        'party': party.id,
                        'shipment_address': party.addresses[0].id,
                        'invoice_address': party.addresses[0].id,
                        'invoice_method': 'shipment',
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'type': 'line',
                                        'sequence': 0,
                                        'product': product.id,
                                        'description': 'invoice_line',
                                        'unit': kg.id,
                                        'quantity': 1,
                                        'unit_price': Decimal('200.0'),
                                        'taxes': [
                                            ('add', [tax.id])],
                                        }])],
                        }, {
                        'party': party.id,
                        'shipment_address': party.addresses[0].id,
                        'invoice_address': party.addresses[0].id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'type': 'line',
                                        'sequence': 0,
                                        'description': 'invoice_line',
                                        'quantity': 1,
                                        'unit_price': Decimal('50.0'),
                                        'taxes': [
                                            ('add', [tax.id])],
                                        }])],
                        }])

            self.sale.quote(sales)
            self.sale.confirm(sales)
            self.sale.process(sales)

            party = self.party(party.id)

            self.assertEqual(party.unpayed_amount, Decimal('100.0'))
            self.assertEqual(party.pending_amount, Decimal('200.0'))
            self.assertEqual(party.draft_invoices_amount,
                Decimal('50.0'))
            self.assertEqual(party.uninvoiced_amount, Decimal('200.0'))
            self.assertEqual(party.credit_amount, Decimal('550.0'))
            self.assertEqual(party.amount_to_limit, Decimal('450.0'))
            self.assertEqual(party.limit_percent, Decimal('55.0'))
            party.credit_limit_amount = Decimal('0.0')
            party.save()

            party = self.party(party.id)
            self.assertEqual(party.limit_percent, Decimal('100.0'))
            self.assertEqual(party.amount_to_limit,
                party.credit_amount.copy_negate())

            party.credit_limit_amount = Decimal('500.0')
            party.save()

            party = self.party(party.id)
            self.assertEqual(party.limit_percent, Decimal('110.0'))
            self.assertEqual(party.amount_to_limit, Decimal('-50.0'))

            #Create an invoice and test it get's added to draft invoices amount
            #and in credit_amount but not in uninvoiced_amount
            invoice, = self.invoice.create([{
                        'number': '1',
                        'invoice_date': period.start_date,
                        'type': 'out_invoice',
                        'party': party.id,
                        'invoice_address': party.addresses[0].id,
                        'journal': journal.id,
                        'account': receivable.id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'out_invoice',
                                        'type': 'line',
                                        'sequence': 0,
                                        'description': 'invoice_line',
                                        'account': revenue.id,
                                        'quantity': 1,
                                        'unit_price': Decimal('50.0'),
                                        'taxes': [
                                            ('add', [tax.id])],
                                        }])],
                        }])

            party = self.party(party.id)
            self.assertEqual(party.unpayed_amount, Decimal('100.0'))
            self.assertEqual(party.pending_amount, Decimal('200.0'))
            self.assertEqual(party.draft_invoices_amount, Decimal('100.0'))
            self.assertEqual(party.uninvoiced_amount, Decimal('200.0'))
            self.assertEqual(party.credit_amount, Decimal('600.0'))


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        #Skip doctest
        class_name = test.__class__.__name__
        if test not in suite and class_name != 'DocFileCase':
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
