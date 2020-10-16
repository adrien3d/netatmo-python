from os import getenv
import json
import requests
import time

_CLIENT_ID     = getenv("NETATMO_CLIENT_ID")
_CLIENT_SECRET = getenv("NETATMO_CLIENT_SECRET")
_USERNAME      = getenv("NETATMO_USERNAME")
_PASSWORD      = getenv("NETATMO_PASSWORD")

_BASE_URL = "https://api.netatmo.com/"
_AUTH_REQ              = _BASE_URL + "oauth2/token"
_GET_MEASURE_REQ        = _BASE_URL + "api/getmeasure"
_GET_STATIONDATA_REQ    = _BASE_URL + "api/getstationsdata"
_GET_THERMOSTATDATA_REQ = _BASE_URL + "api/getthermostatsdata"
_GET_HOMEDATA_REQ       = _BASE_URL + "api/gethomedata"
_GET_CAMERAPICTURE_REQ  = _BASE_URL + "api/getcamerapicture"
_GET_EVENTSUNTIL_REQ    = _BASE_URL + "api/geteventsuntil"

_CAM_CDE_GET_SNAP     = "/live/snapshot_720.jpg"

_CAM_CHANGE_STATUS     = "/command/changestatus?status=%s"            # "on"|"off"

# To test
_PRES_DETECTION_KIND   = ("humans", "animals", "vehicles", "movements")
_PRES_DETECTION_SETUP  = ("ignore", "record", "record & notify")

UNITS = {
    "unit" : {
        0: "metric",
        1: "imperial"
    },
    "windunit" : {
        0: "kph",
        1: "mph",
        2: "ms",
        3: "beaufort",
        4: "knot"
    },
    "pressureunit" : {
        0: "mbar",
        1: "inHg",
        2: "mmHg"
    }
}


class Authentication:
    def __init__(self, client_id=_CLIENT_ID,
                       client_secret=_CLIENT_SECRET,
                       username=_USERNAME,
                       password=_PASSWORD,
                       scope="read_station read_camera access_camera write_camera read_smokedetector " \
                             "read_presence access_presence write_presence read_thermostat write_thermostat"):
        post_params = {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
            "scope": scope
        }
        r = PostRequest(_AUTH_REQ, post_params)
        if r.status_code > 201: raise "Authentication request rejected"

        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = json.loads(r.text)['access_token']
        self._refresh_token = json.loads(r.text)['refresh_token']
        self._scope = json.loads(r.text)['scope']
        self._expiration = int(json.loads(r.text)['expire_in'] + time.time())

    @property
    def access_token(self):
        if self._expiration < time.time(): # Token should be renewed
            post_params = {
                "grant_type": "refresh_token",
                "refresh_token": self._refreshToken,
                "client_id": self._clientId,
                "client_secret": self._clientSecret
            }
            r = PostRequest(_AUTH_REQ, post_params)
            self._access_token = json.loads(r.text)['access_token']
            self._refresh_token = json.loads(r.text)['refresh_token']
            self._expiration = int(json.loads(r.text)['expire_in'] + time.time())
        return self._access_token


class UserInformations:
    pass


class Weather:
    def __init__(self, auth_data):
        if auth_data:
            self._access_token = auth_data.access_token
            '''self._refresh_token = auth_data._refresh_token
            self._scope = auth_data._scope
            self._expiration = auth_data._expiration'''

    def get_stations_data(self):
        post_params = {
            "access_token" : self._access_token
        }
        r = PostRequest(_GET_STATIONDATA_REQ, post_params)
        self.raw_data = json.loads(r.text)['body']
        if not self.raw_data : raise "No weather station available"
        self.station = self.raw_data['devices'][0]

        user_data = self.raw_data['user']
        self.user = UserInformations()
        setattr(self.user, "mail", user_data['mail'])
        for k, v in user_data['administrative'].items():
            if k in UNITS:
                setattr(self.user, k, UNITS[k][v])
            else:
                setattr(self.user, k, v)

        self.master = {
            "name": self.station["module_name"],
            "data": self.station["dashboard_data"]
        }

        outside = [e for e in self.station["modules"] if e["type"] == "NAModule1"][0]
        self.outside = {
            "name": outside["module_name"],
            "data": outside["dashboard_data"]
        }

        secondary = [e for e in self.station["modules"] if e["type"] == "NAModule4"][0]
        self.secondary = {
            "name": secondary["module_name"],
            "data": secondary["dashboard_data"]
        }

        return self


def PostRequest(url, params=None, timeout=10):
    if params:
        r = requests.post(url, data=params)
    else:
        r = requests.post(url)
    return r