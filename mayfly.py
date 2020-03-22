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

    :var type_: Either 'A' for an arrival or 'D' for a departure
    :var dt: For an arrival, the planned time or arrival.  For a departure, the
             planned time of departure.
    :var operator_id: A string representing the operator.  Usually two or three
        capital letters, e.g "EZY" or "FR"
    :var service_id: A string, usually a three or four digit number,
        representing the service e.g "455" or "1234".
    :var dest_or_orig: An IATA airport code, usually a three capital letter
        string.  For arrivals, the origin of the flight, for departures the
        destination of the flight.
    :var delay: An integer representing the delay in minutes.  This will be None
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

    :var arrivals: list of Service objects with type_ 'A'
    :var departures: list of Service objects with type_ 'D'
    """
    arrivals: List[Service]
    departures: List[Service]



def process_csv(data: List[str]) -> List[Service]:
    """Map a list of lines of CSV data into a list of Service tuples

    Example csv line is:

    06/01/2020,A,TOM,6751,TFS,GCTS,TFS,GCTS,73H,189,0030,C,ES,04DEC2019 1403

    Interesting fields: 0: date (BRS local); 1: arrival(A) or departure(D);
    2:operator id; 3: service id; 4: origin or destination; 10: time (BRS local)

    :param data: List of strings representing lines of a csv file

    :returns: A corresponding list of Service objects
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
) -> Dict[Service, Optional[Service]]:
    """Create mappings for AIMS updates.

    :param flights: A list of flight_info.Flight objects

    :returns: A mapping from the scheduled Service object to a Service object
              with estimated or actual times.
    """
    updates: Dict[Service, Optional[Service]] = {}
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
        orig = Service(type_=type_, dt=dt,
                        operator_id=f.operator,
                        service_id=f.flight_num,
                        dest_or_orig=dest_or_orig)
        if f.reg[:5] == "X-CAN":
            updates[orig] = None
        else:
            updates[orig] = orig._replace(
                dt=new_dt, delay=int(delay.total_seconds() / 60))
    return updates


