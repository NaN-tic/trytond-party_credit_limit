#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import datetime
from dateutil.relativedelta import relativedelta
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool
from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences


class TestCase(ModuleTestCase):
    'Test module'
    module = 'party_credit_limit'

    @with_transaction()
    def test0010check_credit_limit(self):
        'Test check_credit_limit'
        pool = Pool()
        Account = pool.get('account.account')
        Invoice = pool.get('account.invoice')
        Journal = pool.get('account.journal')
        Field = pool.get('ir.model.field')
        Move = pool.get('account.move')
        Party = pool.get('party.party')
        PaymentTerm = pool.get('account.invoice.payment_term')
        Property = pool.get('ir.property')
        Product = pool.get('product.product')
        Sale = pool.get('sale.sale')
        Tax = pool.get('account.tax')
        TaxCode = pool.get('account.tax.code')
        Template = pool.get('product.template')
        Uom = pool.get('product.uom')

        company = create_company()
        with set_company(company):
            create_chart(company)
            fiscalyear = set_invoice_sequences(get_fiscalyear(company))
            fiscalyear.save()
            fiscalyear.create_period([fiscalyear])
            period = fiscalyear.periods[0]

            receivable, = Account.search([
                    ('kind', '=', 'receivable'),
                    ])
            revenue, = Account.search([
                    ('kind', '=', 'revenue'),
                    ])
            account_tax, = Account.search([
                    ('kind', '=', 'other'),
                    ('name', '=', 'Main Tax'),
                    ])
            journal, = Journal.search([], limit=1)
            party, = Party.create([{
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

            party = Party(party.id)

            term, = PaymentTerm.create([{
                        'name': 'Payment term',
                        'lines': [
                            ('create', [{
                                        'type': 'remainder',
                                        }])]
                        }])

            tx = TaxCode.create([{
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
            tax, = Tax.create([{
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
            field, = Field.search([
                    ('name', '=', 'account_revenue'),
                    ('model.model', '=', 'product.template'),
                    ])

            Property.create([{
                        'value': 'account.account,%d' % revenue.id,
                        'field': field.id,
                        'res': None,
                        }])
            today = datetime.date.today()
            yesterday = today - relativedelta(days=1)
            Move.create([{
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

            kg, = Uom.search([('name', '=', 'Kilogram')])
            template, = Template.create([{
                        'name': 'Test credit limit',
                        'type': 'goods',
                        'list_price': Decimal(20),
                        'cost_price': Decimal(10),
                        'cost_price_method': 'fixed',
                        'default_uom': kg.id,
                        'salable': True,
                        'sale_uom': kg.id,
                        }])
            product, = Product.create([{
                        'template': template.id,
                        }])
            sales = Sale.create([{
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

            Sale.quote(sales)
            Sale.confirm(sales)
            Sale.process(sales)

            party = Party(party.id)

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

            party = Party(party.id)
            self.assertEqual(party.limit_percent, Decimal('100.0'))
            self.assertEqual(party.amount_to_limit,
                party.credit_amount.copy_negate())

            party.credit_limit_amount = Decimal('500.0')
            party.save()

            party = Party(party.id)
            self.assertEqual(party.limit_percent, Decimal('110.0'))
            self.assertEqual(party.amount_to_limit, Decimal('-50.0'))

            # Create an invoice and test it get's added to draft invoices
            # amount and in credit_amount but not in uninvoiced_amount
            invoice, = Invoice.create([{
                        'number': '1',
                        'invoice_date': period.start_date,
                        'type': 'out',
                        'party': party.id,
                        'invoice_address': party.addresses[0].id,
                        'journal': journal.id,
                        'account': receivable.id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'out',
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

            party = Party(party.id)
            self.assertEqual(party.unpayed_amount, Decimal('100.0'))
            self.assertEqual(party.pending_amount, Decimal('200.0'))
            self.assertEqual(party.draft_invoices_amount, Decimal('100.0'))
            self.assertEqual(party.uninvoiced_amount, Decimal('200.0'))
            self.assertEqual(party.credit_amount, Decimal('600.0'))


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
