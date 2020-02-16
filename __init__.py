from main import Otodomer
from parseter import Parseter
import os
from datetime import datetime

if __name__ == '__main__':
    url = 'https://www.otodom.pl/sprzedaz/mieszkanie/krakow/?search%5Bdescription%5D=1&search%5Bcreated_since%\
    5D=14&search%5Bsubregion_id%5D=410&search%5Bcity_id%5D=38'

    slownik_warstw = {'vist_dist': r'shp\osm_vistula_92.shp', 'trams_dist': r'shp\tram_stops.shp'}

    # Opcje:
    #   1 - czytaj stary plik,
    #   2 - czytaj stary + dodaj nowe ogloszenia (dodac rysowanie i zapisywanie zmiany w czasie),
    #           zapisywac ryciny w folderze
    #   3 - spacljalizuj i predytkuj holdout

    opcja = 2

    now = datetime.now()
    data = now.strftime("%Y_%m_%d")
    folder = os.path.join(r'c:\Users\marci\git\Oto_klasor\Raporty', data)
    ogloszenia_all = r'c:\Users\marci\git\Oto_klasor\csv\gdf_stare.csv'
    ogloszenia_robocze = os.path.join(folder, "ogloszenia.csv")
    ogloszenia_nowe = os.path.join(folder, "ogloszenia_nowe.csv")
    holdout = r'c:\Users\marci\git\Oto_klasor\holdout\mwm.csv'


    if opcja == 2:
        try:
            if os.path.exists(folder):
                os.remove(folder)
            os.mkdir(folder)
        except Exception as e:
            print(e)

        parser = Parseter(url,              # adres url
                        50,                  # last page
                        ogloszenia_robocze, # robocze csv
                        ogloszenia_all,     # csv na polaczone (stare + nowe)
                        ogloszenia_nowe,    # csv na tylko nowe
                        folder)
        parser.parse()
        otodomer = Otodomer(slownik_warstw, ogloszenia_robocze, ogloszenia_nowe, ogloszenia_all, holdout, folder)
        otodomer.spacjalizuj()
        otodomer.spacjalizauj_holdout()
        otodomer.analizuj_df()

    # bez web scrapingu
    elif opcja == 3:
            try:
                if os.path.exists(folder):
                    os.remove(folder)
                os.mkdir(folder)
            except Exception as e:
                print(e)
                otodomer = Otodomer(slownik_warstw, ogloszenia_robocze, ogloszenia_nowe, ogloszenia_all, holdout,
                                    folder)
                otodomer.spacjalizauj_holdout()
                otodomer.analizuj_df()



