from main import OtodomParser
import os
from datetime import datetime

if __name__ == '__main__':
    url = 'https://www.otodom.pl/sprzedaz/mieszkanie/krakow/?search%5Bdescription%5D=1&search%5Bcreated_since%\
    5D=14&search%5Bsubregion_id%5D=410&search%5Bcity_id%5D=38'

    slownik_warstw = {'vist_dist': r'shp\osm_vistula_92.shp', 'trams_dist': r'shp\tram_stops.shp'}

    # TO DO LIST
    # wczytyac csv i robic gpd - i GEOENRICHMENT dla calosci jescze raz!!
    # sklejac caly raport w one slider

    # Opcje:
    #   1 - czytaj stary plik,
    #   2 - czytaj stary + dodaj nowe ogloszenia (dodac rysowanie i zapisywanie zmiany w czasie),
    #           zapisywac ryciny w folderze
    opcja = 2

    ogloszenia_all = r'c:\Users\marci\git\Oto_klasor\csv\gdf_stare.csv'
    now = datetime.now()
    data = now.strftime("%Y_%m_%d")
    folder = os.path.join(r'c:\Users\marci\git\Oto_klasor\Raporty', data)
    ogloszenia_robocze = os.path.join(folder, "ogloszenia.csv")
    ogloszenia_nowe = os.path.join(folder, "ogloszenia_nowe.csv")

    if opcja == 1:
        parser = OtodomParser(url, 100, slownik_warstw, # warstwy GIS
                              ogloszenia_all, ogloszenia_all, ogloszenia_nowe, folder)
        parser.analizuj_df()

    elif opcja == 2:
        try:
            if os.path.exists(folder):
                os.remove(folder)
            os.mkdir(folder)
        except Exception as e:
            print(e)
        parser = OtodomParser(url, 100, # liczba stron
                              slownik_warstw,     # slownik warstw - map zmiennych objasniajacych
                              ogloszenia_robocze, # robocze csv
                              ogloszenia_all,     # csv na polaczone
                              ogloszenia_nowe,    # csv na tylko nowe
                              folder)
        parser.parse()
        parser.spacjalizuj()
        parser.analizuj_df()
