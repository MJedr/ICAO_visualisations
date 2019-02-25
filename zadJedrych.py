import argparse
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re
import os
from math import sin, cos, sqrt, atan2, radians

dir_path = os.path.dirname(os.path.realpath(__file__))

def load_data(data_dir=dir_path, detailed_data_folder='simple_avia_par'):
    data_codes = (os.path.join(data_dir, 'airport-codes.csv'))
    data_country_cds = (os.path.join(data_dir, 'country_codes.txt'))
    airports = pd.read_csv(data_codes)
    country = pd.read_csv(data_country_cds, sep=';')

    path = (os.path.join(data_dir, detailed_data_folder))
    all_files = glob.glob(path + "/*.tsv")

    datasets = []
    for f in all_files:
        df = pd.read_csv(f, sep='\t')
        df['year'] = (int(f.split('_')[-1][:-4]))  # bierzemy ostatni element nazwy i pozbawiamy go z rozszerzenia
        datasets.append(df)

    frame = pd.concat(datasets, axis=0, ignore_index=True)
    frame['airport_dep'] = frame.code_dep.str.split('_').str.get(1)
    frame['iso_code_dep'] = frame.code_dep.str.split('_').str.get(0)
    frame['airport_arr'] = frame.code_arr.str.split('_').str.get(1)
    frame['iso_code_arr'] = frame.code_arr.str.split('_').str.get(0)
    frame = frame.drop(columns=['code_dep', 'code_arr'])
    frame.seats.replace(":", np.nan, inplace=True)

    return airports, country, frame


