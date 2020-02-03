#!/usr/bin/python3

import sys
from bs4 import BeautifulSoup # type: ignore
from typing import NamedTuple, Optional, List
import datetime as dt
import getpass

import aims


class Flight(NamedTuple):
    """The data from a line of an AIMS flight info table.

    :var operator: Three letter code of operator. Currently either "EZY", "EJU" or "EZS".
    :var flight_num: Flight number, usually a three or four digit number.
    :var from_: Origin of the flight.
    :var to: Destination of the flight.
    :var type_: The type of aircraft (e.g. A320)
    :var reg: The registratioin of the aircraft.
    :var sched_off: The scheduled off blocks time.
    :var sched_on: The scheduled on blocks time.
    :var off: The actual or estimated off blocks time.
    :var on: The actual or estimated on blocks time.
    """
    operator: str
    flight_num: str
    from_: str
    to: str
    type_: str
    reg: str
    sched_off: dt.datetime
    sched_on: dt.datetime
    off: dt.datetime
    on: dt.datetime


def _to_dt(s:str, d: dt.date) -> dt.datetime:
    return dt.datetime.combine(
        d, dt.datetime.strptime(s, "%H:%M").time())


def parse_flight_info_html(html:str, d: dt.date
) -> List[Flight]:
    """Extract flight data from AIMS html.

    :param html: The html from the AIMS flight info table.

    :returns: A list of Flight objects corresponding to the lines of the table.
    """
    soup = BeautifulSoup(html, "html.parser")
    info = []
    for row in soup.find_all("tr"):
        data = ["".join(X.stripped_strings)
                for X in row.find_all("td")]
        try:
            l = data[0].split()
            info.append(Flight(
                operator = l[0] if len(l) == 2 else "EZY",
                flight_num = l[-1],
                from_ = data[1],
                to = data[2],
                type_ = data[3],
                reg = data[4],
                sched_off = _to_dt(data[6].split("Z")[0], d),
                sched_on = _to_dt(data[7].split("Z")[0], d),
                off = _to_dt(data[8].split("Z")[0], d),
                on = _to_dt(data[9].split("Z")[0], d),
            ))
        except ValueError as err:
            print(str(err), file=sys.stderr)
    return info


def get_AIMS_flights(pw: str, d: dt.date, count: int = 1) -> List[Flight]:
    """Get specified flights from AIMS.

    :param pw: AIMS password.
    :param d: The first date required.
    :param count: The number of days required.

    :returns: A list of Flight objects including arrivals and departures for all
              the specified dates.
    """
    assert(count > 0)
    aims.connect("009448", pw)
    flights: List[Flight] = []
    for type_ in ("A", "D"):
        for n in range(count):
            date = dt.date.today() + dt.timedelta(days=n)
            html = aims.flight_info(date, type_)
            flights.extend(parse_flight_info_html(html, date))
    aims.logout(True)
    return flights


if __name__ == "__main__":
    def key(flight):
        if flight.from_ == "BRS":
            return flight.off
        return flight.on
    import getpass
    flights = sorted(
        get_AIMS_flights(
            getpass.getpass(), dt.date.today(), 2),
        key=key)
    for flight in flights:
        mov = "A" if flight.to == "BRS" else "D"
        print("{} {:8} {} {} {} {}".format(
            mov, flight.operator + flight.flight_num,
            flight.from_, flight.to,
            flight.off.strftime("[%d]%H:%M"),
            flight.on.strftime("[%d]%H:%M")))
