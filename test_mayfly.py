import unittest
import mayfly
import datetime
import flight_info

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


    def test_update_dict_create(self):
        data = [
            flight_info.Flight(operator='EZY', flight_num='570', from_='BRS', to='NCL',
                               type_='319', reg='G-EZBV',
                               sched_off=datetime.datetime(2020, 1, 30, 20, 50),
                               sched_on=datetime.datetime(2020, 1, 30, 21, 55),
                               off=datetime.datetime(2020, 1, 30, 21, 50),
                               on=datetime.datetime(2020, 1, 30, 22, 55)),
            flight_info.Flight(operator='EZY', flight_num='571', from_='NCL', to='BRS',
                               type_='319', reg='G-EZBV',
                               sched_off=datetime.datetime(2020, 1, 31, 20, 50),
                               sched_on=datetime.datetime(2020, 1, 31, 21, 55),
                               off=datetime.datetime(2020, 1, 31, 20, 50),
                               on=datetime.datetime(2020, 1, 31, 21, 55)),
            ]
        result = {
            mayfly.Service(type_='D', dt=datetime.datetime(2020, 1, 30, 20, 50),
                           operator_id='EZY', service_id='570',
                           dest_or_orig='NCL', delay=None):
            mayfly.Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 50),
                           operator_id='EZY', service_id='570',
                           dest_or_orig='NCL', delay=60),
            mayfly.Service(type_='A', dt=datetime.datetime(2020, 1, 31, 21, 55),
                           operator_id='EZY', service_id='571',
                           dest_or_orig='NCL', delay=None):
            mayfly.Service(type_='A', dt=datetime.datetime(2020, 1, 31, 21, 55),
                           operator_id='EZY', service_id='571',
                           dest_or_orig='NCL', delay=0),

        }
        self.maxDiff = None
        self.assertEqual(mayfly._make_update_dict(data), result)
        self.assertEqual(mayfly._make_update_dict([]), {})
        with self.assertRaises(AttributeError) as cm:
            mayfly._make_update_dict("wrong type of data")
