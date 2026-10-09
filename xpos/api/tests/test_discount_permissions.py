import unittest
from unittest.mock import patch
import frappe
from xpos.api.discounts import validate_discount_payload

class TestDiscountPermissions(unittest.TestCase):
    def setUp(self):
        self.profile = frappe._dict(name='Till', company='LOZIRA COLLECTION', warehouse='Store', currency='MYR', selling_price_list='Retail', ignore_pricing_rule=0)
        self.data = {'customer':'General Public','items':[{'item_code':'A','qty':1,'uom':'Nos','discount_percentage':10}]}

    def test_additional_percentage_and_amount_denied(self):
        with patch('xpos.api.auth.user_has_pos_permission', return_value=False):
            for field in ['additional_discount_percentage','discount_amount']:
                with self.subTest(field=field), self.assertRaises(frappe.PermissionError):
                    validate_discount_payload({field:1},self.profile)

    def test_managers_keep_discount_permission(self):
        with patch('xpos.api.auth.user_has_pos_permission', return_value=True):
            validate_discount_payload({'additional_discount_percentage':10,'items':[{'is_free_item':1}]},self.profile)

    def test_forged_rule_does_not_authorize_discount(self):
        self.data['items'][0]['pricing_rules']='["forged"]'
        with patch('xpos.api.auth.user_has_pos_permission', return_value=False), patch('erpnext.stock.get_item_details.get_item_details', return_value={'price_list_rate':50,'rate':0,'discount_percentage':0,'pricing_rules':None}), self.assertRaises(frappe.PermissionError):
            validate_discount_payload(self.data,self.profile)

    def test_server_promotion_passes_with_both_equivalent_fields(self):
        self.data['items'][0]['discount_amount']=5
        with patch('xpos.api.auth.user_has_pos_permission', return_value=False), patch('erpnext.stock.get_item_details.get_item_details', return_value={'price_list_rate':50,'rate':0,'discount_percentage':10,'discount_amount':5,'pricing_rules':'["PROMO"]'}) as pricing:
            validate_discount_payload(self.data,self.profile)
            self.assertEqual(pricing.call_args.args[0].warehouse,'Store')
            self.assertNotIn('pricing_rules',pricing.call_args.args[0])

    def test_discount_beyond_server_promotion_denied(self):
        self.data['items'][0]['discount_percentage']=11
        with patch('xpos.api.auth.user_has_pos_permission', return_value=False), patch('erpnext.stock.get_item_details.get_item_details', return_value={'price_list_rate':50,'discount_percentage':10,'pricing_rules':['PROMO']}), self.assertRaises(frappe.PermissionError):
            validate_discount_payload(self.data,self.profile)

    def test_client_free_item_denied(self):
        with patch('xpos.api.auth.user_has_pos_permission', return_value=False), self.assertRaises(frappe.PermissionError):
            validate_discount_payload({'items':[{'is_free_item':1}]},self.profile)
