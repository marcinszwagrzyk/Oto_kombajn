import pandas as pd
import os
from regression import MyLinearRegression
# from deep_learning import MyNeuralNetwork
from geoenrichment import Geoenrichment
# -*- coding: utf-8 -*-

class Otodomer:
    def __init__(self, slownik_warstw, ogloszenia_robocze, ogloszenia_nowe, ogloszenia_all, holdout, folder):
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
        self.holdout = holdout
        self.holdout_cleaned = ""
        self.holdout_spatial = r'c:\Users\marci\git\Oto_klasor\holdout\mwm_spatial.csv'
        self.colnames = ['opis', 'dzielnica', 'pokoje', 'cena', 'metraz', 'cena_za_metr', 'link', 'data', 'pietro',
                         'l_pieter',
                         'rok_bud']

        self.lista_holdout_pred =[]

    @staticmethod
    def data_cleaning(df, numeric_columns):
        df[numeric_columns] = df[numeric_columns].replace(['>', ' ', '/',
                                                           'pokoje', 'pokój', 'pokoi', 'zł', 'm²'], '', regex=True)
        df[numeric_columns] = df[numeric_columns].replace([','], '.', regex=True)
        df = df.drop_duplicates(subset = ['opis', 'metraz'], keep='first')
        for pole in numeric_columns:
            df = df[pd.to_numeric(df[pole], errors='coerce').notnull()]
        df[numeric_columns] = df[numeric_columns].astype(float)
        return df

    def spacjalizuj(self):
        self.df = pd.read_csv(self.ogloszenia_robocze, sep=";", names=self.colnames, header=None, error_bad_lines=False)
        # najpierw polaczyc a pozniej geokodowac - join po opisie i skasowac tam, gdzie sie zgadzaja
        print("przed czyszczeniem mamy {} rekordów".format(self.df.shape[0]))
        self.df_cleaned = self.data_cleaning(self.df, numeric_columns=['cena_za_metr', 'metraz', 'cena', 'pietro',
                                                                       'l_pieter', 'rok_bud'])

        print(self.df_cleaned.columns)
        print("przed gekodowaniem mamy {} rekordów".format(self.df_cleaned.shape[0]))

        gdf_geo_nowe = self.geoenrichment.make_spatial(self.df_cleaned)
        print(gdf_geo_nowe.head())
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

    def spacjalizauj_holdout(self):
        self.holdout = pd.read_csv(self.holdout, sep=";", header=0, error_bad_lines=False)
        print(self.holdout.head())
        self.holdout_cleaned = self.data_cleaning(self.holdout, numeric_columns=['cena_za_metr', 'metraz', 'cena'])
        holdout_nowe = self.geoenrichment.make_spatial(self.holdout_cleaned)
        holdout_nowe_enriched = self.geoenrichment.geoenrich(holdout_nowe, self.slownik_warstw, self.folder)
        holdout_nowe_enriched.to_csv(self.holdout_spatial, sep=";")

    def analizuj_df(self):
        self.gdf_polaczony = pd.read_csv(self.ogloszenia_all, sep=";", error_bad_lines=False)
        self.regression.draw_history(self.gdf_polaczony, self.folder)
        self.gdf_holdout = pd.read_csv(self.holdout_spatial, sep=";", error_bad_lines=False)

        # analiza statystyczna
        lista_zmiennych = ['dst_center', 'metraz', 'rok_bud', 'pietro', 'l_pieter']
        for k, v in self.slownik_warstw.items():
            lista_zmiennych.append(k)

        # wywalamy outliers
        self.gdf_polaczony = self.gdf_polaczony.loc[self.gdf_polaczony['cena_za_metr'] < 16000]
        # self.regression.corr_matrix(self.gdf_polaczony, lista_zmiennych, self.folder)

        # pairplot
        self.regression.pairplot(self.gdf_polaczony, lista_zmiennych, self.folder, "variables")

        # regresje - to na pewno zapakowac do petli - i od razu liczyc holdout
        pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'linreg', cv=15)
        pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'ridge', cv=15)
        pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony,  'svm', self.folder)
        pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony, 'random_forest', self.folder)
        pred = self.regression.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony,  'lasso_CV', cv=15)

        # predict holdout za pomoca regresji
        self.model = pred[0]
        self.lista_holdout_pred.append(self.regression.predict(self.model, lista_zmiennych, self.gdf_holdout, 'lasso_CV'))

        # neural network - kompletnie fatalne wyniki !
        # score_nn = self.nn.fit_model(lista_zmiennych, 'cena_za_metr', self.gdf_polaczony)
        # print("score nn wynosi: ", score_nn)

        # NLP
        lista_zmiennych='opis'
        pred = self.regression.fit_nlp(lista_zmiennych, 'cena_za_metr',  self.gdf_polaczony)

        # predict holdout za pomoca nlp
        self.model = pred[0]
        self.lista_holdout_pred.append(self.regression.predict(self.model, lista_zmiennych, self.gdf_holdout, 'nlp'))
        df_holdout_pred = pd.concat(self.lista_holdout_pred, axis=1)
        df_holdout_pred = df_holdout_pred.loc[:, ~df_holdout_pred.columns.duplicated()]
        df_holdout_pred.to_csv(os.path.join(self.folder, "holdout_prediction.csv"))

        # # podsumewanie regresji
        df_pred = pred[1]
        df_pred['mean_regres'] = df_pred[['linreg', 'ridge', 'lasso_CV']].mean(axis=1)
        df_pred['mean_predict'] = df_pred[['mean_regres', 'nlp', 'svm', 'random_forest']].mean(axis=1)
        df_pred.to_csv(os.path.join(self.folder, "prediction.csv"))
        cols = ['cena_za_metr', 'mean_regres', 'nlp', 'mean_predict', 'random_forest']
        self.regression.pairplot(df_pred, cols, self.folder, "prediction")

        linreg_corel  = dokladnosc_all = df_pred['cena_za_metr'].corr(df_pred['linreg'])
        dokladnosc_all = df_pred['cena_za_metr'].corr(df_pred['mean_predict'])
        print("corr sredniej oszacowania ceny z real wynosi ",  dokladnosc_all, "corr linreg - cena wynosi", linreg_corel)



