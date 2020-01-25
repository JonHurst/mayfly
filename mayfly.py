#!/usr/bin/python3

import sys
import os
import csv
from typing import NamedTuple, List, Dict, Tuple, Optional
import datetime
import getpass

import templates
import flight_info

ezy_operator_ids = ["EZY", "EJU", "EZS"]

class Service(NamedTuple):
    type_: str
    dt: datetime.datetime
    operator_id: str
    service_id: str
    dest_or_orig: str
    delay: Optional[int] = None


class MayflyBin(NamedTuple):
    arrivals: List[Service]
    departures: List[Service]


def process_csv(data: List[str]) -> List[Service]:
    """Map a list of lines of CSV data into a list of Service tuples

    Args:
       data: List of strings representing lines of a csv file
"""
    reader = csv.reader(data)
    retval: List[Service] = []
    for row in reader:
        #todo: check data integrity
        dt_string = row[0] + row[10]
        dt = datetime.datetime.strptime(dt_string, "%d/%m/%Y%H%M")
        #todo: convert time to UTC
        retval.append(Service(
            type_=row[1],
            dt=dt,
            operator_id=row[2],
            service_id=row[3],
            dest_or_orig=row[4]))
    return retval


def update_services_from_AIMS(services: List[Service]
) -> Optional[List[Service]]:
    try:
        flights = flight_info.get_AIMS_flights(
            os.getenv("AIMSPASSWORD") or getpass.getpass(),
            datetime.date.today(), 2)
        updates = {}
        for f in flights:
            if f.from_ == "BRS":
                type_ = "D"
                delay = f.off - f.sched_off
                dest_or_orig = f.to
                dt = f.sched_off
                new_dt = f.off
            else:
                type_ = "A"
                delay = f.on - f.sched_on
                dest_or_orig = f.from_
                dt = f.sched_on
                new_dt = f.on
            updates[Service(type_=type_, dt=dt,
                            operator_id=f.operator,
                            service_id=f.flight_num,
                            dest_or_orig=dest_or_orig)] = (
                    Service(type_=type_, dt=new_dt,
                            operator_id=f.operator,
                            service_id=f.flight_num,
                            dest_or_orig=dest_or_orig,
                            delay=int(delay.total_seconds() / 60)))
        retval: List[Service] = []
        for s in services:
            if s in updates:
                retval.append(updates[s])
            else:
                retval.append(s)
        return retval
    except Exception as err:
        #much can go wrong talking to AIMS, so just return None if it does.
        print(err, file=sys.stderr)
        return None


def split_into_bins(services: List[Service]
) -> Dict[datetime.datetime, MayflyBin]:
    retval: Dict[datetime.datetime, MayflyBin] = {}
    for service in services:
        if service.dt.minute < 30:
            bin_id = service.dt.replace(minute=0)
        else:
            bin_id = service.dt.replace(minute=30)
        if bin_id not in retval:
            retval[bin_id] = MayflyBin([], [])
        if service.type_ == "A":
            retval[bin_id].arrivals.append(service)
        elif service.type_ == "D":
            retval[bin_id].departures.append(service)
    return retval


def _make_id(dt: datetime.datetime) -> str:
    return "id" + dt.strftime("%y%m%d%H%M")


def build_service_list(services: List[Service]
) -> str:
    global ezy_operator_ids
    output_strings: List[str] = []
    for s in sorted(services, key=lambda x: x.dt):
        template = templates.nonezy_service_template
        if s.delay is None:
            late_str = ""
            delay = 0
        else:
            late_str = "late" if s.delay > 0 else "not_late"
            delay = s.delay
        if s.operator_id in ezy_operator_ids:
            output_strings.append(templates.ezy_service_template.format(
                s.dt.strftime("%H:%M"),
                "{}{} {}".format(s.operator_id, s.service_id, s.dest_or_orig),
                late_str, delay))
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


def main(csv_filename: str, html_filename: str) -> None:
    with open(csv_filename) as f:
        services = process_csv(f.readlines())
        services = update_services_from_AIMS(services) or services
        bins = split_into_bins(services)
        with open(html_filename, "w") as o:
            o.write(build_page(bins))


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("usage:", sys.argv[0], "csv_file html_file")
