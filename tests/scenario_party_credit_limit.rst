=================
AEAT 349 Scenario
=================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Install aeat_349 module::

    >>> config = activate_modules('party_credit_limit')

Create company::

    >>> eur = get_currency('EUR')
    >>> _ = create_company(currency=eur)
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']

Create tax::

    >>> Tax = Model.get('account.tax')
    >>> TaxCode = Model.get('account.tax.code')
    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()
    >>> invoice_base_code = create_tax_code(tax, 'base', 'invoice')
    >>> invoice_base_code.save()
    >>> invoice_tax_code = create_tax_code(tax, 'tax', 'invoice')
    >>> invoice_tax_code.save()
    >>> credit_note_base_code = create_tax_code(tax, 'base', 'credit')
    >>> credit_note_base_code.save()
    >>> credit_note_tax_code = create_tax_code(tax, 'tax', 'credit')
    >>> credit_note_tax_code.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

    >>> party.credit_amount == Decimal('0.0')
    True
    >>> party.unpayed_amount == Decimal('0.0')
    True
    >>> party.pending_amount == Decimal('0.0')
    True
    >>> party.draft_invoices_amount == Decimal('0.0')
    True
    >>> party.uninvoiced_amount == Decimal('0.0')
    True
    >>> party.limit_percent == Decimal('100.0')
    True
    >>> party.amount_to_limit == Decimal('0.0')
    True

    >>> party.credit_limit_amount = Decimal('1000.0')
    >>> party.save()

    >>> party.credit_amount == Decimal('0.0')
    True
    >>> party.unpayed_amount == Decimal('0.0')
    True
    >>> party.pending_amount == Decimal('0.0')
    True
    >>> party.draft_invoices_amount == Decimal('0.0')
    True
    >>> party.uninvoiced_amount == Decimal('0.0')
    True
    >>> party.limit_percent == Decimal('0.0')
    True
    >>> party.amount_to_limit == Decimal('1000.0')
    True

Create account categories::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

    >>> account_category_tax, = account_category.duplicate()
    >>> account_category_tax.customer_taxes.append(tax)
    >>> account_category_tax.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.account_category = account_category_tax
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create an Inventory::

    >>> Inventory = Model.get('stock.inventory')
    >>> Location = Model.get('stock.location')
    >>> storage, = Location.find([
    ...         ('code', '=', 'STO'),
    ...         ])
    >>> inventory = Inventory()
    >>> inventory.location = storage
    >>> inventory_line = inventory.lines.new(product=product)
    >>> inventory_line.quantity = 100.0
    >>> inventory_line.expected_quantity = 0.0
    >>> inventory.click('confirm')
    >>> inventory.state
    'done'

Create 2 Moves::

    >>> Journal = Model.get('account.journal')
    >>> journal, = Journal.find([], limit=1)
    >>> today = datetime.date.today()
    >>> yesterday = today - relativedelta(days=1)
    >>> Move = Model.get('account.move')
    >>> MoveLine = Model.get('account.move.line')

    >>> move = Move()
    >>> move.journal = journal
    >>> move.period = period
    >>> move.date = period.start_date
    >>> move_line = move.lines.new()
    >>> move_line.debit = Decimal(100)
    >>> move_line.account = receivable
    >>> move_line.party = party
    >>> move_line.maturity_date = yesterday
    >>> move_line = move.lines.new()
    >>> move_line.credit = Decimal(100)
    >>> move_line.account = revenue
    >>> move.save()

    >>> move = Move()
    >>> move.journal = journal
    >>> move.period = period
    >>> move.date = period.start_date
    >>> move_line = move.lines.new()
    >>> move_line.debit = Decimal(200)
    >>> move_line.account = receivable
    >>> move_line.party = party
    >>> move_line = move.lines.new()
    >>> move_line.credit = Decimal(200)
    >>> move_line.account = revenue
    >>> move.save()

Create sale::

    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = party
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = product
    >>> sale_line.quantity = 1.0
    >>> sale_line.unit_price = Decimal('200.0')
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.click('process')

    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = party
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = product
    >>> sale_line.quantity = 1.0
    >>> sale_line.unit_price = Decimal('50.0')
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.click('process')

    >>> party.reload()
    >>> party.unpayed_amount == Decimal('100.0')
    True
    >>> party.pending_amount == Decimal('200.0')
    True
    >>> party.draft_invoices_amount == Decimal('250.0')
    True
    >>> party.uninvoiced_amount == Decimal('0.0')
    True
    >>> party.limit_percent == Decimal('55.0')
    True

    >>> party.credit_limit_amount = Decimal('500.0')
    >>> party.save()

    >>> party.limit_percent == Decimal('110.0')
    True
    >>> party.amount_to_limit == Decimal('-50.0')
    True

Create out invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term
    >>> invoice.invoice_date = period.start_date
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.unit_price = Decimal(50)
    >>> line.quantity = 1
    >>> invoice.save()
    >>> invoice.click('post')

    >>> party.reload()
    >>> party.unpayed_amount == Decimal('155.0')
    True
    >>> party.pending_amount == Decimal('200.0')
    True
    >>> party.draft_invoices_amount == Decimal('250.0')
    True
    >>> party.uninvoiced_amount == Decimal('0.0')
    True
    >>> party.credit_amount == Decimal('605.0')
    True
