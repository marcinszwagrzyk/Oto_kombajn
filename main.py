import pandas as pd
import os
from regression import MyLinearRegression
# from deep_learning import MyNeuralNetwork
from geoenrichment import Geoenrichment
# -*- coding: utf-8 -*-

class Otodomer:
    def __init__(self, slownik_warstw, ogloszenia_robocze, ogloszenia_nowe, ogloszenia_all, folder):
        self.regression = MyLinearRegression(folder)
        # self.nn = MyNeuralNetwork()
        self.geoenrichment = Geoenrichment()
        self.df = ""
        self.df_cleaned = ""
        self.slownik_warstw = slownik_warstw
        self.ogloszenia_robocze = ogloszenia_robocze
        self.ogloszenia_nowe = ogloszenia_nowe
        self.ogloszenia_all = ogloszenia_all
        self.folder = folder
        self.colnames = ['opis', 'dzielnica', 'pokoje', 'cena', 'metraz', 'cena_za_metr', 'link', 'data']


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
        lista_zmiennych = ['dst_center', 'metraz', 'latitude', 'longitude']
        lista_zmiennych_txt = ['dst_center', 'metraz', 'latitude', 'longitude', 'opis']
        #  lista_zmiennych = ['dst_center', 'metraz']

        for k, v in self.slownik_warstw.items():
            lista_zmiennych.append(k)

        self.gdf_polaczony = self.gdf_polaczony.loc[self.gdf_polaczony['cena_za_metr'] < 16000]
        #self.regression.corr_matrix(self.gdf_polaczony, lista_zmiennych, self.folder)

        self.regression.pairplot(self.gdf_polaczony, lista_zmiennych, self.folder)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'linreg', cv=15)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'ridge', cv=15)
        self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'svm', self.folder)
        df_pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'lasso_CV',  cv=15)
        df_pred.to_csv(os.path.join(self.folder, "prediction.csv"))

        # self.regression.fit_nlp(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'opis')
        # neural network - kompletnie fatalne wyniki !
        # self.nn.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony)