# funckcja obliczająca odległości
def calculate_distance(latt1, long1, latt2, long2):
    R = 6373.0

    lat1 = radians(latt1)
    lon1 = radians(long1)
    lat2 = radians(latt2)
    lon2 = radians(long2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def plot_country_airports(county_code, plot_name='traffic_plot.png'):
    airports, country, frame = load_data()

    arrivals = frame[frame.iso_code_arr == county_code].groupby(['year', 'airport_arr']).sum().unstack()
    departures = frame[frame.iso_code_dep == county_code].groupby(['year', 'airport_dep']).sum().unstack()

    last_year_arrivals = arrivals.apply(lambda x: x[x.notnull()].values[-1]).rename("arrivals") # pomija nulle
    last_year_departures = departures.apply(lambda x: x[x.notnull()].values[-1]).rename("departures")

    last_year_traffic = pd.concat([last_year_arrivals, last_year_departures], axis=1, join='inner')

    last_year_traffic["sum"] = last_year_traffic.sum(axis=1)
    last_year_traffic.index = last_year_traffic.index.set_names(['variable', 'airport_code'])
    last_year_traffic = last_year_traffic.reset_index().sort_values(by=['sum'], ascending=False)

    # wizualizacja
    ax = sns.barplot(data=last_year_traffic, x="airport_code", y="sum")
    ax.set_title("Airports for {}".format(county_code))
    plt.xlabel("Airport ICAO code")
    plt.ylabel("Passangers [thousands]")
    plt.savefig(plot_name)
    plt.show()


def plot_country_traffic(county_code, plot_name='traffic_plot.png'):
    airports, country, frame = load_data()

    selected_data = frame[(frame.iso_code_dep == county_code)][['passengers', 'airport_dep', 'year']]
    selected_data_pivot = pd.pivot_table(selected_data, index=['airport_dep', 'year'], values='passengers',
                                         aggfunc=np.sum) # grupuje wg. roku i liczy sumę pasażerow
    selected_data_pivot = selected_data_pivot.reset_index()

    # wizualizacja
    ax = sns.lineplot(data=selected_data_pivot, x='year', hue='airport_dep', y='passengers')
    ax.set_title("Traffic at {}".format(county_code))
    ax.get_legend().texts[0].set_text('Airport')
    plt.savefig(plot_name)
    plt.show()


def plot_airport_partners(airport_name, plot_name='plot_airport.png'):
    airports, country, frame = load_data()
    departures = frame[(frame.airport_dep == airport_name) & (frame.year == 2015)][['airport_arr', 'passengers']]
    departures = departures.rename(columns={'passengers': 'passengers_from'})
    arrivals = frame[(frame.airport_arr == airport_name) & (frame.year == 2015)][['airport_dep', 'passengers']]
    arrivals = arrivals.rename(columns={'passengers': 'passengers_to'})

    traffic = arrivals.merge(departures, left_on='airport_dep', right_on='airport_arr', how='outer')
    traffic = traffic.fillna(value=0)
    traffic['passengers_sum'] = traffic.apply(lambda row: row.passengers_to + row.passengers_from, axis=1)
    traffic_sorted = traffic.sort_values(by=['passengers_sum'], ascending=False)
    traffic_top10 = traffic_sorted.head(10)

    # wizualizacja
    ax = sns.barplot(data=traffic_top10, x="airport_arr", y="passengers_sum")
    ax.set_title("Largest partners of {}".format(airport_name))
    plt.xlabel("Destination airport")
    plt.ylabel("Passangers [thousands]")
    plt.savefig(plot_name)
    plt.show()


def plot_airport_capacity(airport_name, plot_name='plot_airport.png'):
    airports, country, frame = load_data()
    selected_data = frame[(frame.airport_dep == airport_name)]
    last_year = max(selected_data.year)
    selected_data.seats = selected_data.seats.astype("float16")
    selected_data_year = selected_data.loc[(selected_data.year == last_year)]

    # wizualizacja
    ax = sns.regplot(data=selected_data_year, y='passengers', x='seats')
    ax.set_title("Passangers vs. capacity for {}".format(airport_name))
    ax.set_xlabel("Passangers [thousands]")
    ax.set_ylabel("Avaiable seats [thousands]")
    plt.savefig(plot_name)
    plt.show()


def plot_airport_distance(airport_name, plot_name='plot_airport.png'):
    airports, country, frame = load_data()
    departures = frame[(frame.airport_dep == airport_name)]
    departures = departures[(departures.year == max(departures.year))][['airport_arr', 'passengers']]
    airports_coords = airports[['ident', 'latitude_deg', 'longitude_deg']]

    coordsChosen = airports[(airports.ident == airport_name)][['latitude_deg', 'longitude_deg']]
    y = coordsChosen.iloc[0]['latitude_deg']
    x = coordsChosen.iloc[0]['longitude_deg']

    departures_with_coords = departures.merge(airports_coords, left_on='airport_arr', right_on='ident')
    departures_with_coords['distance'] = departures_with_coords.apply(
        lambda row: calculate_distance(y, x, row.latitude_deg, row.longitude_deg), axis=1)
    departures_with_coords = departures_with_coords.sort_values(by=['distance'])

    # wizualizacja
    ax = sns.regplot(data=departures_with_coords, y='passengers', x='distance')
    ax.set_title("Passangers vs. distance for {}".format(airport_name))
    ax.set(xscale="log", yscale="log")
    ax.set_xlabel("Distance [km] log10")
    ax.set_ylabel("Passangers [thousands] log10")
    plt.savefig(plot_name)
    plt.show()


def print_route(year, origin, destination):
    airports, country, frame = load_data()

    connection = frame[(frame.year ==  year)&(frame.airport_dep == origin)&(frame.airport_arr == destination)]
    if len(connection.index) < 1:
        print('No connection found!')
        sys.exit(1)
    traffic_seats = connection[['passengers', 'seats']]
    traffic = traffic_seats.values[0][0]
    round(traffic * 1000)
    seats = traffic_seats.values[0][1]
    seats = round(float(seats) * 1000)

    name_country_origin = airports[airports.ident == origin][['name', 'iso_country']]
    name_origin = airports.at[name_country_origin.index[0], "name"]
    country_origin_aberr = airports.at[name_country_origin.index[0], 'iso_country']
    country_origin = country[country.iso_country == country_origin_aberr]['country'].values[0]
    country_origin = country_origin[0] + country_origin[1:].lower()

    name_country_destination = airports[airports.ident == destination][['name', 'iso_country']]
    name_destination = airports.at[name_country_destination.index[0], "name"]
    country_destination_aberr = airports.at[name_country_destination.index[0], 'iso_country']
    country_destination = country[country.iso_country == country_destination_aberr]['country'].values[0]
    country_destination = country_destination[0] + country_destination[1:].lower()

    coords_origin = airports[airports.ident == origin][['latitude_deg', 'longitude_deg']]
    yo, xo = coords_origin['latitude_deg'].values[0], coords_origin['longitude_deg'].values[0]
    coords_dest = airports[airports.ident == destination][['latitude_deg', 'longitude_deg']]
    yd, xd = coords_dest['latitude_deg'].values[0], coords_dest['longitude_deg'].values[0]
    distance = round(calculate_distance(yo, xo, yd, xd))

    info_details = (f"""Route information ({year}):
                    Origin: {name_origin} ({origin}) airport in {country_origin} ({country_origin_aberr}),
                    Destination: {name_destination} {destination} airport in {country_destination} ({country_destination_aberr}),
                    Distance: {distance} km,
                    Passangers: {traffic} thousands,
                    Avaiable seats: {seats}""")
    return info_details


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get info about selected track.')
    parser.add_argument('year', help='The year', type=int)
    parser.add_argument('airport_origin', help='Origin airport.', type = str)
    parser.add_argument('airport_destination', help='Destination airport.', type = str)
    args = parser.parse_args()

    info = print_route(args.year, args.airport_origin, args.airport_destination)
    print(info)