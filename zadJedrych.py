import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import re
import os
from math import sin, cos, sqrt, atan2, radians


# MD: ok, wpliku airport_info jest lepsza struktura, a tutaj jest więcej funkcji.
# MD: kod działa i jest ok w skali "mikro", ale struktura średnia - długie funkcje robiące kilka rzeczy na raz


def load_data(data_dir='.', detailed_data_folder='simple_avia_par'):
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

    # czyszczenie danych - podział na osobne kolumny
    # kolumna airport - departure
    frame['airport_dep'] = frame.code_dep.str.split('_').str.get(1)

    # kolumna z kodem iso dla lotniska odlotu
    frame['iso_code_dep'] = frame.code_dep.str.split('_').str.get(0)

    # kolumna airport_arr
    frame['airport_arr'] = frame.code_arr.str.split('_').str.get(1)

    # kolumna z kodem iso dla lotniska docelowego
    frame['iso_code_arr'] = frame.code_arr.str.split('_').str.get(0)

    # wyrzucenie zbędnych kolumn
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


def plot_country_airport(county_code, option, plot_name='traffic_plot.png'):
    airports, country, frame = load_data()

    arrivals = frame[frame.iso_code_arr == county_code].groupby(['year', 'airport_arr']).sum().unstack()
    departures = frame[frame.iso_code_dep == county_code].groupby(['year', 'airport_dep']).sum().unstack()

    last_year_arrivals = arrivals.apply(lambda x: x[x.notnull()].values[-1]).rename("arrivals")
    last_year_departures = departures.apply(lambda x: x[x.notnull()].values[-1]).rename("departures")

    last_year_traffic = pd.concat([last_year_arrivals, last_year_departures], axis=1, join='inner')

    last_year_traffic["sum"] = last_year_traffic.sum(axis=1)
    last_year_traffic.index = last_year_traffic.index.set_names(['variable', 'airport_code'])
    last_year_traffic = last_year_traffic.reset_index().sort_values(by=['sum'], ascending=False)

    # wizualizacja
    ax = sns.barplot(data=last_year_traffic, x="airport_code", y="sum").set_title("Airports for {}".format(county_code))
    plt.xlabel("Airport ICAO code")
    plt.ylabel("Passangers [thousands]")
    plt.savefig(plot_name)
    plt.show()


def plot_country_traffic(county_code, plot_name='traffic_plot.png'):
    airports, country, frame = load_data()

    selected_data = frame[(frame.iso_code_dep == county_code)][['passengers', 'airport_dep', 'year']]
    selected_data_pivot = pd.pivot_table(selected_data, index=['airport_dep', 'year'], values='passengers',
                       aggfunc=np.sum)
    selected_data_pivot = selected_data_pivot.reset_index()

    # wizualizacja
    ax = sns.lineplot(data=selected_data_pivot, x='year', hue='airport_dep', y='passengers')
    ax.get_legend().texts[0].set_text('Airport')

    plt.savefig(plot_name)
    plt.show()


