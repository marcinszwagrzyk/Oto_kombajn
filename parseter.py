import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime


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