def update_services_from_AIMS(services: List[Service]
) -> Optional[List[Service]]:
    """Use AIMS to update a list of Service objects.

    :param services: The list of services to apply the update to.

    :returns: An updated list of services or None if unable to update.  The
              original input list is not changed by this function.
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
            update = updates[s]
            if update is not None:
                retval.append(update)
        else:
            retval.append(s)
    return retval


def split_into_bins(services: List[Service]
) -> Dict[datetime.datetime, MayflyBin]:
    """Organise Service objects into 30 minute bins.

    :param services: A list of Service objects.

    :returns: A dictionary with bin label (start datetime of the bin) as key and
              a MayflyBin object as data.
    """
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
    """Build an html list from a list of Service objects.

    The templates.ezy_service_template template is used for list items where the
    operator_id of the service is one of the ids listed in the ezy_operator_ids
    global, otherwise templates.nonezy_service_template is used.  These
    templates have all the fields of the Service object available as keywords.
    In addition they have the following keywords available:

    * "time": The time part of the dt field, formatted as HH:MM

    * "delay_str": The delay formatted as (+X) for late, (-X) for early or an
    empty string for unknown, where X is the delay in minutes

    * "late_str": A string that is either "late" if late, "not_late" if not late
    or "delay_unknown" if no AIMS data is available.

    The list items are concatenated in time order, and then wrapped in
    templates.service_list_template.

    :param services: A list of Service objects.

    :returns: A string containing an html list.
    """
    global ezy_operator_ids
    output_strings: List[str] = []
    for s in sorted(services, key=lambda x: x.dt):
        s_dict = s._asdict()
        s_dict["time"] = s.dt.strftime("%H:%M")
        if s.delay is None:
            s_dict["late_str"] = "delay_unknown"
            s_dict["delay_str"] = ""
        else:
            s_dict["late_str"] = "late" if s.delay > 0 else "not_late"
            s_dict["delay_str"] = "({:+d})".format(s.delay)
        template = (templates.ezy_service_template
                    if s.operator_id in ezy_operator_ids
                    else templates.nonezy_service_template)
        output_strings.append(template.format(**s_dict))
    return templates.service_list_template.format(
        "".join(output_strings))


def build_bin(current_bin: datetime.datetime,
              data: Optional[MayflyBin],
              max_scale: int,
              heat_map_params: Tuple[float, float, float]
) -> str:
    """Produce an html table row from a MayflyBin.

    :param current_bin: The datetime object that acts as the identifier for the
        bin to be processed.
    :param data: The MayflyBin object to be processed
    :param max_scale: The number of services to use as full scale.  If there are
        more services than full scale, they wil be presented as full scale.
    :param heat_map_params: A tuple containing the heat map parameters.

        The heat map parameters are (x, w1, w2).  x is the balance between
        arrivals and departures, with x = 0.5 being equally balanced and x > 0.5
        meaning arrivals are considered more significant than departures.  w1
        and w2 are the thresholds for the two warning levels.  Levels below w1
        are supposed to indicate that inbound delays are unlikely, between w1
        and w2 that moderate inbound delays are likely and above w2 that
        significant inbound delays are likely.

    :returns: The html of a table row.
    """
    t_dict = {
        "bin_id": _make_id(current_bin),
        "bin_start_time": current_bin.strftime("%H:%M"),
        "arrivals_count": " ", "departures_count": " ",
        "arrivals_width": "0%", "departures_width": "0%",
        "arrivals_listing": "", "departures_listing": "",
        "heat": "w0"
        }
    if data:
        t_dict["arrivals_count"] = str(len(data.arrivals) or " ")
        t_dict["departures_count"] = str(len(data.departures) or " ")
        a = len(data.arrivals) * 100 // max_scale
        t_dict["arrivals_width"] = "100%" if a > 100 else str(a) + "%"
        d = len(data.departures) * 100 // max_scale
        t_dict["departures_width"] = "100%" if d > 100 else str(d) + "%"
        t_dict["arrivals_listing"] = build_service_list(data.arrivals)
        t_dict["departures_listing"] = build_service_list(data.departures)
        x, w1, w2 = heat_map_params
        h = x * len(data.arrivals) + (1 - x) * len(data.departures)
        if h >= w1: t_dict["heat"] = "w1"
        if h >= w2: t_dict["heat"] = "w2"
    return templates.bin_template.format(**t_dict)


def build_page(
        data: Dict[datetime.datetime, MayflyBin],
        max_scale: int = 10,
        heat_map_params: Tuple[float, float, float] = (0.6, 3.5, 4.74),
        mayfly_window: int = 48,
        updated:bool = False
) -> str:
    """Create an html page from a dictionary of MayflyBin objects.

    :param data: The dictionary containing the source data.  Keys are bin
        identifiers in the form of datetime objects (the start time of the bin),
        values are MayflyBin objects.
    :param max_scale: The number of arrivals or departures that will cause the
        bar to be full width.  If the number of arrivals or depatures is greater
        than max_scale, the bar will be shown full width with but labelled with
        the correct number.
    :param heat_map_params: A tuple containing the parameters used to determine
        the colour of the background of each bin.  See build_bin documentation
        for details.
    :param mayfly_window: The number of hours worth of bins to output.
    :param updated: If True, indicates that the mayfly data has been updated
        with AIMS data.

    :return: The html page.  This contains a table with the bins and a
             javascript variable, lookup, that can be used to quickly lookup in
             which bins a particular flight number occurs.
    """
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
            build_bin(current_bin, data.get(current_bin, None),
                      max_scale, heat_map_params))
        #Create a dictionary to serialize and insert as the 'lookup' javascript
        #variable. Key is service number, value is a list of bin identifiers in
        #which flights with that service number may be found.
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