def plot_airport(airport_name, options, plot_name='plot_airport.png'):
    """
    Umożliwia wizualizację danych dotyczących wybranego lotniska
    :param airport_name: Skrót lotniska (wg. ICAO)
    :param options: typ wykresu - 'partners' - 10 największych partnerów, 'capacity' - korelacja między ilością wolnych miejsc
    a liczbą pasażerów, 'distance' - zależność między odległością a liczbą pasażerów
    :param plot_name: nazwa pliku wyjściowego dla wykresu
    :return:
    """
    airports, country, frame = load_data()
    if options == 'partners':
        # ramka z odlotami z lotniska
        departures =frame[(frame.airport_dep == airport_name) & (frame.year == 2015)][['airport_arr', 'passengers']]
        departures = departures.rename(columns={'passengers': 'passengers_from'})
        # ramka z przylotami do lotniska
        arrivals = frame[(frame.airport_arr == airport_name)&(frame.year == 2015)][['airport_dep', 'passengers']]
        arrivals = arrivals.rename(columns={'passengers': 'passengers_to'})

        # połączenie ramek odlotów i przylotów
        traffic = arrivals.merge(departures, left_on='airport_dep', right_on='airport_arr', how='outer')
        traffic = traffic.fillna(value=0)
        # policzenie sumy pasażerów przylatujących i odlatujących dla każdego lotniska
        traffic['passengers_sum'] = traffic.apply(lambda row: row.passengers_to + row.passengers_from, axis=1)
        # posortowanie ramki danych malejąco
        traffic_sorted = traffic.sort_values(by=['passengers_sum'], ascending=False)
        # wybór największych partnerów
        traffic_top10 = traffic_sorted.head(10)

        # wizualizacja
        # TODO: sprawdzić czy ax się w ogóle kiedyś wyświetla
        ax = sns.barplot(data=traffic_top10, x="airport_arr", y="passengers_sum").set_title(
            "Largest partners of {}".format(airport_name))
        plt.xlabel("Destination airport")
        plt.ylabel("Passangers [thousands]")
        plt.savefig(plot_name)
        plt.show()

    elif options == 'capacity':
        # wybór lotniska
        selected_data = frame[(frame.airport_dep == airport_name)]
        # sprawdzenie ostatniego dostępnego roku
        last_year = max(selected_data.year)
        # zmiana typu kolumny
        selected_data.seats = selected_data.seats.astype("float16")
        # wybór danych dla ostatniego dostępnego roku
        selected_data_year = selected_data[(selected_data.year == last_year)]

        # wizualizacja
        ax = sns.regplot(data=selected_data_year, y='passengers', x='seats')
        ax.set_title("Passangers vs. capacity for {}".format(airport_name))
        ax.set_xlabel("Passangers [thousands]")
        ax.set_ylabel("Avaiable seats [thousands]")
        plt.savefig(plot_name)
        plt.show()

    elif options == 'distance':
        # wybór lotniska
        departures = frame[(frame.airport_dep == airport_name)]
        # wybór danych dla ostatniego dostępnego roku
        departures = departures[departures.year == max(departures.year)][['airport_arr', 'passengers']]
        # pobranie współrzędnych wszystkich lotnisk
        airports_coords = airports[['ident', 'latitude_deg', 'longitude_deg']]

        # pobranie współrzędnych lotniska
        coordsChosen = airports[airports.ident == airport_name][['latitude_deg', 'longitude_deg']]
        # zapis współrzędnej x i y lotniska
        y = coordsChosen.iloc[0]['latitude_deg']
        x = coordsChosen.iloc[0]['longitude_deg']

        # połączenie ramki z lotniskami i współrzędnymi
        departures = departures.merge(airports_coords, left_on='airport_arr', right_on='ident')
        # obliczenie odległości do lotnisk
        departures['distance'] = departures.apply(
            lambda row: calculate_distance(y, x, row.latitude_deg, row.longitude_deg), axis=1)
        # posortowanie odległości malejąco
        departures = departures.sort_values(by=['distance'])

        # wizualizacja
        ax = sns.regplot(data=departures, y='passengers', x='distance')
        ax.set_title("Passangers vs. distance for {}".format(airport_name))
        ax.set(xscale="log", yscale="log")
        ax.set_xlabel("Distance [km] log10")
        ax.set_ylabel("Passangers [thousands] log10")
        plt.savefig(plot_name)
        plt.show()


def print_route(year, origin, destination):
    airports, country, frame = load_data()
    # pobór nazwy lotniska wylotu
    name_country_origin = airports[airports.ident == origin][['name', 'iso_country']]
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
    traffic_seats = frame[(frame.year == year) & (frame.airport_dep == origin) & (frame.airport_arr == destination)][
        ['passengers', 'seats']]
    # jeżeli nie ma połączenia - zatrzymaj program
    try:
        traffic = traffic_seats.values[0][0]
    except IndexError:
        print('No connection found')
        sys.exit(1)  # MD: to nienajlepsze miejsce do wyjścia z programu, ale ok.
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
