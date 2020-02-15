import unittest

from main import OtodomParser


class TestAdditionalMethods(unittest.TestCase):
    def test_empty_address_string(self):
        self.assertRaises(Exception, OtodomParser, 123)

    def test_remove_blank_strings(self):
        data = [' ', 'a', 'b', 33, '', None]
        result = OtodomParser.remove_blank_strings(data)
        self.assertEqual(result, ['a', 'b', 33])

    def test_remove_unnecessary_elements(self):
        data = ['Mieszkanie na sprzedaż: Warszawa, Mokotów', '    No spaces 1', 'No spaces 2 ']
        result = OtodomParser.remove_unnecessary_elements(data)
        self.assertEqual(result, ['Mokotów', 'No spaces 1', 'No spaces 2'])

    def test_list_from_offer(self):
        from test_utils import arcticle as data
        from bs4 import BeautifulSoup
        offer = BeautifulSoup(data, 'html.parser').find_all('article')[0]
        result = OtodomParser.prepare_list_from_offer(offer)
        self.assertEqual(len(result), 21)

    def test_parser(self):
        import os

        url = 'https://www.otodom.pl/sprzedaz/mieszkanie/warszawa/' \
              '?search%5Bfilter_float_price%3Ato%5D=450000&search%5Bfilter_float_m' \
              '%3Afrom%5D=50&search%5Bdist%5D=0&search%5Bsubregion_id%5D=197&search%5Bcity_id%5D=26&nrAdsPerPage=1'

        parser = OtodomParser(url, 1, 'test.csv')
        parser.parse()
        self.assertTrue(os.path.isfile('./test.csv'))
        os.remove('./test.csv')

