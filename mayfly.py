#!/usr/bin/python3

import sys
import os
import csv
from typing import NamedTuple, List, Dict, Tuple, Optional
import datetime
import getpass
import json
import pytz

import templates
import flight_info

ezy_operator_ids = ["EZY", "EJU", "EZS"]

class Service(NamedTuple):
    """NamedTuple representing a service extracted from a Mayfly csv.

    Fields:
        type_: Either 'A' for an arrival or 'D' for a departure
        dt: For an arrival, the planned time or arrival. For a departure, the
            planned time of departure.
        operator_id: A string representing the operator. Usually two or three
            capital letters, e.g "EZY" or "FR"
        service_id: A string, usually a three or four digit number, representing
            the service e.g "455" or "1234".
        dest_or_orig: An IATA airport code, usually a three capital letter
            string. For arrivals, the origin of the flight, for departures the
            destination of the flight.
        delay: An integer representing the delay in minutes. This will be None
            unless updated from AIMS.
    """
    type_: str
    dt: datetime.datetime
    operator_id: str
    service_id: str
    dest_or_orig: str
    delay: Optional[int] = None


class MayflyBin(NamedTuple):
    """Lists of arrivals and depatures within a given time window.

    Fields:
        arrivals: list of Service objects with type_ 'A'
        departures: list of Service objects with type_ 'D'
    """
    arrivals: List[Service]
    departures: List[Service]



def process_csv(data: List[str]) -> List[Service]:
    """Map a list of lines of CSV data into a list of Service tuples

    Args:
       data: List of strings representing lines of a csv file

    Example csv line is:

    06/01/2020,A,TOM,6751,TFS,GCTS,TFS,GCTS,73H,189,0030,C,ES,04DEC2019 1403

    Interesting fields: 0: date (BRS local); 1: arrival(A) or departure(D);
    2:operator id; 3: service id; 4: origin or destination; 10: time (BRS local)
    """
    reader = csv.reader(data)
    retval: List[Service] = []
    london_tz = pytz.timezone('Europe/London')
    for row in reader:
        dt_string = row[0] + row[10]
        dt = datetime.datetime.strptime(dt_string, "%d/%m/%Y%H%M")
        utc_dt = london_tz.localize(dt).astimezone(pytz.utc).replace(tzinfo=None)
        retval.append(Service(
            type_=row[1],
            dt=utc_dt,
            operator_id=row[2],
            service_id=row[3],
            dest_or_orig=row[4]))
    return retval



def _make_update_dict(flights: List[flight_info.Flight]
) -> Dict[Service, Service]:
    """Create mappings for AIMS updates.

    Args:
        flights: A list of flight_info.Flight objects

    Returns:
        A mapping from the scheduled Service object to a Service object with
        estimated or actual times.
    """
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
    return updates


def update_services_from_AIMS(services: List[Service]
) -> Optional[List[Service]]:
    """Use AIMS to update a list of Service objects.

    Args:
        services: The list of services to apply the update to.

    Returns:
        An updated list of services or None if unable to update.

    The original input list is not changed by this function.
    """
    try:
        flights = flight_info.get_AIMS_flights(
            os.getenv("AIMSPASSWORD") or getpass.getpass(),
            datetime.date.today(), 2)
    except Exception as err:
        #much can go wrong talking to AIMS, so just return None if it throws any
        #exceptions.
        print(err, file=sys.stderr)
        return None
    updates = _make_update_dict(flights)
    retval: List[Service] = []
    for s in services:
        if s in updates:
            retval.append(updates[s])
        else:
            retval.append(s)
    return retval


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
            late_str = "hidden"
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


def build_page(data: Dict[datetime.datetime, MayflyBin],
               max_scale: int = 10,
               warm_threshold: int = 7,
               mayfly_window: int = 48,
               updated:bool = False
) -> str:
    start_bin = (
        datetime.datetime.utcnow().replace(
            minute=0, second=0, microsecond=0) -
        datetime.timedelta(hours=1))
    end_bin = start_bin + datetime.timedelta(hours=mayfly_window)
    bin_list = []
    lookup: Dict[str, List[str]] = {}
    current_bin = start_bin
    while current_bin != end_bin:
        if current_bin == start_bin or (
                current_bin.hour == 0 and current_bin.minute == 0):
            h = templates.header.format(
                    current_bin.strftime("%A %d %B"))
            bin_list.append(h)
        bin_list.append(
            build_bin(current_bin, data, max_scale, warm_threshold))
        if current_bin in data:
            for sid in [X.service_id for X in
                        data[current_bin].arrivals +
                        data[current_bin].departures
                        if X.operator_id in ezy_operator_ids]:
                if sid not in lookup: lookup[sid] = []
                lookup[sid].append(_make_id(current_bin))
        current_bin = current_bin + datetime.timedelta(minutes=30)
    return (templates.page_template.format(
        json.dumps(lookup),
        (f"Updated from AIMS at {datetime.datetime.utcnow():%H:%Mz}"
         if updated else "AIMS update not available"),
        templates.table_template.format(
            "".join(bin_list))))


def main(csv_filename: str, html_filename: str) -> None:
    with open(csv_filename) as f:
        services = process_csv(f.readlines())
        updated_services = update_services_from_AIMS(services)
        updated = False
        if updated_services:
            services = updated_services
            updated = True
        bins = split_into_bins(services)
        with open(html_filename, "w") as o:
            o.write(build_page(bins, updated=updated))


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("usage:", sys.argv[0], "csv_file html_file")
