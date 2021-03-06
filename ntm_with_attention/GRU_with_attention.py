# coding=utf-8
import tensorflow as tf
from keras.layers import GRU, Dense, Input, Lambda, Embedding, concatenate, Bidirectional, Dropout
from keras.optimizers import Adam
import numpy as np
import os
from pretreat1.common_pretreat import FIXED_SIZE, RELATION_COUNT, PF_EMBEDDING_LENGTH, POS_EMBEDDING_LENGTH
from attention_layer import AttentionLayer
from keras import Model
from keras.callbacks import Callback
from comm.scorer import get_marco_f1
from keras.callbacks import EarlyStopping, ModelCheckpoint


class f1_calculator(Callback):
    def __init__(self, index, pos1_index, pos2_index, pos, result):
        self.index = index
        self.result = result
        self.pos1_index = pos1_index
        self.pos2_index = pos2_index
        self.pos = pos

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        predict_result = self.model.predict(
            x=[self.index, self.pos1_index, self.pos2_index, self.pos, ])
        f1_score = get_marco_f1(predict_result, self.result)
        self.save_best(f1_score)
        logs["f1_score"] = f1_score

    def save_best(self, f1):
        with open("/home/zy/git/zy_paper/ntm_with_attention/gru/README", "r") as file:
            best_f1 = file.readline()
            best_f1 = float(best_f1)
        if f1 > best_f1:
            os.system("rm /home/zy/git/zy_paper/ntm_with_attention/gru/README")
            with open("/home/zy/git/zy_paper/ntm_with_attention/gru/README", "w") as file:
                file.write(str(f1))
            self.model.save("/home/zy/git/zy_paper/ntm_with_attention/gru/simple_gru.model")


PF_EMBEDDING_DIM = 25
POS_EMBEDDING_DIM = 25

np.random.seed(1337)
tf.set_random_seed(1337)

os.chdir("/home/zy/data/zy_paper/common_pretreat")
os.environ["CUDA_VISIBLE_DEVICES"] = "3"
embedding_vec = np.load("wiki_100d_vec.npy")
train_word_index = np.load("train_word_index.npy")
test_word_index = np.load("test_word_index.npy")
train_relative_e1_distance = np.load("train_relative_e1_distance.npy")
test_relative_e1_distance = np.load("test_relative_e1_distance.npy")
train_relative_e2_distance = np.load("train_relative_e2_distance.npy")
test_relative_e2_distance = np.load("test_relative_e2_distance.npy")
train_pos_tag = np.load("train_pos_tag.npy")
test_pos_tag = np.load("test_pos_tag.npy")
train_label = np.load("train_label.npy")
test_label = np.load("test_label.npy")

word_embedding_dim = embedding_vec.shape[1]

word_input = Input(shape=(FIXED_SIZE,), dtype="int32")
pos_tag_input = Input(shape=(FIXED_SIZE,), dtype="int32")
relative_e1_input = Input(shape=(FIXED_SIZE,), dtype="int32")
relative_e2_input = Input(shape=(FIXED_SIZE,), dtype="int32")

word_embedding = Embedding(input_dim=len(embedding_vec), output_dim=word_embedding_dim, input_length=FIXED_SIZE,
                           trainable=True)(word_input)
pos_embedding = Embedding(input_dim=POS_EMBEDDING_LENGTH, output_dim=POS_EMBEDDING_DIM, input_length=FIXED_SIZE,
                          trainable=True)(pos_tag_input)
relative_e1_embedding = Embedding(input_dim=PF_EMBEDDING_LENGTH, output_dim=PF_EMBEDDING_DIM, input_length=FIXED_SIZE,
                                  trainable=True)(relative_e1_input)
relative_e2_embedding = Embedding(input_dim=PF_EMBEDDING_LENGTH, output_dim=PF_EMBEDDING_DIM, input_length=FIXED_SIZE,
                                  trainable=True)(relative_e2_input)

embedding_output = concatenate([word_embedding, pos_embedding, relative_e1_embedding, relative_e2_embedding], axis=2)

gru_layer = Bidirectional(GRU(units=200, return_sequences=True, dropout=0.6))

# (None, 96, 400)
gru_output = gru_layer(embedding_output)

attention_layer = AttentionLayer(80)

output = attention_layer(gru_output)

# output = Dropout(0.4)(output)

output = Dense(RELATION_COUNT, activation="softmax")(output)

model = Model(inputs=[word_input, relative_e1_input, relative_e2_input, pos_tag_input, ], outputs=[output])

optimizer = Adam()

model.compile(optimizer=optimizer, loss="categorical_crossentropy", metrics=["accuracy"])

model.fit(x=[train_word_index, train_relative_e1_distance, train_relative_e2_distance, train_pos_tag, ],
          y=[train_label],
          # validation_data=(
          #     [test_index, test_relative_e1_pos, test_relative_e2_pos, test_pos], [test_labels]),
          batch_size=32,
          epochs=1000,
          callbacks=[f1_calculator(test_word_index, test_relative_e1_distance, test_relative_e2_distance, test_pos_tag,
                                   test_label),
                     ModelCheckpoint("simple_cnn.model", "f1_score", 0, True, False, "max"),
                     EarlyStopping("f1_score", 0.000001, 50, 0, "max")
                     ]
          )
