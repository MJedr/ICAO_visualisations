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


# wczytywanie danych
dataCodes = 'airport-codes.csv'
dataCountryCds = 'country_codes.txt'
airports = pd.read_csv(dataCodes)
ctry = pd.read_csv(dataCountryCds, sep=';')

# wczytywanie danych z katalogu
path = r'simple_avia_par'  # po co r?
allFiles = glob.glob(path + "/*.tsv")

list_ = []

for file_ in allFiles:
    df = pd.read_csv(file_, sep='\t')
    df['year'] = (int(re.findall("[.0-9][.0-9][.0-9][.0-9]", file_)[0]))  # MD: po co "."? Można prościej!
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


def plot_country(county_code,
                 option={'airport', 'traffic'},  # MD: 1) co to miałoby osiągnąć? 2) nie używamy mutowalnych obiektów jako domyślnych argumentów: https://docs.python-guide.org/writing/gotchas/
                 plot_name='traffic_plot.png'):
    if option == 'airport':
        # MD: tego typu komentarze można starać się zastąpić odpowidnio nazwanymi zmiennymi np. arrivals_df itp.
        # MD: więcej o pisaniu dobrych komentarzy np:
        # MD: https://medium.freecodecamp.org/code-comments-the-good-the-bad-and-the-ugly-be9cc65fbf83
        # MD: https://blog.codinghorror.com/code-tells-you-how-comments-tell-you-why/
        # pomocnicza ramka dancyh z lotniskami w wybranym kraju - przyloty
        f1 = frame[(frame.iso_code_dep == county_code) & (frame.iso_code_arr == county_code)][
            ['passengers', 'airport_arr', 'year']]
        # pomocnicza ramka dancyh z lotniskami w wybranym kraju - odloty
        f2 = frame[(frame.iso_code_dep == county_code) & (frame.iso_code_arr == county_code)][
            ['passengers', 'airport_dep', 'year']]
        # zmiana nazwy kolumny - zapobieganie duplikowaniu kolumny
        f2 = f2.rename(columns={'passengers': 'pessangers_dep'})

        # połączenie obydwu ramek danych na podstawie lotniska i roku
        new_df = pd.merge(f1, f2, how='left', left_on=['airport_arr', 'year'], right_on=['airport_dep', 'year'])
        # pogrupowanie lotnisk w unikalne pary
        df = new_df.groupby(['airport_dep', 'airport_arr', 'year'])[['pessangers_dep', 'passengers']].sum()
        # zsumowanie liczby pasażerów
        df['pessangers_sum'] = df.apply(lambda row: row.pessangers_dep + row.passengers, axis=1)  # MD: bez lambda, po prostu sumujemy wektorowo
        df = df.dropna(axis=1)
        df = df.reset_index()

        # przekształcenie ramki danych, żeby każda unikalna para była osobą kolumną
        # wypełnienie brakujących danych wartościami ostatniej dostępnej wartości
        df = df.groupby(['airport_dep', 'airport_arr', 'year']).sum().unstack(['airport_dep', 'airport_arr']).fillna(
            method='ffill').reset_index()
        # wybór ostatniego roku
        df = pd.DataFrame(df[df.year == 2015].pessangers_sum.unstack())  # MD: 2015 wpisane na sztywno do kodu
        df = df.reset_index()
        # odrzucenie zbędnych kolumn, zmiana nazw kolumn
        df = df.drop(columns=['level_2', 'airport_arr'])
        df = df.rename(columns={0: 'sum',
                                'airport_dep': 'airport_code'})
        # sortowanie malejąco
        df = df.sort_values(by=['sum'], ascending=False)

        # wizualizacja
        # MD: coś mi się te obliczenia nie zgtadzają, ale zależy jeszcze jak się traktuje NaN
        ax = sns.barplot(data=df, x="airport_code", y="sum").set_title("Airports for {}".format(county_code))
        plt.xlabel("Airport ICAO code")
        plt.ylabel("Passangers [thousands]")
        plt.savefig(plot_name)
        plt.show()

    elif option == 'traffic':
        # wybór danych
        f = frame[(frame.iso_code_dep == county_code)][['passengers', 'airport_dep', 'year']]
        # tabela przestawna z danymi dla każdego roku i każdego lotniska w wybranym kraju
        f = pd.pivot_table(f, index=['airport_dep', 'year'], values='passengers',
                           aggfunc=np.sum)
        f = f.reset_index()

        # wizualizacja
        ax = sns.lineplot(data=f, x='year', hue='airport_dep', y='passengers')
        ax.get_legend().texts[0].set_text('Airport')

    plt.savefig(plot_name)
    plt.show()


def plot_airport(airport_name, options={'partners', 'capacity', 'distance'}, plot_name='plot_airport.png'):
    """
    Umożliwia wizualizację danych dotyczących wybranego lotniska
    :param airport_name: Skrót lotniska (wg. ICAO)
    :param options: typ wykresu - 'partners' - 10 największych partnerów, 'capacity' - korelacja między ilością wolnych miejsc
    a liczbą pasażerów, 'distance' - zależność między odległością a liczbą pasażerów
    :param plot_name: nazwa pliku wyjściowego dla wykresu
    :return:
    """
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
        traffic = traffic.sort_values(by=['passengers_sum'], ascending=False)
        # wybór największych partnerów
        traffic_top10 = traffic.head(10)

        # wizualizacja
        ax = sns.barplot(data=traffic_top10, x="airport_arr", y="passengers_sum").set_title(
            "Largest partners of {}".format(airport_name))
        plt.xlabel("Destination airport")
        plt.ylabel("Passangers [thousands]")
        plt.savefig(plot_name)
        plt.show()

    elif options == 'capacity':
        # wybór lotniska
        selection = frame[(frame.airport_dep == airport_name)]
        # usunięcie obserwacji z brakiem danych
        selection = selection.loc[(selection['seats'] != ":")]   # MD: można by to załatwić na etapie read_csv (na_values=':')
        # sprawdzenie ostatniego dostępnego roku
        last_year = max(selection.year)
        # zmiana typu kolumny
        selection.seats = selection.seats.astype("float16")
        # wybór danych dla ostatniego dostępnego roku
        selection = selection[(selection.year == last_year)]

        # wizualizacja
        ax = sns.regplot(data=selection, y='passengers', x='seats')
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
    # pobór nazwy lotniska wylotu
    name_country_origin = airports[airports.ident == origin][['name', 'iso_country']]
    name_origin = airports.at[name_country_origin.index[0], "name"]
    # pobór nazwy państwa wylotu
    country_origin_aberr = airports.at[name_country_origin.index[0], 'iso_country']
    country_origin = ctry[ctry.iso_country == country_origin_aberr]['country'].values[0]
    country_origin = country_origin[0] + country_origin[1:].lower()

    # pobór nazwy lotniska docelowego
    name_country_destination = airports[airports.ident == destination][['name', 'iso_country']]
    name_destination = airports.at[name_country_destination.index[0], "name"]
    # pobór nazwy państwa docelowego
    country_destination_aberr = airports.at[name_country_destination.index[0], 'iso_country']
    country_destination = ctry[ctry.iso_country == country_destination_aberr]['country'].values[0]
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
