import os
import enum
import logging
import requests
import threading
from furl import furl
from contextlib import contextmanager
from dotenv import find_dotenv, load_dotenv
from . import exceptions as exc


log = logging.getLogger(__name__)
__all__ = [
    "EnumMixin", "OSRMProfile", "OSRMService", "OSRMClient",
    "get_client", "config"
]


# singleton instances: thread-local
__threadlocal = threading.local()


class AttrDict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None


class EnumMixin:
    @classmethod
    def resolve(cls, value):
        if isinstance(value, cls):
            return value
        if value in [c.name for c in cls]:
            return cls[value]
        if value in [c.value for c in cls]:
            return cls(value)

        errmsg = f"Invalid value provided for {cls.__name__}: {value}"
        raise ValueError(errmsg)


class APIClient:
    """Defines base interface expected of a client interacting with an
    external service.
    """
    SERVICE_NAME = None
    DEFAULT_HEADERS = ()

    def __init__(self, urlbase, apikey=None):
        if "://" not in urlbase or urlbase.startswith("://"):
            raise ValueError("urlbase must specify a scheme")
        
        if urlbase and urlbase.endswith("/"):
            urlbase = urlbase[:-1]

        self.urlbase = urlbase
        self.apikey = apikey

    def _build_url(self, urlpath=None, **params):
        furlobj = furl(self.urlbase, path=urlpath, args=params)
        log.debug(f"built service url: {furlobj.url}")

        return furlobj

    def __call__(self, urlpath=None, payload=None, headers=None, as_get=True):
        """Performs a request to an external service.

        A GET request is made by default if as_get remains True and payload is
        treated as the query params otherwise a POST request is made if as_get
        is False.
        """
        request_headers = dict(self.DEFAULT_HEADERS)
        request_headers.update(headers or {})

        if as_get:
            furlobj = self._build_url(urlpath, **payload)
            resp = requests.get(furlobj.url, headers=request_headers)
        else:
            payload = payload or []
            request_url = self._build_url(urlpath)
            resp = request.post(
                furlobj.url, headers=request_headers, json=payload
            )
        return resp

    def __repr__(self):
        """Returns string representation for inistances.
        """
        return "<APIClient urlbase={urlbase} ({service_name})>".format(
            urlbase=self.urlbase, service_name=self.SERVICE_NAME
        )


class OSRMProfile(EnumMixin, enum.Enum):
    BIKE = "bike"
    CAR  = "car"
    FOOT = "foot"


class OSRMService(EnumMixin, enum.Enum):
    ROUTE = "route"
    MATCH = "match"
    NEAREST = "nearest"
    TABLE = "table"
    TRIP = "trip"
    TILE = "tile"


class OSRMClient(APIClient):
    """Client for interacting with the OSRM hosted demo routing server.
    """
    SERVICE_NAME="OSRM"
    REQUIRED_PAYLOAD_ENTRIES=("coordinates",)

    def __init__(
        self, urlbase, apikey=None, service=None,
        version="v1", profile=OSRMProfile.CAR
    ):
        super().__init__(urlbase, apikey=apikey)
        self.service = OSRMService.resolve(service or "route")
        self.profile = OSRMProfile.resolve(profile)
        self.version = version or "v1"

    def _build_url(self, urlpath=None, **params):
        if not params:
            raise exc.ValidationError("payload is required")
        
        for entry in self.REQUIRED_PAYLOAD_ENTRIES:
            if entry not in params:
                raise exc.ValidationError("'{entry}' missing from payload")

        # ignore whatever urlpath that was provided and build another
        urlpath = f"/{self.service.value}/{self.version}/{self.profile.value}"

        # include coordinates
        coordinates = params.pop("coordinates")
        if not isinstance(coordinates, (list, tuple)):
            coordinates = list(coordinates)

        coords = ";".join([c.strip() for c in coordinates if c])
        urlpath = f"{urlpath}/{coords}.json"

        return super()._build_url(urlpath, **params)

    @contextmanager
    def for_(self, service, profile):
        yield self.__class__(self.urlbase, service, profile=profile)


def load_config():
    """Load configuration from ENV VARS for now.
    """
    def norm(key):
        # normalize ENV VAR names
        return key[7:].lower().replace("_", ".")

    if hasattr(__threadlocal, "config"):
        return

    load_dotenv(find_dotenv())

    # read in all ENV VARS that begin with "ROUTE__"
    config = AttrDict({
        norm(key): value
        for (key, value) in os.environ.items()
        if key.startswith("ROUTE__")
    })

    # refine configs namespaced to provides service name so they become the
    # default configs (by dropping the service name)...
    service_tag = f"{config.service.upper()}."
    for key in config.keys():
        if key.upper().startswith(service_tag):
            # drop service name in key
            config[key[len(service_tag):]] = config[key]
            del config[key]

    setattr(__threadlocal, "config", config)


def get_config():
    """Returns the configuration dict stored on the thread-local if present
    otherwise config is load from all available sources, set on thread-local
    then returned.
    """
    if not hasattr(__threadlocal, "config"):
        load_config()

    return __threadlocal.config


def get_client():
    """Returns the APIClient instance set on the thread-local if present
    otherwise one is created using available configuration and set on the
    thread-local then returned.
    """
    if not hasattr(__threadlocal, "client"):
        config = get_config()

        service = config.get("engine", "OSRM")
        client_cls = OSRMClient if service == "OSRM" else APIClient
        client = client_cls(config.urlbase, config.apikey)
        setattr(__threadlocal, "client", client)

    return __threadlocal.client
