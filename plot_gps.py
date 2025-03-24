import gpxpy
import gpxpy.gpx
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import argparse
import numpy as np
import zipfile
import gzip
import os
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
import pandas as pd
import gzip
import re
import multiprocessing

acts_df = pd.read_csv('/Users/jonathan.jung/Downloads/export_5879226/activities.csv')
acts_df['Activity Date'] = pd.to_datetime(acts_df['Activity Date'])
#acts_df = acts_df[acts_df['Activity Date'] > pd.to_datetime('1/1/2024')]

filenames = acts_df['Filename'].dropna().tolist()

act_dict = {}


for activity_filename in filenames:
    print(activity_filename)
    if '.tcx' in activity_filename:
        activity_filename = os.path.join('/Users/jonathan.jung/Downloads/export_5879226/', activity_filename)
        with gzip.open(activity_filename, 'rb') as f:
            xml_str = f.read().decode("utf-8")
            xml_str = re.sub('xmlns=".*?"', '', xml_str)
            xml_str = xml_str.replace('          ', '')
            root = ET.fromstring(xml_str)
            activities = root.findall('.//Activity')
            for activity in activities:
                print('-- {} --'.format(activity.attrib['Sport']))
                if activity.attrib['Sport'] in ['Biking', 'Running', 'Other', 'Walk']:
                    lats = []
                    longs = []
                    alts = []
                    tracking_points = activity.findall('.//Trackpoint')
                    for tracking_point in list(tracking_points):
                        children = list(tracking_point)
                        time = children[0].text
                        # hr = list(children[4])[0].text
                        latitude = float(list(children[1])[0].text)
                        longitude = float(list(children[1])[1].text)
                        alt = float(children[2].text)
                        # print('Time: {}, HR: {}, Alt: {}, Coor: [{},{}]'.format(time, hr, alt, latitude, longitude))
                        lats.append(latitude)
                        longs.append(longitude)
                        alts.append(alt)
                        act_dict[f'{activity_filename}']=  {
                                'lat': lats,
                                'lon': longs,
                                'alt': alts
                        }

routes = act_dict.values()
left_bound = -118.45
right_bound = -118
lower_bound = 33.7
upper_bound = 34.3
routes = list(filter(lambda r: r["lon"][0] > left_bound and r["lon"][0] < right_bound and r["lat"][0] > lower_bound and r["lat"][0] < upper_bound, routes))
print(len(routes))
# Extract all latitude, longitude, and altitude values for normalization
all_latitudes = np.concatenate([route["lat"] for route in routes])
all_longitudes = np.concatenate([route["lon"] for route in routes])
all_altitudes = np.concatenate([route["alt"] for route in routes])

print(f'{np.min(all_latitudes)} - {np.max(all_latitudes)}')
print(f'{np.min(all_longitudes)} - {np.max(all_longitudes)}')


max_len = 0

for t in routes:
    if len(t['lat']) > max_len:
        max_len = len(t['lat'])

# Normalize altitude values for colormap
norm = mcolors.Normalize(vmin=all_altitudes.min(), vmax=all_altitudes.max())

# Create figure
step = 10
ranges = np.arange(0, max_len, step)

for r in ranges:
    if r > 0:
        fig, ax = plt.subplots(figsize=(9, 16), dpi=150)
        # Plot all route segments
        for route in routes:
            latitudes = np.array(route["lat"][0:r])
            longitudes = np.array(route["lon"][0:r])
            altitudes = np.array(route["alt"][0:r])

            # Create line segments
            points = np.array([longitudes, latitudes]).T.reshape(-1, 1, 2)
            segments = np.hstack([points[:-1], points[1:]])

            # Create colormap based on altitude
            # colors = cm.plasma(norm(altitudes[:-1]))

            # Create LineCollection for multiple segments
            lc = LineCollection(segments, cmap='gist_earth', norm=norm, linewidth=1, alpha=0.3)
            lc.set_array(altitudes[:-1])  # Color based on altitude
            ax.add_collection(lc)
            # if r != ranges[-1]:
            #     ax.scatter(longitudes[-1], latitudes[-1], color='red', s=2, zorder=3)

            # Scatter waypoints
            # ax.scatter(longitudes, latitudes, color='black', s=40)


        # Colorbar
        # cbar = fig.colorbar(lc, ax=ax, orientation='vertical', label="Altitude (m)")

        ax.set_aspect(1.0)
        ax.set_xlim([left_bound, right_bound])
        ax.set_ylim([lower_bound, upper_bound])
        # ax.set_xlim([-118.4, -118.1])
        # ax.set_ylim([34, 34.16])
        plt.axis('off')
        plt.tight_layout()
        fname = f'./images/{str(r // step).zfill(4)}-export'
        print(f'saving {fname} out of {max_len/step}')

        plt.savefig(fname, dpi=600)
        plt.close() 