import gpxpy
import gpxpy.gpx
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import argparse
import numpy as np
import zipfile
import gzip
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
import pandas as pd
import gzip
import re
import multiprocessing
import argparse
import math

IMG_DIR = "images"


def load_data(export_dir: str, starting_date: str, bounds):
    """
    :param export_dir: the path to the dir strava activities file
    :param starting_date: an optional starting date formatted as MM-DD-YYYY
    :return:
    """
    activities_df = pd.read_csv(f'{export_dir}activities.csv')
    activities_df['Activity Date'] = pd.to_datetime(activities_df['Activity Date'])

    # filter activities by starting date
    if starting_date:
        activities_df = activities_df[activities_df['Activity Date'] > pd.to_datetime(starting_date)]

    filenames = activities_df['Filename'].dropna().tolist()

    activity_dict = {}

    for activity_filename in filenames:
        activity_filename = os.path.join(export_dir, activity_filename)
        if '.tcx' in activity_filename:
            with gzip.open(activity_filename, 'rb') as f:
                xml_str = f.read().decode("utf-8")
                xml_str = re.sub('xmlns=".*?"', '', xml_str)
                xml_str = xml_str.replace('          ', '')
                root = ET.fromstring(xml_str)
                activities = root.findall('.//Activity')
                for activity in activities:
                    print(f' loading {activity_filename}:{activity.attrib['Sport']}')
                    if activity.attrib['Sport'] in ['Biking', 'Running', 'Alpine Ski']:
                        lats = []
                        longs = []
                        alts = []
                        tracking_points = activity.findall('.//Trackpoint')
                        for tracking_point in list(tracking_points):
                            children = list(tracking_point)
                            latitude = float(list(children[1])[0].text)
                            longitude = float(list(children[1])[1].text)
                            alt = float(children[2].text)
                            lats.append(latitude)
                            longs.append(longitude)
                            alts.append(alt)
                            activity_dict[f'{activity_filename}'] = {
                                'lat': lats,
                                'lon': longs,
                                'alt': alts
                            }
        elif '.gpx' in activity_filename:
            with open(activity_filename, "r") as gpx_file:
                gpx = gpxpy.parse(gpx_file)
            print(f' loading {activity_filename}')
            data = {"lat": [], "lon": [], "alt": []}
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        data["lat"].append(point.latitude)
                        data["lon"].append(point.longitude)
                        data["alt"].append(point.elevation)  # Elevation in meters
            activity_dict[f'{activity_filename}'] = data

    routes = activity_dict.values()
    # filter routes based on bounds
    routes = list(filter(
        lambda r: r["lon"][0] > bounds['left'] and r["lon"][0] < bounds['right'] and r["lat"][0] > bounds[
            'bottom'] and r["lat"][0] < bounds['top'], routes))
    print(len(routes))
    return routes


def plot_routes(routes, max_len, step, r, bounds):
    all_altitudes = np.concatenate([route["alt"] for route in routes])
    # Normalize altitude values for colormap
    norm = mcolors.Normalize(vmin=all_altitudes.min(), vmax=all_altitudes.max())

    # Create figure
    fig, ax = plt.subplots(figsize=(9, 16))
    for route in routes:
        latitudes = np.array(route["lat"][0:r])
        longitudes = np.array(route["lon"][0:r])
        altitudes = np.array(route["alt"][0:r])

        # Create line segments
        points = np.array([longitudes, latitudes]).T.reshape(-1, 1, 2)
        segments = np.hstack([points[:-1], points[1:]])

        # Create LineCollection for multiple segments
        lc = LineCollection(segments, cmap='gist_earth', norm=norm, linewidth=1, alpha=0.3)
        lc.set_array(altitudes[:-1])  # Color based on altitude
        ax.add_collection(lc)

    ax.set_aspect(1.0)
    ax.set_xlim([bounds['left'], bounds['right']])
    ax.set_ylim([bounds['bottom'], bounds['top']])
    plt.axis('off')
    plt.tight_layout()
    fname = f'./{IMG_DIR}/{str(r // step).zfill(4)}-export'
    print(f'saving {fname} out of {max_len / step}')
    plt.savefig(fname, dpi=300)
    plt.close()


def get_bounding_box(lat, lon, radius_km):
    """Calculate a 9:16 aspect ratio bounding box from lat/lon and radius."""

    # Earth's radius in km
    earth_radius = 6371.0

    # Aspect ratio calculation: Height = 16 parts, Width = 9 parts
    aspect_height = (16 / math.sqrt(9 ** 2 + 16 ** 2)) * radius_km * 2  # Total height
    aspect_width = (9 / math.sqrt(9 ** 2 + 16 ** 2)) * radius_km * 2  # Total width

    # Convert latitude to radians
    lat_rad = math.radians(lat)

    # Angular distances for latitude and longitude
    angular_distance_lat = aspect_height / (2 * earth_radius)
    angular_distance_lon = aspect_width / (2 * earth_radius)

    # Calculate new latitude bounds
    lat_min = lat - math.degrees(angular_distance_lat)
    lat_max = lat + math.degrees(angular_distance_lat)

    # Calculate new longitude bounds, adjusting for latitude
    lon_delta = math.degrees(angular_distance_lon / math.cos(lat_rad))
    lon_min = lon - lon_delta
    lon_max = lon + lon_delta

    return {
        "top": lat_max,
        "bottom": lat_min,
        "left": lon_min,
        "right": lon_max
    }


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Calculate bounding box from lat/lon and radius.")
    parser.add_argument("export_dir", type=str, help="File path (not used in calculations)")
    parser.add_argument("latitude", type=float, help="Latitude of the center point")
    parser.add_argument("longitude", type=float, help="Longitude of the center point")
    parser.add_argument("radius", type=float, help="Radius in kilometers")
    parser.add_argument("starting_date", type=str)
    parser.add_argument("step", type=int)

    args = parser.parse_args()
    os.makedirs(IMG_DIR, exist_ok=True)

    bounds = get_bounding_box(args.latitude, args.longitude, args.radius)
    print(bounds)
    routes = load_data(args.export_dir, args.starting_date, bounds)
    multiprocessing.set_start_method('spawn')

    max_len = 0
    step = args.step

    for t in routes:
        if len(t['lat']) > max_len:
            max_len = len(t['lat'])
    ranges = np.arange(0, max_len, step)

    processes = []
    for r in ranges:
        if r > 0:
            p = multiprocessing.Process(target=plot_routes, args=(routes, max_len, step, r, bounds))
            processes.append(p)
            p.start()

    # Wait for all processes to finish
    print('waiting for processes')
    for p in processes:
        p.join()


if __name__ == '__main__':
    main()
