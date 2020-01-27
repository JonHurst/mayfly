import requests
import sys
import os
import datetime as dt
from typing import Optional
import base64
import hashlib


REQUEST_TIMEOUT = os.getenv("AIMS_TIMEOUT") or 60

_session = None
_aims_url:Optional[str] = None


def _check_response(r: requests.Response, *args, **kwargs) -> None:
    """Checks the response from a request; raises exceptions as required.
    """
    _fprint(".")
    r.raise_for_status()


def _fprint(str_: str) -> None:
    """Send str to stderr then immediately flush.

    Args:
        str: The string to send.
    """
    sys.stderr.write(str_)
    sys.stderr.flush()


def _initialise_session() -> None:
    """Set up headers and hooks."""
    global _session
    _session = requests.Session()
    _session.hooks['response'].append(_check_response)
    _session.headers.update({
        "User-Agent":
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) "
        "Gecko/20100101 Firefox/64.0"})


def _login(username:str, password:str, recurse: bool = True) -> None:
    global _session, _aims_url
    ecrew_url = "https://ecrew.easyjet.com/wtouch/wtouch.exe/verify"
    encoded_id = base64.b64encode(username.encode()).decode()
    encoded_pw = hashlib.md5(password.encode()).hexdigest()
    _initialise_session()
    assert(_session)
    r = _session.post(ecrew_url,
                      {"Crew_Id": encoded_id, "Crm": encoded_pw},
                      timeout=REQUEST_TIMEOUT)
    _aims_url = r.url.split("wtouch.exe")[0]
    #If already logged in, need to logout then login again
    if r.text.find("Please log out and try again.") != -1:
        logout(False)
        if recurse: _login(username, password, False)


def connect(username:str, password:str) -> None:
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
    _fprint("Connecting ")
    _login(username, password)
    _fprint(" Done\n")


def logout(msg: bool = True) -> None:
    """Logout of AIMS server

    Args:
        msg: Display "Logging out . Done"
    """
    global _session, _aims_url
    if _session and _aims_url:
        if msg: _fprint("\nLogging out ")
        _session.post(_aims_url + "perinfo.exe/AjAction?LOGOUT=1",
                      {"AjaxOperation": "0"}, timeout=REQUEST_TIMEOUT)
        _aims_url, _session = None, None
        if msg: _fprint(" Done\n")


def flight_info(d: dt.date, type_: str, airport: str="brs") -> str:
    """Get HTML of flight info page

    Args:
        d: Date to retrieve data for
        type_: "A" for arrivals or "D" for departures
    """
    global _session, _aims_url
    assert(_session)
    assert(_aims_url)
    assert(type_ == "A" or type_ == "D")
    dstr = dt.date.strftime(d, "%d/%m/%Y")
    url = _aims_url + "fltinfo.exe/AjAction"
    deps = "1" if type_ == "D" else "2"
    r = _session.post(
        url, {
        "AjaxOperation": "2",
        "cal1": dstr,
        "Airport": airport,
        "ACRegistration": "",
        "Deps": deps,
        "Flight": "",
        "times_format": "2",
        },
        timeout=REQUEST_TIMEOUT)
    return r.text


if __name__ == "__main__":
    import getpass
    connect("009448", getpass.getpass())
    print(flight_info(
        dt.date.today(),
        "A"))
