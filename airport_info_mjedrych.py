import argparse
import sys
import numpy as np
import pandas as pd
import glob
import os
from math import sin, cos, sqrt, atan2, radians

# MD: lepsza struktura, ale ta funkcjonalność była i tak krótka...

def load_data(data_dir='.', detailed_data_folder='simple_avia_par'):
    data_codes = (os.path.join(data_dir,'airport-codes.csv'))
    data_country_cds = (os.path.join(data_dir,'country_codes.txt'))
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

    # czyszczenie danych - podział na osobne kolumny
    # kolumna airport - departure
    airport_dep = frame.code_dep.str.split('_').str.get(1)

    # kolumna z kodem iso dla lotniska odlotu
    iso_code_dep = frame.code_dep.str.split('_').str.get(0)

    # kolumna airport_arr
    airport_arr = frame.code_arr.str.split('_').str.get(1)

    # kolumna z kodem iso dla lotniska docelowego
    iso_code_arr = frame.code_arr.str.split('_').str.get(0)

    # dołączenie utworzonych kolumn do ramki danych
    frame["airport_dep"] = airport_dep
    frame["iso_code_dep"] = iso_code_dep
    frame["airport_arr"] = airport_arr
    frame["iso_code_arr"] = iso_code_arr

    # wyrzucenie zbędnych kolumn
    frame = frame.drop(columns=['code_dep', 'code_arr'])  # deleted 'seats' from list

    return airports, country, frame


def calculate_distance(latt1, long1, latt2, long2):
    """ Funkcja obliczcająca odległośc pomiędz dwoma punktami """

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


def print_route(airports, country, airports_data, year, origin, destination):

    # pobór nazwy lotniska wylotu
    name_country_origin = airports[airports['ident'] == origin][['name', 'iso_country']]
    print(name_country_origin)
    name_origin = airports.at[name_country_origin.index[0], "name"]
    # pobór nazwy państwa wylotu
    country_origin_aberr = airports.at[name_country_origin.index[0], 'iso_country']
    country_origin = country[country.iso_country == country_origin_aberr]['country'].values[0]
    country_origin = country_origin[0] + country_origin[1:].lower()

    # pobór nazwy lotniska docelowego
    name_country_destination = airports[airports.ident == destination][['name', 'iso_country']]
    name_destination = airports.at[name_country_destination.index[0], "name"]
    # pobór nazwy państwa docelowego
    country_destination_aberr = airports.at[name_country_destination.index[0], 'iso_country']
    country_destination = country[country.iso_country == country_destination_aberr]['country'].values[0]
    country_destination = country_destination[0] + country_destination[1:].lower()

    # pobranie informacji o natężeniu ruchu i liczbie miejsc na trasie
    traffic_seats = airports_data[(airports_data.year == year) & (airports_data.airport_dep == origin) &
                                  (airports_data.airport_arr == destination)][['passengers', 'seats']]
    # jeżeli nie ma połączenia - zatrzymaj program
    try:
        traffic = traffic_seats.values[0][0]
    except IndexError:
        print('No connection found')
        sys.exit(1)
    round(traffic * 1000)
    seats = traffic_seats.values[0][1]
    seats = round(float(seats) * 1000)

    # obliczenie dystansu na trasie
    coords_origin = airports[airports.ident == origin][['latitude_deg', 'longitude_deg']]
    yo, xo = coords_origin['latitude_deg'].values[0], coords_origin['longitude_deg'].values[0]
    coords_dest = airports[airports.ident == destination][['latitude_deg', 'longitude_deg']]
    yd, xd = coords_dest['latitude_deg'].values[0], coords_dest['longitude_deg'].values[0]
    distance = round(calculate_distance(yo, xo, yd, xd))

    # wypisanie informacji o trasie
    info_details = (f"""Route information ({year}):
                        Origin: {name_origin} ({origin}) airport in {country_origin} ({country_origin_aberr}),
                        Destination: {name_destination} {destination} airport in {country_destination} ({country_destination_aberr}),
                        Distance: {distance} km,
                        Passangers: {traffic},
                        Avaiable seats: {seats}""")
    return info_details


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get info about selected track.')
    parser.add_argument('year', help='The year', type = int)
    parser.add_argument('airport_origin', help='Origin airport.', type = str)
    parser.add_argument('airport_destination', help='Destination airport.', type = str)
    args = parser.parse_args()

    info = print_route(args.year, args.airport_origin, args.airport_destination)
    print(info)
