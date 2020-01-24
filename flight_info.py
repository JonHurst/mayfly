#!/usr/bin/python3

import base64
import hashlib
import requests
import sys
from bs4 import BeautifulSoup # type: ignore
from typing import NamedTuple, Optional
import datetime as dt
import getpass

class Flight(NamedTuple):
    flight_num: str
    from_: str
    to: str
    type_: str
    reg: str
    sched_off: dt.datetime
    sched_on: dt.datetime
    off_: dt.datetime
    on_: dt.datetime

    def __repr__(self):
        return (f'{self.flight_num:9} '
                f'{self.from_} {self.to} '
                f'{self.off_:%H:%M}'
                f'({int((self.off_ - self.sched_off).total_seconds() / 60):+4d}) '
                f'{self.on_:%H:%M}'
                f'({int((self.on_ - self.sched_on).total_seconds() / 60):+4d})')

REQUEST_TIMEOUT=60

_session = None
_aims_url:Optional[str] = None

def fprint(str_: str) -> None:
    """Send str to stderr then immediately flush.

    Args:
        str: The string to send.
    """
    sys.stderr.write(str_)
    sys.stderr.flush()


def _check_response(r: requests.Response, *args, **kwargs) -> None:
    """Checks the response from a request; raises exceptions as required.
    """
    fprint(".")
    r.raise_for_status()


def logout(msg: bool = True) -> None:
    """Logout of AIMS server

    Args:
        msg: Display "Logging out . Done"
    """
    global _session, _aims_url
    if _session and _aims_url:
        if msg: fprint("\nLogging out ")
        _session.post(_aims_url + "perinfo.exe/AjAction?LOGOUT=1",
                      {"AjaxOperation": "0"}, timeout=REQUEST_TIMEOUT)
        if msg: fprint(" Done\n")


def _initialise_session() -> None:
    global _session
    _session = requests.Session()
    _session.hooks['response'].append(_check_response)
    _session.headers.update({
        "User-Agent":
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) "
        "Gecko/20100101 Firefox/64.0"})


def connect_via_ecrew(username:str, password:str) -> None:
    """Connects to AIMS server ecrew server.

    Args:
        username: AIMS username (e.g. 001234)
        password: AIMS password (8 digit or less numeric password)

    Raises:
        requests.ConnectionError:
            A network problem occured.
        requests.HTTPError:
            Request returned unsuccessful status code.
        requests.Timeout:
            No response from server within REQUEST_TIMEOUT seconds.

    Mimic the sign of procedure that a web browser would use to sign on to
    the easyJet ecrew server. Sets the _session and _aims_url globals allowing
    access to any other AIMS page.
    """
    global _session, _aims_url
    _initialise_session()
    assert(_session)
    fprint("Connecting ")
    ecrew_url = "https://ecrew.easyjet.com/wtouch/wtouch.exe/verify"
    encoded_id = base64.b64encode(username.encode()).decode()
    encoded_pw = hashlib.md5(password.encode()).hexdigest()
    r = _session.post(ecrew_url,
                      {"Crew_Id": encoded_id, "Crm": encoded_pw},
                      timeout=REQUEST_TIMEOUT)
    _aims_url = r.url.split("wtouch.exe")[0]
    #If already logged in, need to logout then login again
    if r.text.find("Please log out and try again.") != -1:
        logout(False)
        r = _session.post(ecrew_url,
                          {"Crew_Id": encoded_id, "Crm": encoded_pw},
                          timeout=REQUEST_TIMEOUT)
        _aims_url = r.url.split("wtouch.exe")[0]
    fprint(" Done\n")


def get_flight_info(d: dt.date):
    assert(_aims_url)
    assert(_session)
    dstr = dt.date.strftime(d, "%d/%m/%Y")
    url = _aims_url + "fltinfo.exe/AjAction"
    r = _session.post(url, {
        "AjaxOperation": "2",
        "cal1": dstr,
        "Airport": "brs",
        "ACRegistration": "",
        "Deps": "1",
        "Flight": "",
        "times_format": "2",
        },
                  timeout=REQUEST_TIMEOUT)
    departures = parse_flight_info_html(r.text, d)
    r = _session.post(url, {
        "AjaxOperation": "2",
        "cal1": dstr,
        "Airport": "brs",
        "ACRegistration": "",
        "Deps": "2",
        "Flight": "",
        "times_format": "2",
        },
                  timeout=REQUEST_TIMEOUT)
    arrivals = parse_flight_info_html(r.text, d)
    return(arrivals, departures)


def _to_dt(s:str, d: dt.date) -> dt.datetime:
    return dt.datetime.combine(
        d, dt.datetime.strptime(s, "%H:%M").time())


def parse_flight_info_html(html:str, d: dt.date):
    soup = BeautifulSoup(html, "html.parser")
    info = []
    for row in soup.find_all("tr"):
        data = ["".join(X.stripped_strings)
                for X in row.find_all("td")]
        info.append(Flight(
            flight_num = data[0],
            from_ = data[1],
            to = data[2],
            type_ = data[3],
            reg = data[4],
            sched_off = _to_dt(data[6].split("Z")[0], d),
            sched_on = _to_dt(data[7].split("Z")[0], d),
            off_ = _to_dt(data[8].split("Z")[0], d),
            on_ = _to_dt(data[9].split("Z")[0], d),
        ))
    return info


if __name__ == "__main__":
    connect_via_ecrew("009448", getpass.getpass())
    d = dt.date.today()
    arrivals, departures = get_flight_info(d)
    logout(True)
    print("Arrivals\n========")
    for f in sorted(arrivals, key=lambda x: x.on_): print(f)
    print("\n\nDepartures\n==========")
    for f in sorted(departures, key = lambda x: x.off_): print(f)
