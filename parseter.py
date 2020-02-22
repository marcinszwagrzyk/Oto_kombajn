import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import numpy as np


# -*- coding: utf-8 -*-
class Parseter:
    def __init__(self, address_string, last_page_number, ogloszenia_robocze, ogloszenia_all,
                 ogloszenia_nowe, folder):
        self.ogloszenia_robocze = ogloszenia_robocze
        self.ogloszenia_all = ogloszenia_all
        self.ogloszenia_nowe = ogloszenia_nowe
        self.actual_page = 1
        self.last_page_number = last_page_number
        self.lista_linkow = []
        self.l_powt = 50
        self.folder = folder
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

    # wchodzimy do ogloszenia i dodajemy wiecej zmiennych
    def parse_wglab(self, url):
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        lista_slow = ['Rok budowy: ', 'Piętro: ', 'Liczba pięter: ']
        lista_slow2 = ['<li>', '</strong>', '<strong>', '</li>', '&gt;']
        lista_slow3 = lista_slow + lista_slow2

        vals = soup.find_all("li")
        lista_val = []
        licznik =0
        for val in vals:
            val_str = str(val)
            try:
                for slowo in lista_slow:
                    if slowo in val_str:
                        licznik =+1
                        if licznik > 2:
                            lista_val = [np.nan, np.nan, np.nan]
                            return lista_val
                            break
                        for slowo_zbedne in lista_slow3:
                            val_str = val_str.replace(slowo_zbedne, "")
                            if val_str == 'parter':
                                val_str = '0'
                        lista_val.append(val_str)
            except:
                lista_val = ["", "", ""]
                return lista_val

        if len(lista_val) !=3:
            lista_val = ["", "", ""]
            return lista_val
        return lista_val

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
                link = offer.find('a').attrs['href']
                offer_as_list.append(link)
                lista_dod = self.parse_wglab(link)
                offer_as_list.append(str(datetime.datetime.now()))
                offer_as_list.append(lista_dod[0])
                offer_as_list.append(lista_dod[1])
                offer_as_list.append(lista_dod[2])

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
                        result_list.append(';'.join(offer_as_list))
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
