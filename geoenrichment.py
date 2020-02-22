import geopandas as gpd
from difflib import SequenceMatcher
from geopy.geocoders import Nominatim
import pandas as pd
pd.set_option('mode.chained_assignment', None)
import matplotlib.pyplot as plt
from geopy.extra.rate_limiter import RateLimiter
import os


class Geoenrichment:
    def __init__(self) -> object:
        self.locator = Nominatim(user_agent='nlp2')
        self.geocode = RateLimiter(self.locator.geocode, min_delay_seconds=1)

    def __repr__(self):
        return "Class for geospatial stuff"

    def make_gdf(self, datafame):
        # DataFrame with x,y to GeoDataFrame
        gdf = gpd.GeoDataFrame(datafame, geometry=gpd.points_from_xy(x=datafame.longitude, y=datafame.latitude),
                               crs={'init': 'epsg:4326'})
        # reprojekcja do Panstwowego Ukladu Wspolrzednych Geodezyjnych PUWG1992
        gdf = gdf.to_crs({'init': 'epsg:2180'})
        return gdf

    def rob_liste_ulic(self, dataframe):
        # pobranie listy ulic z warstwy OpenStreetMap dla Krakowa
        streets = gpd.read_file(r'shp\drogi_krk_osm_dis.shp')
        self.lista_nazw = []
        for i in streets.itertuples():
            # dodac zakres x y ulicy
            # pobranie bounding box i pozniej losowanie w ramach tego bounding box
            ulica = i.name
            ulica_list = ulica.split(" ")
            self.lista_nazw.append(ulica_list[-1])

        # stworzenie listy dzielnic
        self.lista_dzielnic = []
        self.lista_dzielnic = ['Justowska', 'Ruczaj', 'Bronowice', 'Osiedle', "Kraków", "Krakowa", "Nowe", "Nowa",
                               "Nowy", "Krakowska", "Krakusów", "budowie", "parkingu", "piękna", "Kraka", "Piękna",
                               "Zielona", "Kazimierz", "Prądnika"]

    def szukaj_ulicy(self, cell):
        opis_list = cell.split(" ")
        for slowo in opis_list:
            if len(slowo) > 4:
                for ulica in self.lista_nazw:
                    ulica = ulica.replace('"',"")
                    ratio = SequenceMatcher(None, slowo, ulica).ratio()
                    if ratio > 0.8:
                      if ulica not in self.lista_dzielnic:
                        print("ulica ", ulica)
                        return ulica

    def geokoduj(self, dataframe, pole):
        dataframe['geo_location'] = dataframe[pole].apply(self.geocode)
        located = dataframe.loc[dataframe["geo_location"].notnull()]
        not_located = dataframe.loc[dataframe["geo_location"].isnull()]
        return (located, not_located)

    def plot_offers(self, geodataframe, field, folder):
        # plot geocoded offers
        rds = gpd.read_file(r'shp\osm_rds_92.shp')
        liczba = geodataframe.shape[0]
        plt.rcParams['figure.figsize'] = (25, 18)
        plt.rcParams['font.family'] = 'sans-serif'

        krk_border = gpd.read_file(r'shp\krk_border.shp')
        ax = krk_border.plot(color='lightgray', edgecolor='black')
        ax.set_title("{} of housing offers, no of offers: {}".format(field, liczba))
        ax.legend()
        rds.plot(ax=ax, color='black', linewidth=0.1);
        geodataframe.plot(ax=ax, marker='o', column=field, cmap='Reds', markersize=5);
        # colorbar will be created by ...
        fig = ax.get_figure()
        cbax = fig.add_axes([0.95, 0.3, 0.03, 0.39])
        colormap = "Reds"  # add _r to reverse the colormap
        vmin_gdf = geodataframe[field].min()
        vmax_gdf = geodataframe[field].max()
        sm = plt.cm.ScalarMappable(cmap=colormap, \
                                   norm=plt.Normalize(vmin=vmin_gdf,
                                                      vmax=vmax_gdf))
        sm._A = []
        fig.colorbar(sm, cax=cbax, format="%d")
        plt.savefig(os.path.join(folder, field + "_map.jpg"), dpi=400, bbox_inches='tight')

    def haversine(self, row):
        """
              calculates distance to city center
              """
        import math
        lon1 = row['longitude']
        lat1 = row['latitude']

        # coords of the city center
        lon2 = 19.938
        lat2 = 50.061

        R = 6371000  # radius of Earth in meters
        phi_1 = math.radians(lat1)
        phi_2 = math.radians(lat2)

        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0) ** 2

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        meters = R * c  # output distance in meters
        meters = round(meters)
        return (meters)

    def dist_layer(self, geodataframe, warstwa_path, field):
        gdf_warstwa = gpd.read_file(warstwa_path)

        def min_distance(point, gdf_warstwa):
            return gdf_warstwa.distance(point).min()

        geodataframe[field] = geodataframe.geometry.apply(min_distance,
                                                          args=(gdf_warstwa,))
        geodataframe = geodataframe.loc[geodataframe[field] < 30000] # usuniecie blednie zgeolokalizowanych
        return geodataframe

    def make_spatial(self, dataframe):
        geocode = RateLimiter(self.locator.geocode, min_delay_seconds=1)
        #  1 - prepare street names list
        self.rob_liste_ulic(dataframe)
        #  2 - add field with street name base on list
        dataframe['ulica'] = dataframe['opis'].apply(self.szukaj_ulicy)
        dataframe['lokator_ulica_dzielnica'] = dataframe['dzielnica'] + ", " + dataframe['ulica']
        #  3 - geocode base one street name
        geokoduj = self.geokoduj(dataframe.loc[dataframe["ulica"].notnull()], 'lokator_ulica_dzielnica')
        located = geokoduj[0]
        il_ogloszen = located.shape[0]
        print('we have {} geocoded offers out of all {}'.format(il_ogloszen, dataframe.shape[0]))
        if il_ogloszen == 0:
            return 0
        # 4 - create longitude, laatitude and altitude from location column (returns tuple)
        located['point'] = located['geo_location'].apply(lambda loc: tuple(loc.point) if loc else None)
        # 5 - split point column into latitude, longitude and altitude columns
        located[['latitude', 'longitude', 'altitude']] = pd.DataFrame(located['point'].tolist(), index=located.index)
        # 6 - make geodataframe base on lat lon
        gdf = self.make_gdf(located)

        # 7 - plot geocoded offers
        # self.plot_offers(gdf, 'cena_za_metr', folder)
        return gdf

    def geoenrich(self, gdf, slownik_warstw, folder):
        # 7 - oblicz odleglosc do centrum
        gdf['dst_center'] = gdf.apply(self.haversine, axis=1)
        gdf = gdf.loc[gdf['dst_center'] < 30000]

        # zaminieamy drozsze niz 15 000 na 15000, zeby nie bylo ich na mapie, zeby nie zaciemnialy
        seria = gdf['cena_za_metr']
        gdf['cena_za_metr2'] = [15000 if rekord > 15000 else rekord for rekord in seria]
        gdf['cena_za_metr2'] = [5000 if rekord < 5000 else rekord for rekord in seria]
        self.plot_offers(gdf, 'cena_za_metr2', folder)
        # dodac plotowanie heatmapy folium

        for k, v in slownik_warstw.items():
            gdf = self.dist_layer(gdf, v, k)
            self.plot_offers(gdf, k, folder)
        return gdf
