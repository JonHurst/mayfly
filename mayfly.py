#!/usr/bin/python3

import sys
import os
import csv
from typing import NamedTuple, List, Dict, Tuple
import datetime

import templates
import flight_info

ezy_operator_ids = ["EZY", "EJU", "EZS"]

class Service(NamedTuple):
    dt: datetime.datetime
    operator_id: str
    service_id: str
    dest_or_orig: str
    delay: int = 0


class MayflyBin(NamedTuple):
    arrivals: List[Service]
    departures: List[Service]


def process_csv(data: List[str], updates: Dict[Service, Service]
) -> Dict[datetime.datetime, MayflyBin]:
    reader = csv.reader(data)
    retval: Dict[datetime.datetime, MayflyBin] = {}
    for row in reader:
        #todo: check data integrity
        dt_string = row[0] + row[10]
        dt = datetime.datetime.strptime(dt_string, "%d/%m/%Y%H%M")
        #todo: convert time to UTC
        service = Service(dt, row[2], row[3], row[4])
        if service in updates:
            service = updates[service]
        if service.dt.minute < 30:
            bin_id = service.dt.replace(minute=0)
        else:
            bin_id = service.dt.replace(minute=30)
        if bin_id not in retval:
            retval[bin_id] = MayflyBin([], [])
        if row[1] == "A":
            retval[bin_id].arrivals.append(service)
        elif row[1] == "D":
            retval[bin_id].departures.append(service)
    return retval


def _make_id(dt: datetime.datetime) -> str:
    return "id" + dt.strftime("%y%m%d%H%M")


def build_service_list(services: List[Service]
) -> str:
    global ezy_operator_ids
    output_strings: List[str] = []
    for s in services:
        template = templates.nonezy_service_template
        if s.operator_id in ezy_operator_ids:
            output_strings.append(templates.ezy_service_template.format(
                s.dt.strftime("%H:%M"),
                "{}{} {}".format(s.operator_id, s.service_id, s.dest_or_orig),
                "late" if s.delay > 0 else "not_late",
                s.delay))
        else:
            output_strings.append(templates.nonezy_service_template.format(
                s.dt.strftime("%H:%M"),
                "{}{} {}".format(s.operator_id, s.service_id, s.dest_or_orig)))
    return templates.service_list_template.format(
        "".join(output_strings))


def build_bin(current_bin: datetime.datetime,
              data: Dict[datetime.datetime, MayflyBin],
              max_scale: int, warm_threshold: int
) -> str:
    arrivals_count, departures_count = 0, 0
    arrivals_listing, departures_listing = "", ""
    if current_bin in data:
        arrivals_count = len(data[current_bin].arrivals)
        arrivals_listing = build_service_list(
            data[current_bin].arrivals)
        departures_count = len(data[current_bin].departures)
        departures_listing = build_service_list(
            data[current_bin].departures)
    heat = "cool"
    if departures_count + arrivals_count >= warm_threshold:
        heat = "warm"
    arrivals_width = arrivals_count * 100 // max_scale
    if arrivals_width > 100: arrivals_width = 100
    departures_width = departures_count * 100 // max_scale
    if departures_width > 100: departures_width = 100
    return (templates.bin_template.format(
        _make_id(current_bin),
        current_bin,
        heat,
        arrivals_width,
        str(arrivals_count) if arrivals_count else " ",
        arrivals_listing,
        departures_width,
        str(departures_count) if departures_count else " ",
        departures_listing))


def build_javascript_lookup_object(
        data: Dict[datetime.datetime, MayflyBin],
        start_bin: datetime.datetime,
        end_bin: datetime.datetime
) -> str:
    global ezy_operator_ids
    reverse_dict: Dict[str, List[datetime.datetime]] = {}
    for key in data:
        if key < start_bin or key >= end_bin: continue
        for _list in (data[key].arrivals, data[key].departures):
            for service in _list:
                if service.operator_id not in ezy_operator_ids:
                   continue
                if service.service_id not in reverse_dict:
                    reverse_dict[service.service_id] = []
                reverse_dict[service.service_id].append(key)
    pairs = []
    for service_id in reverse_dict:
        pairs.append('"{}": [{}]'.format(
            service_id,
            ", ".join(['"' + _make_id(X) + '"'
                       for X in reverse_dict[service_id]])))
    return "var lookup = {" + ", ".join(pairs) + "};"


def build_page(data: Dict[datetime.datetime, MayflyBin],
               max_scale: int = 10,
               warm_threshold: int = 7,
               mayfly_window: int = 48
) -> str:
    start_bin = (
        datetime.datetime.utcnow().replace(
            minute=0, second=0, microsecond=0) -
        datetime.timedelta(hours=1))
    end_bin = start_bin + datetime.timedelta(hours=mayfly_window)
    bin_list = []
    current_bin = start_bin
    while current_bin != end_bin:
        if current_bin == start_bin or (
                current_bin.hour == 0 and current_bin.minute == 0):
            h = templates.header.format(
                    current_bin.strftime("%A %d %B"))
            bin_list.append(h)
        bin_list.append(
            build_bin(current_bin, data, max_scale, warm_threshold))
        current_bin = current_bin + datetime.timedelta(minutes=30)
    return (templates.page_template.format(
        build_javascript_lookup_object(data, start_bin, end_bin),
        templates.table_template.format(
            "".join(bin_list))))


def create_update_dict():
    flight_info.connect_via_ecrew("009448",
                                  os.getenv("AIMSPASSWORD"))
    d = datetime.date.today()
    arrivals, departures = flight_info.get_flight_info(d)
    ret = {}
    for f in arrivals:
        if f.sched_on == f.on_: continue
        flight_num_components = f.flight_num.split()
        service_id = flight_num_components[-1]
        op_id = "EZY"
        if len(flight_num_components) == 2:
            op_id = flight_num_components[0]
        delay = int((f.on_ - f.sched_on).total_seconds() / 60)
        ret[Service(
            dt=f.sched_on,
            operator_id=op_id,
            service_id=service_id,
            dest_or_orig=f.from_)] = Service(dt=f.on_,
                                             operator_id=op_id,
                                             service_id=service_id,
                                             dest_or_orig=f.from_,
                                             delay=delay)
    for f in departures:
        if f.sched_off == f.off_: continue
        flight_num_components = f.flight_num.split()
        service_id = flight_num_components[-1]
        op_id = "EZY"
        if len(flight_num_components) == 2:
            op_id = flight_num_components[0]
        delay = int((f.off_ - f.sched_off).total_seconds() / 60)
        ret[Service(
            dt=f.sched_off,
            operator_id=op_id,
            service_id=service_id,
            dest_or_orig=f.to)] = Service(dt=f.off_,
                                          operator_id=op_id,
                                          service_id=service_id,
                                          dest_or_orig=f.to,
                                          delay=delay)
    flight_info.logout(True)
    return ret


def main(csv_filename: str, html_filename: str) -> None:
    updates = create_update_dict()
    with open(csv_filename) as f:
        bins = process_csv(f.readlines(), updates)
        with open(html_filename, "w") as o:
            o.write(build_page(bins))


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("usage:", sys.argv[0], "csv_file html_file")
