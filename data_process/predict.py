import h5py
import lightgbm as lgb
import os
import matplotlib.pyplot as plt
import pandas as pd
import torch
from data_process.fingerprint import FPS
# from data_process.gcnn import GConvRegressor
# from data_process.smiles_to_graph import *
# from data_process.gcnn import MolDataset
from torch.utils.data import DataLoader
from data_process.MLP import Net as MLP
import numpy as np

FP_SIZE = 1024
RADIUS = 2
RESULT_DIR = os.path.join(f'../result/2022-07-07/light_GBM/')
models = []
data_path = '/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv'
data = pd.read_csv(data_path).iloc[:, -2:]
smile = data['smile']
result = []


def get_sim(smi1, smi2):
    x = np.array(FPS(fp_size=FP_SIZE, radius=RADIUS).get_fps([smi1, smi2]))
    def tanimoto(v1, v2):
        return (np.bitwise_and(v1, v2).sum() / np.bitwise_or(v1, v2).sum())
    sim = tanimoto(x[0], x[1])
    return sim

for s in smile:
    if s.find('<') > 0:
        s = s[:s.find('<')]
        result.append(s)
data['smile'] = result

featurizer = FPS(fp_size=FP_SIZE, radius=RADIUS)
x = featurizer.get_fps(data)

def predict(smis, log):
    model = lgb.Booster(model_file=os.path.join(RESULT_DIR, f'model_step2sample_factor400.h5'))
    x = FPS(fp_size=2048, radius=3).get_fps(list(smis))
    scores = model.predict(x)
    print(scores)
    print(log, scores)


def predict_by_lgb():
    model = lgb.Booster(model_file=os.path.join(RESULT_DIR, f'model_undersample_8_sample_factor_600.h5'))
    scores = model.predict(x)
    for s in scores:
        print(s)


def predict_by_GCN_RE():
    model_dir = os.path.join('../result/2022-06-14/GCNN_Re/gcnn_re_6.pt')
    model = GConvRegressor(128, 6)
    model.load_state_dict(torch.load(model_dir))
    dataset = MolDataset(smile, [0 for i in range(len(smile))], 90)
    dataset = DataLoader(dataset, batch_size=len(smile))
    for data in dataset:
        data['X'] = torch.tensor(data['X'], dtype=torch.float32)
        data['A'] = torch.tensor(data['A'], dtype=torch.float32)
        for i in np.squeeze(model(data['X'], data['A']).detach().numpy()):
            print(i)


def predict_by_MLP():
    model_dir = os.path.join('../result/2022-07-07/MLP/MLP_None.pt')
    model = MLP(2048, [256 for i in range(1)])
    state_dict = torch.load(model_dir)
    model.load_state_dict(state_dict)
    model = model.eval()
    global x
    preds = np.squeeze(model(torch.FloatTensor(x)).detach().numpy())
    for i in preds:
        print(i)
    plt.plot(preds)
    plt.show()

predict_by_lgb()
