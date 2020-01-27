import unittest
import mayfly
import datetime

class TestMayfly(unittest.TestCase):

    def test_csv_import(self):
        data = ["06/01/2020,A,TOM,6751,TFS,GCTS,TFS,GCTS,"
                "73H,189,0030,C,ES,04DEC2019 1403",
                "01/06/2020,A,TOM,6751,TFS,GCTS,TFS,GCTS,"
                "73H,189,0030,C,ES,04DEC2019 1403"]
        result = [
            mayfly.Service(
                type_='A',
                dt=datetime.datetime(2020, 1, 6, 0, 30),
                operator_id='TOM',
                service_id='6751',
                dest_or_orig='TFS',
                delay=None),
            mayfly.Service(
                type_='A',
                dt=datetime.datetime(2020, 5, 31, 23, 30),
                operator_id='TOM',
                service_id='6751',
                dest_or_orig='TFS',
                delay=None)]
        self.assertEqual(
            mayfly.process_csv(data),
            result)


    def test_csv_import_bad_format(self):
        data = ["06/01/2020,TOM,6751,TFS,GCTS,TFS,GCTS,"
                "73H,189,0030,C,ES,04DEC2019 1403"]
        with self.assertRaises(ValueError) as cm:
            mayfly.process_csv(data)
