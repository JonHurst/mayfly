import unittest
import mayfly
import datetime
import flight_info
import os
import getpass
from mayfly import MayflyBin, Service

class TestMayfly(unittest.TestCase):

    def setUp(self):
        def monkey_patch_get_AIMS_flights(_1, _2, _3):
            return [
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
        self.get_AIMS_flights_orig = flight_info.get_AIMS_flights
        flight_info.get_AIMS_flights = monkey_patch_get_AIMS_flights
        self.getpass_orig = getpass.getpass
        def monkey_patch_getpass(): return None
        getpass.getpass = monkey_patch_getpass


    def tearDown(self):
        flight_info.get_AIMS_flights = self.get_AIMS_flights_orig
        getpass.getpass = self.getpass_orig


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


    def test_update_services_from_AIMS(self):
        data = [
            mayfly.Service(type_='D', dt=datetime.datetime(2020, 1, 30, 20, 50),
                           operator_id='EZY', service_id='570',
                           dest_or_orig='NCL', delay=None),
            mayfly.Service(type_='A', dt=datetime.datetime(2020, 1, 31, 21, 55),
                           operator_id='EZY', service_id='571',
                           dest_or_orig='NCL', delay=None),
        ]
        result = [
            mayfly.Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 50),
                           operator_id='EZY', service_id='570',
                           dest_or_orig='NCL', delay=60),
            mayfly.Service(type_='A', dt=datetime.datetime(2020, 1, 31, 21, 55),
                           operator_id='EZY', service_id='571',
                           dest_or_orig='NCL', delay=0),
        ]
        self.assertEqual(mayfly.update_services_from_AIMS(data), result)
        self.assertEqual(mayfly.update_services_from_AIMS([]), [])
        def raise_exception(_1, _2, _3):
            raise ValueError("Test exception")
        old = flight_info.get_AIMS_flights
        flight_info.get_AIMS_flights = raise_exception
        self.assertEqual(mayfly.update_services_from_AIMS(data), None)
        flight_info.get_AIMS_flights = old


    def test_split_into_bins(self):
        data = [
            mayfly.Service(type_='D', dt=datetime.datetime(2020, 1, 30, 20, 50),
                           operator_id='EZY', service_id='570',
                           dest_or_orig='NCL', delay=None),
            mayfly.Service(type_='A', dt=datetime.datetime(2020, 1, 30, 21, 55),
                           operator_id='EZY', service_id='571',
                           dest_or_orig='NCL', delay=None),
        ]
        for mins in range(10, 70, 10):
            for n in (0, 1):
                data.append(
                    data[n]._replace(
                        dt = data[n].dt + datetime.timedelta(minutes=mins),
                        service_id = str(int(data[n].service_id) + mins)))
        result = {
    datetime.datetime(2020, 1, 30, 20, 30): MayflyBin(
        arrivals=[],
        departures=[
            Service(type_='D', dt=datetime.datetime(2020, 1, 30, 20, 50), operator_id='EZY', service_id='570', dest_or_orig='NCL', delay=None)]),
    datetime.datetime(2020, 1, 30, 21, 0): MayflyBin(
        arrivals=[],
        departures=[Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 0), operator_id='EZY', service_id='580', dest_or_orig='NCL', delay=None),
                    Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 10), operator_id='EZY', service_id='590', dest_or_orig='NCL', delay=None),
                    Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 20), operator_id='EZY', service_id='600', dest_or_orig='NCL', delay=None)]),
    datetime.datetime(2020, 1, 30, 21, 30): MayflyBin(
        arrivals=[Service(type_='A', dt=datetime.datetime(2020, 1, 30, 21, 55), operator_id='EZY', service_id='571', dest_or_orig='NCL', delay=None)],
        departures=[Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 30), operator_id='EZY', service_id='610', dest_or_orig='NCL', delay=None),
                    Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 40), operator_id='EZY', service_id='620', dest_or_orig='NCL', delay=None),
                    Service(type_='D', dt=datetime.datetime(2020, 1, 30, 21, 50), operator_id='EZY', service_id='630', dest_or_orig='NCL', delay=None)]),
    datetime.datetime(2020, 1, 30, 22, 0): MayflyBin(
        arrivals=[Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 5), operator_id='EZY', service_id='581', dest_or_orig='NCL', delay=None),
                  Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 15), operator_id='EZY', service_id='591', dest_or_orig='NCL', delay=None),
                  Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 25), operator_id='EZY', service_id='601', dest_or_orig='NCL', delay=None)],
        departures=[]),
    datetime.datetime(2020, 1, 30, 22, 30): MayflyBin(
        arrivals=[Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 35), operator_id='EZY', service_id='611', dest_or_orig='NCL', delay=None),
                  Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 45), operator_id='EZY', service_id='621', dest_or_orig='NCL', delay=None),
                  Service(type_='A', dt=datetime.datetime(2020, 1, 30, 22, 55), operator_id='EZY', service_id='631', dest_or_orig='NCL', delay=None)],
        departures=[])}
        self.assertEqual(mayfly.split_into_bins(data), result)
