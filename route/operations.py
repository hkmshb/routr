import csv
import time
import random
import requests
from furl import furl
from collections import OrderedDict

from .common import get_client, AttrDict, OSRMService, OSRMProfile


def compute_distances(origin, *destinations):
    """Returns a table of the distances from a single source point to multiple
    destination points.
    """
    client = get_client()

    origin_coords = "{},{}".format(*origin)
    with client.for_(OSRMService.ROUTE, OSRMProfile.CAR) as cl:
        for dest in destinations:
            dest_coords = "{},{}".format(dest["dest_long"], dest["dest_lat"])
            payload = {"coordinates": [origin_coords, dest_coords]}

            resp = cl(payload=payload)
            data = AttrDict(resp.json())

            if not (data.code and data.code == "Ok" and data.routes):
                dest["distance"] = "?"
                continue

            route = data.routes[0]
            if not route:
                dest["distance"] = "?"
                continue

            try:
                dest["distance"] = route["distance"] / 100.0
            except:
                dest["distance"] = "?"
            
            # sleep in order not to overload server
            time.sleep(10)

    return (origin, destinations)


def compute(args):
    # cli task entry point
    coordset = OrderedDict()
    reader = csv.DictReader(args.source)
    for row in reader:
        origin_coord = (row["origin_long"], row["origin_lat"])
        dest_coord = {k: row[k] for k in ("dest_long", "dest_lat")}

        coords = coordset.setdefault(origin_coord, [])
        coords.append(dest_coord) 

    # process coordinates further
    results = []
    for (origin, destinations) in coordset.items():
        result = compute_distances(origin, *destinations)
        results.append(result)

    fnames = ("origin_lat", "origin_long", "dest_lat", "dest_long", "distance")
    with args.output as fp:
        writer = csv.DictWriter(fp, fnames)
        writer.writeheader()

        for (origin, destinations) in results:
            for dest in destinations:
                row = {"origin_lat": origin[0], "origin_long": origin[1], **dest}
                writer.writerow(row)
