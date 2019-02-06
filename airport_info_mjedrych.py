import argparse
import sys
import numpy as np
import pandas as pd
import glob
import re
import os
from math import sin, cos, sqrt, atan2, radians

# MD: lepsza struktura, ale ta funkcjonalność była i tak krótka...
# MD: za to działa argparse - to dobrze
# MD: momentami problemy ze składnią pythona

def load_data(data_dir='.', detailed_data_folder =  r'simple_avia_par'):  # po co 'r'?
    dataCodes = (os.path.join(data_dir,'airport-codes.csv'))
    dataCountryCds = (os.path.join(data_dir,'country_codes.txt'))
    airports = pd.read_csv(dataCodes)
    ctry = pd.read_csv(dataCountryCds, sep=';')

    path = (os.path.join(data_dir, detailed_data_folder))
    allFiles = glob.glob(path + "/*.tsv")

    list_ = []

    for file_ in allFiles:
        df = pd.read_csv(file_, sep='\t')
        df['year'] = (int(re.findall("[.0-9][.0-9][.0-9][.0-9]", file_)[0]))  # MD: 1) po co "."? Da się prościej...
        list_.append(df)

    frame = pd.concat(list_, axis=0, ignore_index=True)

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
    frame = frame.drop(columns=['code_dep', "code_arr"])  # deleted 'seats' from list

    return airports, ctry, frame

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
    # MD: tutaj lepszy byłby f-string, albo formatowanie przez key-value - bo tak łatwo się pogubić    
    info_details = ("""Route information ({11}):\n\
     Origin: {0} ({1}) airport in {2} ({3}),\n\
     Destination: {4} {5} airport in {6} ({7})\n\
     Distance: {8} km,\n\
     Passangers: {9},\n\
     Avaiable seats: {10}""").format(name_origin, origin, country_origin, country_origin_aberr,
                                     name_destination, destination, country_destination, country_destination_aberr,
                                     distance, traffic, seats, year)
    return info_details


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get info about selected track.')
    parser.add_argument('year', help='The year', type = int)
    parser.add_argument('airport_origin', help='Origin airport.', type = str)
    parser.add_argument('airport_destination', help='Destination airport.', type = str)
    args = parser.parse_args()

    # MD: nieeee! w ten sposób wczytujemy dane 3 razy! trzeba tak:
    # MD: airports, countries, airport_details = load_data()
    airports = load_data()[0]
    countries = load_data()[1]
    airports_details = load_data()[2]    
    info = print_route(airports, countries, airports_details, args.year, args.airport_origin, args.airport_destination)
    print(info)
