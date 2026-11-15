# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


# Prices before rate cards (Nov 2026). The doctype stays so its rows survive the migration that moves
# them onto rate cards (patches/v1_0/move_prices_to_rate_cards.py); nothing else uses it.
class ReturnFee(Document):
	pass
