import pandas as pd
import os
from sklearn import preprocessing
from collections import deque
import random
import numpy as np
from tensorflow.keras.callbacks import TensorBoard
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM, BatchNormalization
import time
import tensorflow as tf
os.environ['KMP_DUPLICATE_LIB_OK']='True'


DESIRED_PERCENT_INCREASE = 1.001;
PERIOD_LENGTH = 50
PERIOD_TO_PREDICT= 15;
COIN_TO_PREDICT='BTC_data' # ["BTC_data", "LTC_data", "BCH_data", "ETH_data", "EOS_data", "XRP_data"]
EPOCHS = 30
BATCH_SIZE = 64
NAME = str(PERIOD_LENGTH) + "-PERIOD_LENGTH-"+str(PERIOD_TO_PREDICT)+"-PERIOD_TO_PREDICT-"+ str(int(time.time()))+"-TIME-"


def print_and_write_to_logfile(log_text):
    if log_text is not None:
        print(log_text + '\n')
        with open('cryptoLogs/logs.txt', 'a') as myfile:
            myfile.write(log_text + '\n\n')
def classifier(price, future_price):
    if(future_price>price*DESIRED_PERCENT_INCREASE):
        return 1
    return 0
def preprocess_cryptodata(data):
    data = data.drop("FUTURE_PRICE_TO_PREDICT", 1)
    for col in data.columns:
        if col != "VALIDATE" and col != "CHANGEPCT24HOUR"and col != "CHANGEPCTDAY"and col != "CHANGEPCTHOUR":
            data[col] = data[col].pct_change()
            data.dropna(inplace=True)
            data = data[np.isfinite(data).all(1)]

            data.dropna(inplace=True)
            # print(data[col].values)
            data[col] = preprocessing.scale(data[col].values)

    data.dropna(inplace=True)
    preprocessed = []
    period = deque(maxlen=PERIOD_LENGTH)

    for i in data.values:
        period.append([n for n in i[:-1]])
        if len(period) == PERIOD_LENGTH:
            preprocessed.append([np.array(period), i[-1]])
    random.shuffle(preprocessed)

    buys = []
    dontBuy = []

    for seq, target in preprocessed:
        if target == 0:
            dontBuy.append([seq, target])
        elif target == 1:
            buys.append([seq, target])

    random.shuffle(buys)
    random.shuffle(dontBuy)

    lower = min(len(buys), len(dontBuy))

    buys = buys[:lower]
    dontBuy = dontBuy[:lower]

    preprocessed = buys + dontBuy
    random.shuffle(
        preprocessed)

    X = []
    y = []

    for seq, target in preprocessed:
        X.append(seq)
        y.append(target)

    return np.array(X), y



gatheredCryptoData = pd.DataFrame()
coins_to_train = ["BTC_data", "LTC_data", "BCH_data", "ETH_data", "EOS_data", "XRP_data"]
for coin in coins_to_train:
    dataset = 'crypto_data/'+coin+'.csv'
    data = pd.read_csv(dataset, names=['TIME', 'PRICE', 'VOLUMEDAYTO', 'VOLUME24HOURTO', 'MEDIAN', 'CHANGEPCT24HOUR',
                                     'CHANGEPCTDAY', 'CHANGEPCTHOUR'])
    data.rename(columns={"PRICE": coin+"_PRICE", "VOLUMEDAYTO": coin+ "_VOLUMEDAYTO",
                       "VOLUME24HOURTO": coin+"_VOLUME24HOURTO", "MEDIAN": coin+"_MEDIAN",
                       "CHANGEPCT24HOUR": coin+"_CHANGEPCT24HOUR", "CHANGEPCTDAY": coin+"_CHANGEPCTDAY",
                       "CHANGEPCTHOUR": coin+"_CHANGEPCTHOUR"}, inplace=True)

    data.set_index("TIME", inplace=True)

    if len(gatheredCryptoData)==0:
        gatheredCryptoData = data
    else:
        gatheredCryptoData = gatheredCryptoData.join(data)

gatheredCryptoData['FUTURE_PRICE_TO_PREDICT'] = gatheredCryptoData[COIN_TO_PREDICT+'_PRICE'].shift(-PERIOD_TO_PREDICT)
gatheredCryptoData['VALIDATE'] = list(map(classifier, gatheredCryptoData[COIN_TO_PREDICT+'_PRICE'], gatheredCryptoData['FUTURE_PRICE_TO_PREDICT']))


sortedCryptoData = sorted(gatheredCryptoData.index.values)
last_5pct = sorted(gatheredCryptoData.index.values)[-int(0.05*len(sortedCryptoData))]
last_20pct = sorted(gatheredCryptoData.index.values)[-int(0.2*len(sortedCryptoData))]

validation_gatheredCryptoData = gatheredCryptoData[(gatheredCryptoData.index >= last_20pct)]
gatheredCryptoData = gatheredCryptoData[(gatheredCryptoData.index < last_5pct)]

train_x, train_y = preprocess_cryptodata(gatheredCryptoData)
validation_x, validation_y = preprocess_cryptodata(validation_gatheredCryptoData)




print("#Train Data: "+str(len(train_x)) +  " #Validation: " + str(len(validation_x)))
print("#Dont Buys: "+str(train_y.count(0)) + ", #Buys: " + str(train_y.count(1)))
print("#Validation Dont buys: "+str(validation_y.count(0)) + ", #Validation Buys: " + str(validation_y.count(1)))

model = Sequential()
model.add(LSTM(128, input_shape=(train_x.shape[1:]), return_sequences=True))
model.add(Dropout(0.2))
model.add(BatchNormalization())

model.add(LSTM(128, return_sequences=True))
model.add(Dropout(0.3))
model.add(BatchNormalization())

model.add(LSTM(128))
model.add(Dropout(0.2))
model.add(BatchNormalization())

model.add(Dense(32, activation='sigmoid'))
model.add(Dropout(0.1))

model.add(Dense(32, activation='relu'))
model.add(Dropout(0.1))

model.add(Dense(32, activation='sigmoid'))
model.add(Dropout(0.1))

model.add(Dense(32, activation='relu'))
model.add(Dropout(0.1))

model.add(Dense(2, activation='softmax'))

opt = tf.keras.optimizers.Adam(lr=0.003, decay=1e-6)

model.compile(
    loss='sparse_categorical_crossentropy',
    optimizer=opt,
    metrics=['accuracy']
)


tensorboard = TensorBoard(log_dir="logs/{}".format(NAME))
filepath = "CRYPTOCOIN_TRAINED-{epoch:02d}-{val_accuracy:.3f}-"+COIN_TO_PREDICT
checkpoint = ModelCheckpoint("models/{}.model".format(filepath, monitor='val_accuracy', verbose=1, save_best_only=True, mode='max'))


train_y = np.asarray(train_y)
validation_y = np.asarray(validation_y)

history = model.fit(
    train_x, train_y,
    batch_size=BATCH_SIZE,
    epochs=EPOCHS,
    validation_data=(validation_x, validation_y),
    callbacks=[tensorboard, checkpoint],
)

score = model.evaluate(validation_x, validation_y, verbose=0)
print('Test loss:', score[0])
print('Test accuracy:', score[1])

model.save("models/{}".format(NAME))
