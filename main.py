import requests
from bs4 import BeautifulSoup
import datetime
import pandas as pd
from regression import MyLinearRegression
from geoenrichment import Geoenrichment
import geopandas as gpd
# -*- coding: utf-8 -*-

class OtodomParser:
    def __init__(self, address_string, last_page_number, slownik_warstw, ogloszenia_robocze, ogloszenia_all,
                 ogloszenia_nowe, folder):
        self.regression = MyLinearRegression()
        self.geoenrichment = Geoenrichment()
        self.ogloszenia_robocze = ogloszenia_robocze
        self.ogloszenia_all = ogloszenia_all
        self.ogloszenia_nowe = ogloszenia_nowe
        self.actual_page = 1
        self.last_page_number = last_page_number
        self.lista_linkow = []
        self.l_powt = 5
        self.df = ""
        self.df_cleaned = ""
        self.slownik_warstw = slownik_warstw
        self.folder = folder
        self.colnames = ['opis', 'dzielnica', 'pokoje', 'cena', 'metraz', 'cena_za_metr', 'link', 'data']
        if type(address_string) is not str:
            raise Exception("Address string can't be empty or not str type.")
        self.address_string = '{0}&page={1}'.format(address_string, "{}")

    @staticmethod
    def remove_blank_strings(l):
        return [e for e in l if e and str(e).strip()]

    @staticmethod
    def remove_unnecessary_elements(_offer):
        result = []
        for el in _offer:
            new_el = el.strip()
            if el.startswith('Mieszkanie na sprzedaż: Kraków'):
                new_el = el.replace('Kraków', '')
            result.append(new_el)
        return result

    @staticmethod
    def prepare_list_from_offer(_offer):
        return list(_offer.children)[3].text.split('\n')

    @staticmethod
    def data_cleaning(df, numeric_columns):
        df[numeric_columns] = df[numeric_columns].replace(['>', ' ', '/',
                                                           'pokoje', 'pokój', 'pokoi', 'zł', 'm²'], '', regex=True)
        df[numeric_columns] = df[numeric_columns].replace([','], '.', regex=True)
        df = df.drop_duplicates(['opis'], keep='first')
        for pole in numeric_columns:
            df = df[pd.to_numeric(df[pole], errors='coerce').notnull()]
        df[numeric_columns] = df[numeric_columns].astype(float)
        return df

    def parse(self):
        self.liczba_ogloszen = 0
        self.licznik = 0
        self.licznik_powtorzen = 0
        lista_linkow_nowa = []
        licznik_kryt = 0

        result_list = []
        r = requests.get(self.address_string.format(self.actual_page))

        while self.actual_page <= self.last_page_number:
            soup = BeautifulSoup(r.content, 'html.parser')
            offers = soup.find_all('article')

            for offer in offers:
                self.liczba_ogloszen += 1
                offer_as_list = self.prepare_list_from_offer(offer)
                offer_as_list = self.remove_blank_strings(offer_as_list)
                offer_as_list = self.remove_unnecessary_elements(offer_as_list)
                offer_as_list.append(offer.find('a').attrs['href'])
                offer_as_list.append(str(datetime.datetime.now()))
                try:
                    link = offer_as_list[7]
                except:
                    pass
                if link in lista_linkow_nowa:
                    licznik_kryt += 1
                    if licznik_kryt > self.l_powt:
                        print("mamy {} raz to samo ogloszenie, teraz zapiszemy i przerywamy dzialanie skryptu".
                              format(self.l_powt))
                        with open(self.ogloszenia_robocze, 'a', encoding='utf-8') as file:
                            for el in result_list:
                                file.write("{}\n".format(el))
                                self.licznik += 1
                        return

                if link not in self.lista_linkow:
                    if link not in lista_linkow_nowa:
                        result_list.append(';'.join(offer_as_list[1:]))
                        lista_linkow_nowa.append(link)
                else:
                    self.licznik_powtorzen += 1

            self.actual_page += 1
            r = requests.get(self.address_string.format(self.actual_page))

        with open(self.ogloszenia_robocze, 'a', encoding='utf-8') as file:
            for el in result_list:
                el = el.replace("Mieszkanie na sprzedaż:", "Kraków")
                file.write("{}\n".format(el))
                self.licznik += 1

        print("sprawdzono", self.liczba_ogloszen, "ofert,  dodano", self.licznik, "nowych rekordow, znaleziono",
              self.licznik_powtorzen, "powtorzonych ogloszen")

    def spacjalizuj(self):
        self.df = pd.read_csv(self.ogloszenia_robocze, sep=";", names=self.colnames, header=None, error_bad_lines=False)
        # najpierw polaczyc a pozniej geokodowac - join po opisie i skasowac tam, gdzie sie zgadzaja
        print("przed czyszczeniem mamy {} rekordów".format(self.df.shape[0]))
        self.df_cleaned = self.data_cleaning(self.df, numeric_columns=['cena_za_metr', 'metraz', 'cena'])
        print("przed gekodowaniem mamy {} rekordów".format(self.df_cleaned.shape[0]))

        gdf_geo_nowe = self.geoenrichment.make_spatial(self.df_cleaned)
        gdf_geo_nowe.to_csv(self.ogloszenia_nowe, sep=";")
        stare_gdf = pd.read_csv(self.ogloszenia_all, sep=";", error_bad_lines=False)

        # scalenie, usuniecie zbednych kolumn oraz duplikatow wierszy
        df_concat = pd.concat([stare_gdf, gdf_geo_nowe], ignore_index=True)
        df_concat = df_concat.drop_duplicates(['opis'], keep='first')
        df_concat = df_concat.loc[:, ~df_concat.columns.str.contains('^unnamed', case=False)]

        # wczytuje df, robi GDF i dopsiuje wartosci zmiennych z mapy
        gdf = self.geoenrichment.make_gdf(df_concat)
        gdf_enriched = self.geoenrichment.geoenrich(gdf, self.slownik_warstw, self.folder)
        gdf_enriched.to_csv(self.ogloszenia_all, sep=";")

    def analizuj_df(self):
        self.gdf_polaczony = pd.read_csv(self.ogloszenia_all, sep=";", error_bad_lines=False)
        self.regression.draw_history(self.gdf_polaczony, self.folder)

        # wywalamy outliers
        # self.gdf_polaczony = self.gdf_polaczony.loc[self.gdf_polaczony['cena_za_metr'] < 17500]

        # analiza statystyczna
        lista_zmiennych = ['dst_center', 'metraz']
        for k, v in self.slownik_warstw.items():
            lista_zmiennych.append(k)
        self.regression.corr_matrix(self.gdf_polaczony, lista_zmiennych, self.folder)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'linreg', cv=15)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'ridge', cv=15)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'svm')
        # self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'elastic_CV', cv=15)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'lasso_CV', cv=15)

        # dodadc do powyzszcyh metod sklearn.model_selection.GridSearchCV
        # koniecznie plotowac ceny predicted vs real!

