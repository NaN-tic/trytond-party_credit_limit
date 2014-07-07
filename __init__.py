# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .party import *


def register():
    Pool.register(
        Party,
        module='party_credit_limit', type_='model')
    Pool.register(
        OpenLimit,
        module='party_credit_limit', type_='wizard')
