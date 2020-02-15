from keras.models import Sequential
from keras.layers.core import Dense
from keras.optimizers import Adam
from sklearn.model_selection import train_test_split

class MyNeuralNetwork():
    def __init__(self) -> object:
        self.r2 = 0
        self.coef_df = 0

    def __repr__(self):
        return "I am a Linear Regression model!"

    def fit_model(self, X: object, y: object, dataframe: object):

        # Split using ALL data in sample_df
        X_train, X_test, y_train, y_test = train_test_split(dataframe[X], dataframe[y], test_size=0.25)

        def create_mlp(dim, regress=False):
            # define our MLP network
            model = Sequential()
            model.add(Dense(8, input_dim=dim, activation="relu"))
            model.add(Dense(4, activation="relu"))
            # check to see if the regression node should be added
            if regress:
                model.add(Dense(1, activation="linear"))
            # return our model
            return model

        model = create_mlp(X_train.shape[1], regress=True)
        opt = Adam(lr=1e-3, decay=1e-3 / 200)
        model.compile(loss="mean_absolute_percentage_error", optimizer=opt)

        model.fit(X_train, y_train, validation_data=(X_test, y_test),
                  epochs=10, batch_size=5)

        dataframe['preds'] = model.predict(dataframe[X])
        df = dataframe[['cena_za_metr', 'preds']]
        df = df.sort_values('cena_za_metr')



