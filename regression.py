import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR
from sklearn.linear_model import RidgeCV
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import GridSearchCV
from sklearn.linear_model import LassoCV
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from pandas import DataFrame
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer


class MyLinearRegression():
    def __init__(self, folder) -> object:
        self.r2 = 0
        self.coef_df = 0
        self.folder = folder
        self.lista_df = []
        self.vectorizer = CountVectorizer(min_df=4)

    def __repr__(self):
        return "I am a Linear Regression model!"

    def corr_matrix(self, df, cols, folder):
        """"
                plots corr matrix of explanatory variables
                """
        plt.figure(figsize=(10, 5))
        c = df[cols].corr()
        sns.heatmap(c, cmap="BrBG", annot=True)
        plt.savefig(os.path.join(folder, "corr_matrix.jpg"), bbox_inches='tight')

    def pairplot(self, df, cols, folder, name):
        """"
                plots corr matrix of explanatory variables
                """
        plt.figure(figsize=(10, 5))
        sns.pairplot(df[cols], diag_kind="kde")
        plt.savefig(os.path.join(folder, name + "_pairplot.jpg"), bbox_inches='tight')

    def draw_history(self, df, folder):
        """"
        draws plot of mean price change and a histogram of a mean price
        """
        try:
            df['data'] = df['data'].astype('str')
            df["data"] = df["data"].str.split(" ", n=1, expand=True)
            # konwersja na format daty
            df['data'] = pd.to_datetime(df['data'], format='%Y-%m-%d')
            df.set_index('data', inplace=True)
            df_daily = df.resample('w').mean()
            plt.figure(figsize=(12, 8))
            plt.style.use('ggplot')
            plt.grid = True
            plt.plot(df_daily.index, df_daily.cena_za_metr)
            plt.savefig(os.path.join(folder, "prices_change.jpg"))
        except Exception as e:
            print(e)

        # hisotgram ceny
        plt.figure(figsize=(12, 8))
        plt.style.use('ggplot')
        _ = sns.distplot(df['cena_za_metr']).set_title('housing prices (PLN per sq m)')
        plt.savefig(os.path.join(folder, "prices_histogram.jpg"))

    def fit_nlp(self, x_txt: object, y: object, dataframe: object):

        X_train, X_test, y_train, y_test = train_test_split(dataframe[x_txt], dataframe[y], test_size=0.2)
        X_train = self.vectorizer.fit_transform(X_train)
        X_test = self.vectorizer.transform(X_test)

        linreg = LinearRegression()
        # Fit it to the training data
        linreg.fit(X_train, y_train)

        # Compute and print the metrics
        self.r2 = linreg.score(X_test, y_test)
        print("nlp model, R2 na podsawie opisu  wynosi {}".format( self.r2))

        self.lista_df.append(self.predict(linreg, x_txt, dataframe, "nlp"))
        df_pred = pd.concat(self.lista_df, axis=1)
        df_pred = df_pred.loc[:, ~df_pred.columns.duplicated()]

        return linreg, df_pred

    def fit_model(self, X: object, y: object, dataframe: object, reg, cv=0 ):
        """
        Fit ridge regression model coefficients from a Pandas DataFrame.
        Arguments:
        X: A list of columns of the dataframe acting as features. Must be only numerical.
        y: Name of the column of the dataframe acting as the target
        dataframe: dataframe with variables (X) and target (y) columns
        """
        assert (
                type(X) == list
        ), "X must be a list of the names of the numerical feature/predictor columns"
        assert (
                type(y) == str
        ), "y must be a string - name of the column you want as target"

        if reg == 'linreg':
            model = LinearRegression()
            # regression = GridSearchCV(model, param_grid, cv=cv)
        elif reg == 'ridge':
            model = RidgeCV(cv=cv)
        elif reg == 'svm':
            model = SVR(C=1.0, epsilon=0.2)
        elif reg == 'elastic_CV':
            elastic_net = ElasticNet()
            l1_space = np.linspace(0, 1, 30)
            param_grid = {'l1_ratio': l1_space}
            model = GridSearchCV(elastic_net, param_grid, cv=cv)
        elif reg == 'lasso_CV':
            model = LassoCV(cv=cv, random_state=0)

        # Split using ALL data in sample_df
        X_train, X_test, y_train, y_test = train_test_split(dataframe[X], dataframe[y], test_size=0.2)
        liczba_obserwacji = X_train.shape[0]

        # Setup the pipeline steps: steps
        steps = [
                ('imputation', SimpleImputer(missing_values=np.NAN, strategy='mean')),
                ('scaler', StandardScaler()),
                ('reg', model)]

        # Create the pipeline: pipeline
        self.pipeline = Pipeline(steps)

        # Fit it to the training data
        self.pipeline.fit(X_train, y_train)

        # Compute and print the metrics
        self.r2 = self.pipeline.score(X_test, y_test)
        print("{} model, R2 przy zmiennych {} , wynosi {}. {} obserwacji".format(reg, X, self.r2, liczba_obserwacji))

        self.lista_df.append(self.predict(self.pipeline, X, dataframe, reg))
        # coefficents df - only for
        if reg in ['linreg']:
            self.coef_df = DataFrame(zip(X_train.columns, np.transpose(self.pipeline.steps[2][1].coef_)))
            self.coef_df.columns = ['variable', 'impact of max on price']

        return self.pipeline, self.r2

    def predict(self, pipeline, X, dataframe, reg):
        """Output model prediction.
        Arguments:
        X:
        dataframe:
        """
        if X != 'opis':
            dataframe['cena_pred'] = pipeline.predict(dataframe[X])
            df = dataframe[['cena_za_metr', 'cena_pred', 'opis']]

        else:
            holdout_txt = dataframe[X]
            holdout_opis = self.vectorizer.transform(holdout_txt)
            dataframe['cena_pred'] = pipeline.predict(holdout_opis)
            df = dataframe[['cena_pred', 'opis']]

        df.reset_index(inplace=True)
        df = df.rename(columns={'cena_pred': reg})
        return df

