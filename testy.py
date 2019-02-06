from zadJedrych import print_route, plot_airport, plot_country_airport, plot_country_traffic

print(print_route(2015, 'LOWW', 'EPWA'))
p=plot_airport('EPWA', 'partners')
plot_airport('EPWA', 'capacity')
plot_airport('EPWA', 'distance')
plot_country_airport('PL', 'airport')
plot_country_traffic('PL', 'traffic')

