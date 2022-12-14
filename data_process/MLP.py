import os.path
import numpy as np
import torch
from torch.utils import data
from torch import nn
import plotly.graph_objs as go
import plotly
import matplotlib.pyplot as plt
from pytorchtools.pytorchtools import EarlyStopping
from datetime import date
import warnings
from fingerprint import *
from optuna import Trial
from create_dataset import FPS_DataSet
import time
from torch.utils import data as dt
from torch.utils.data import Dataset, DataLoader
from torch.optim.lr_scheduler import ExponentialLR


warnings.filterwarnings("ignore")

torch.manual_seed(1024)
LOG_FILE = os.path.join('.', 'run.log')
DATA_DIR = '/home/ubuntu/project/tigit/data/train_data/TIGIT_trisython_smi_low.csv'
RESULT_DIR = f'/home/ubuntu/project/tigit/result/{date.today()}/MLP'
FPS_DIR = f'/home/ubuntu/project/tigit/data/train_data/fps/TIGIT_trisython_smi_low_radius_3.h5'
MAX_NTOMS = 90
BATCH_SIZE = 512
penalty_factor = 18
NAME = None


if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)


class CustomLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.mse = nn.MSELoss()
        self.penalty = 18

    def forward(self, pred, actual):
        loss = torch.where(torch.min(pred) < -300., torch.mean(self.mse(pred, actual)) * self.penalty,
                           torch.mean(self.mse(pred, actual)))
        return loss


class MyDataset(Dataset):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, item):
        return self.x[item], self.y[item]

    def __len__(self):
        return self.x.shape[0]


class Net(nn.Module):

    def __init__(self, input_size, layer_sizes, dropout=0.8):
        super(Net, self).__init__()
        layers = [nn.Linear(input_size, layer_sizes[0])]
        for i in range(1, len(layer_sizes)):
            layers.append(nn.Dropout(dropout))
            layers.append(nn.ReLU())
            layers.append(nn.Linear(layer_sizes[i - 1], layer_sizes[i]))
        layers.append(nn.Linear(layer_sizes[-1], 1))
        self.layers = nn.Sequential(*layers)
        self.softplus = torch.nn.functional.softplus

    def forward(self, x):
        return self.softplus(self.layers(x))


def load_array(data_array, batch_size, istrain=True):
    '''create dataset'''
    dataset = data.TensorDataset(*data_array)
    return data.DataLoader(dataset, batch_size, shuffle=istrain)


def main(train_dataloader, valid_dataloader1, valid_dataloader2, num_train, layers, hidden=256, fpsize=2048):
    model = Net(fpsize, [hidden for i in range(layers)])
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    n_epochs = 20
    early_stopping = EarlyStopping(verbose=True, patience=20, path=os.path.join(RESULT_DIR, f'MLP_{NAME}.pt'))
    scheduler = ExponentialLR(optimizer, gamma=0.9)
    loss_fn = nn.MSELoss()
    st = time.time()

    for epoch in range(n_epochs):
        mse_loss_list = []
        for i_batch, batch in enumerate(train_dataloader):
            x, y = batch
            optimizer.zero_grad()
            pred = model(x).squeeze(-1)
            loss = loss_fn(pred, y) * BATCH_SIZE
            mse = loss.detach().numpy()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            mse_loss_list.append(mse)
        mse_loss = sum(mse_loss_list) / num_train

        for i_batch, batch in enumerate(valid_dataloader1):
            x, y = batch
            pred = model(x).squeeze(-1)
            mse_test_loss1 = loss_fn(pred, y)

        for i_batch, batch in enumerate(valid_dataloader2):
            x, y = batch
            pred = model(x).squeeze(-1)
            mse_test_loss2 = loss_fn(pred, y)

        if early_stopping.early_stop:
            print("Early stopping")
            break

        print_msg = ('epoch:' + str(epoch) + ' '
                                             f'train_loss: {mse_loss:.5f}' + ' ' +
                     f'valid_loss1: {mse_test_loss1:.5f}' + ' ' +
                     f'valid_loss2: {mse_test_loss2:.5f}')

        print(print_msg)
        early_stopping(mse_test_loss1 + mse_test_loss2, model)
        scheduler.step()

    end = time.time()
    print('Time:', end - st)

    model_dir = os.path.join(RESULT_DIR, f'MLP_{NAME}.pt')
    model = Net(fpsize, [hidden for i in range(layers)])
    state_dict = torch.load(model_dir)
    model.load_state_dict(state_dict)
    return mse_test_loss1 + mse_test_loss2, model


def eva(model, train_dataloader, valid_dataloader1, valid_dataloader2, test_dataloader1, test_dataloader2, num_train):
    model.eval()
    y_pred_train = []
    Y_train_b = []
    loss_fn = nn.MSELoss()
    rmse_loss_list = []
    mse_loss_list = []
    for i_batch, batch in enumerate(train_dataloader):
        x, y = batch
        pred = model(x).squeeze(-1)

        loss = loss_fn(pred, y) * BATCH_SIZE
        mse = loss.detach().numpy()

        y_pred_train.extend(list(pred.detach().numpy()))
        Y_train_b.extend(list(y.detach().numpy()))

        mse_loss_list.append(mse)

    train_mse = sum(mse_loss_list) / num_train
    train_rmlse = sum(rmse_loss_list) / num_train

    y_pred_test1 = []
    Y_test_b1 = []
    for i_batch, batch in enumerate(test_dataloader1):
        x, y = batch
        pred = model(x).squeeze(-1)
        test_mse1 = loss_fn(pred, y).detach().numpy()
        y_pred_test1.append(pred)
        Y_test_b1.append(y)

    y_pred_test2 = []
    Y_test_b2 = []
    for i_batch, batch in enumerate(test_dataloader2):
        x, y = batch
        pred = model(x).squeeze(-1)
        print(pred)
        test_mse2 = loss_fn(pred, y).detach().numpy()
        top_set,top_set_ind = pred.topk(6)

        print(top_set_ind)
        test_acc = len(set(top_set_ind.numpy()) & set(range(6))) / 6
        y_pred_test2.append(pred)
        Y_test_b2.append(y)

    y_pred_valid1 = []
    y_valid_b1 = []
    for i_batch, batch in enumerate(valid_dataloader1):
        x, y = batch
        pred = model(x).squeeze(-1)
        valid_mse1 = loss_fn(pred, y).detach().numpy()
        y_pred_valid1.append(pred)
        y_valid_b1.append(y)

    y_pred_valid2 = []
    y_valid_b2 = []
    for i_batch, batch in enumerate(valid_dataloader2):
        x, y = batch
        pred = model(x).squeeze(-1)
        valid_mse2 = loss_fn(pred, y).detach().numpy()
        top_set,top_set_ind = pred.topk(6)
        valid_acc = len(set(top_set_ind.numpy()) & set(range(6)))/6
        print(top_set,top_set_ind)
        y_pred_valid2.append(pred)
        y_valid_b2.append(y)



    print('train_mse', train_mse)
    print('test_mse1', test_mse1)
    print('test_mse2', test_mse2)
    print('valid_mse1', valid_mse1)
    print('valid_mse2', valid_mse2)
    print('valid_acc',valid_acc)
    print('test_acc',test_acc)
    return train_mse, train_rmlse, test_mse1, test_mse2, valid_mse1, valid_mse2, valid_acc,test_acc


class RMSLELoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.mse = nn.MSELoss()

    def forward(self, pred, actual):
        pred = torch.where(pred.to(torch.float) < 0., torch.tensor(0, dtype=torch.float), pred.to(torch.float))
        return torch.sqrt(self.mse(torch.log(pred + 1), torch.log(actual + 1)))


def plot(pre, true):
    ls = np.arange(len(pre))
    trace0 = go.Scatter(x=ls, y=pre, mode='lines+markers', name='pre')
    trace1 = go.Scatter(
        x=ls, y=true, mode='lines+markers', name='true')
    data = [trace0, trace1]
    plotly.offline.plot(data, filename='scatter-MLP.html')
    plt.show()


def write_result(content, path):
    if not os.path.exists(path):
        data = pd.DataFrame(
            columns=['parameters', ])
        data.to_csv(path, index=False)
    data = pd.read_csv(path)
    data = data.append(content, ignore_index=True)
    data.to_csv(path, index=False)


def search():
    batch_size = BATCH_SIZE
    data = pd.read_csv('/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv')
    # smiles = [s[:s.find('<')] for s in data['smile']][::2]
    # Y = data['Y'].to_list()[::2]
    layers = [1,2]
    hiddens = [256,512]
    undersampled_steps = [2,4,6,8]
    is_generate = False
    generate_factor = 0
    generate_type = 1
    is_oversample = True
    sample_factors = [200,400,600,800]
    modify_bit = 0
    modify_type = 0
    radius = [2,3]
    fpsizes = [1024,2048]
    value = ['O=C(O)COC1=CC=C(C(C2=CC=C(OC)C=C2OC)NC([C@@H](NC(C3=CC=C(C=C(OC)C=C4)C4=C3)=O)CC5=CSC=C5)=O)C=C1']
    global NAME
    for layer in layers:
        for hidden in hiddens:
            for sample_factor in sample_factors:
                for undersampled_step in undersampled_steps:
                    for radiu in radius:
                        for fpsize in fpsizes:
                            NAME = f'{layer}_{hidden}_{sample_factor}_{undersampled_step}_{radiu}_{fpsize}'
                            dataset = FPS_DataSet(undersampled_step=undersampled_step, value=[value], is_generate=is_generate,
                                                  generate_factor=generate_factor,
                                                  generate_type=generate_type,
                                                  is_oversample=is_oversample, sample_factor=sample_factor, modify_bit=modify_bit,
                                                  append_smi=[value], append_y=[0.9], fpsize=fpsize, radius=radiu)

                            x, y = dataset.get_train_data_set()
                            X_train, Y_train, = x, y
                            X_valid1, X_valid2, Y_valid1, Y_valid2 = dataset.get_valid_data_set(num=100000)
                            X_test1, X_test2, Y_test1, Y_test2 = dataset.get_test_data_set(num=100000)

                            X_train, Y_train, = torch.FloatTensor(X_train), torch.FloatTensor(Y_train)
                            X_valid1, Y_valid1 = torch.FloatTensor(X_valid1), torch.FloatTensor(Y_valid1)
                            X_test1, Y_test1 = torch.FloatTensor(X_test1), torch.FloatTensor(Y_test1)
                            X_valid2, Y_valid2, X_test2, Y_test2 = torch.FloatTensor(X_valid2), torch.FloatTensor(Y_valid2), \
                                                                   torch.FloatTensor(X_test2), torch.FloatTensor(Y_test2)

                            train_dataset = dt.TensorDataset(X_train, Y_train)
                            valid_dataset1 = dt.TensorDataset(X_valid1, Y_valid1)
                            test_dataset1 = dt.TensorDataset(X_test1, Y_test1)
                            valid_dataset2 = dt.TensorDataset(X_valid2, Y_valid2)
                            test_dataset2 = dt.TensorDataset(X_test2, Y_test2)

                            train_dataloader = DataLoader(train_dataset, shuffle=True, batch_size=batch_size)
                            valid_dataloader1 = DataLoader(valid_dataset1, batch_size=len(valid_dataset1))
                            test_dataloader1 = DataLoader(test_dataset1, shuffle=True, batch_size=len(test_dataset1))
                            valid_dataloader2 = DataLoader(valid_dataset2, batch_size=len(valid_dataset2))
                            test_dataloader2 = DataLoader(test_dataset2, batch_size=len(test_dataset2))

                            num_train = len(train_dataset)

                            mse, model = main(train_dataloader, valid_dataloader1, valid_dataloader2, num_train, layers=layer, fpsize=fpsize,
                                              hidden=hidden)
                            train_mse, train_rmlse, test_mse1, test_mse2, valid_mse1, valid_mse2, valid_acc,test_acc = eva(model, train_dataloader,
                                                                                                       valid_dataloader1, valid_dataloader2,
                                                                                                       test_dataloader1, test_dataloader2,
                                                                                                       num_train)
                            print(
                                f'current para radius:{radius},fpsize:{fpsize},sample_factor:{sample_factor},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid loss:{valid_mse1 + valid_mse2},valid_acc:{valid_acc},test_acc{test_acc}')
                            path = os.path.join(RESULT_DIR, 'MLP.csv')
                            write_result({'mse': train_mse,
                                          'is_oversamle': is_oversample,
                                          'oversample_factor': sample_factor,
                                          'undersampled_step': undersampled_step,
                                          'is_generate': is_generate,
                                          'generate_factor': generate_factor, 'modify_bit': modify_bit, 'modify_type': modify_type,
                                          'test_mse': test_mse1, 'test_mse2': test_mse2,
                                          'train_mse': train_mse, 'train_mse2': train_rmlse,
                                          'valid_mse': valid_mse1, 'valid_mse2': valid_mse2,
                                          'valid_acc':valid_acc, 'test_acc':test_acc,
                                          'append_smi': value if value else 'None',
                                          'layers':layer,'hidden':hidden,'tag':NAME
                                          }, path=path)



def set_seed():
    np.random.seed(1024)
    torch.manual_seed(1024)
    torch.cuda.manual_seed(1024)
    torch.cuda.manual_seed_all(1024)


def process():
    batch_size = BATCH_SIZE
    data = pd.read_csv('/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv')
    smiles = [s[:s.find('<')] for s in data['smile']][::2]
    Y = data['Y'].to_list()[::2]

    undersampled_step = 6
    is_generate = False
    generate_factor = 0
    generate_type = 0
    is_oversample = True
    sample_factor = 400
    modify_bit = 0

    radius = 3
    fpsize = 2048
    layer = 1
    hidden = 256

    global NAME
    for i in range(6):
        value = ['O=C(O)COC1=CC=C(C(C2=CC=C(OC)C=C2OC)NC([C@@H](NC(C3=CC=C(C=C(OC)C=C4)C4=C3)=O)CC5=CSC=C5)=O)C=C1']
        value.append(smiles[i])
        NAME = f'f78,smile_{i}'
        dataset = FPS_DataSet(undersampled_step=undersampled_step, value=value, is_generate=is_generate,
                              generate_factor=generate_factor,
                              generate_type=generate_type,
                              is_oversample=is_oversample, sample_factor=sample_factor, modify_bit=modify_bit,
                              append_smi=value, append_y=[0.8,Y[i]], fpsize=fpsize, radius=radius)
        x, y = dataset.get_train_data_set()
        X_train, Y_train, = x, y
        X_valid1, X_valid2, Y_valid1, Y_valid2 = dataset.get_valid_data_set(num=100000)
        X_test1, X_test2, Y_test1, Y_test2 = dataset.get_test_data_set(num=100000)
        X_train, Y_train, = torch.FloatTensor(X_train), torch.FloatTensor(Y_train)
        X_valid1, Y_valid1 = torch.FloatTensor(X_valid1), torch.FloatTensor(Y_valid1)
        X_test1, Y_test1 = torch.FloatTensor(X_test1), torch.FloatTensor(Y_test1)
        X_valid2, Y_valid2, X_test2, Y_test2 = torch.FloatTensor(X_valid2), torch.FloatTensor(Y_valid2), \
                                               torch.FloatTensor(X_test2), torch.FloatTensor(Y_test2)

        train_dataset = dt.TensorDataset(X_train, Y_train)
        valid_dataset1 = dt.TensorDataset(X_valid1, Y_valid1)
        test_dataset1 = dt.TensorDataset(X_test1, Y_test1)
        valid_dataset2 = dt.TensorDataset(X_valid2, Y_valid2)
        test_dataset2 = dt.TensorDataset(X_test2, Y_test2)

        set_seed()
        train_dataloader = DataLoader(train_dataset, shuffle=True, batch_size=batch_size)
        valid_dataloader1 = DataLoader(valid_dataset1, batch_size=len(valid_dataset1))
        test_dataloader1 = DataLoader(test_dataset1, batch_size=len(test_dataset1))
        valid_dataloader2 = DataLoader(valid_dataset2, batch_size=len(valid_dataset2))
        test_dataloader2 = DataLoader(test_dataset2,  batch_size=len(test_dataset2))

        num_train = len(train_dataset)


        mse, model = main(train_dataloader, valid_dataloader1, valid_dataloader2, num_train, layers=layer, fpsize=fpsize,
                          hidden=hidden)
        train_mse, train_rmlse, test_mse1, test_mse2, valid_mse1, valid_mse2, valid_acc, test_acc = eva(model,
                                                                                                        train_dataloader,
                                                                                                        valid_dataloader1,
                                                                                                        valid_dataloader2,
                                                                                                        test_dataloader1,
                                                                                                        test_dataloader2,
                                                                                                        num_train)
        print(
            f'current para radius:{radius},fpsize:{fpsize},sample_factor:{sample_factor},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid loss:{valid_mse1 + valid_mse2},valid_acc:{valid_acc},test_acc{test_acc}')
        path = os.path.join(RESULT_DIR, 'MLP.csv')
        write_result({'mse': train_mse,
                      'is_oversamle': is_oversample,
                      'oversample_factor': sample_factor,
                      'undersampled_step': undersampled_step,
                      'is_generate': is_generate,
                      'generate_factor': generate_factor, 'modify_bit': modify_bit, 'modify_type': generate_type,
                      'test_mse': test_mse1, 'test_mse2': test_mse2,
                      'train_mse': train_mse, 'train_mse2': train_rmlse,
                      'valid_mse': valid_mse1, 'valid_mse2': valid_mse2,
                      'valid_acc': valid_acc, 'test_acc': test_acc,
                      'append_smi': value if value else 'None',
                      'layers': layer, 'hidden': hidden, 'tag': NAME,
                      }, path=path)

def optuna_params(trial:Trial):
    if not os.path.exists(os.path.join(RESULT_DIR, 'best')):
        os.mkdir(os.path.join(RESULT_DIR, 'best'))

    data = pd.read_csv('/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv')
    smiles = [s[:s.find('<')] for s in data['smile']][::2]
    Y = data['Y'].to_list()[::2]
    undersampled_step = trial.suggest_int('undersampled_step', 2, 10)
    is_generate = False
    generate_factor = 0
    generate_type = 0
    is_oversample = True
    sample_factor = trial.suggest_int('sample_factor', 20, 1000)
    modify_bit = 0
    i = trial.suggest_int('i', 0,6)
    radius = trial.suggest_categorical('radius', [2, 3])
    fpsize = trial.suggest_categorical('fpsize', [1024,2048])
    layers = trial.suggest_int('layers',1,5)
    hidden = trial.suggest_categorical('hidden',[128,256,512,1024])
    batch_size = 512
    value = [smiles[i]]
    dataset = FPS_DataSet(undersampled_step=undersampled_step, value=value, is_generate=is_generate,
                          generate_factor=generate_factor,
                          generate_type=generate_type,
                          is_oversample=is_oversample, sample_factor=sample_factor, modify_bit=modify_bit,
                          append_smi=value, append_y=[Y[i]], fpsize=fpsize, radius=radius)

    x, y = dataset.get_train_data_set()
    X_train, Y_train, = x, y
    X_valid1, X_valid2, Y_valid1, Y_valid2 = dataset.get_valid_data_set(num=100000)
    X_test1, X_test2, Y_test1, Y_test2 = dataset.get_test_data_set(num=100000)
    X_train, Y_train, = torch.FloatTensor(X_train), torch.FloatTensor(Y_train)
    X_valid1, Y_valid1 = torch.FloatTensor(X_valid1), torch.FloatTensor(Y_valid1)
    X_test1, Y_test1 = torch.FloatTensor(X_test1), torch.FloatTensor(Y_test1)
    X_valid2, Y_valid2, X_test2, Y_test2 = torch.FloatTensor(X_valid2), torch.FloatTensor(Y_valid2), \
                                           torch.FloatTensor(X_test2), torch.FloatTensor(Y_test2)

    train_dataset = dt.TensorDataset(X_train, Y_train)
    valid_dataset1 = dt.TensorDataset(X_valid1, Y_valid1)
    test_dataset1 = dt.TensorDataset(X_test1, Y_test1)
    valid_dataset2 = dt.TensorDataset(X_valid2, Y_valid2)
    test_dataset2 = dt.TensorDataset(X_test2, Y_test2)

    set_seed()
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size)
    valid_dataloader1 = DataLoader(valid_dataset1, batch_size=len(valid_dataset1))
    test_dataloader1 = DataLoader(test_dataset1, batch_size=len(test_dataset1))
    valid_dataloader2 = DataLoader(valid_dataset2, batch_size=len(valid_dataset2))
    test_dataloader2 = DataLoader(test_dataset2, batch_size=len(test_dataset2))

    num_train = len(train_dataset)

    mse, model = main(train_dataloader, valid_dataloader1, valid_dataloader2, num_train, layers=layers,
                      fpsize=fpsize, hidden=hidden)
    train_mse, train_rmlse, test_mse1, test_mse2, valid_mse1, valid_mse2, valid_acc, test_acc = eva(model,
                                                                                                    train_dataloader,
                                                                                                    valid_dataloader1,
                                                                                                    valid_dataloader2,
                                                                                                    test_dataloader1,
                                                                                                    test_dataloader2,
                                                                                                    num_train)
    print(
        f'current para   sample_factor:{0},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid_mse:{valid_mse1 + valid_mse2}')
    path = os.path.join(RESULT_DIR, 'MLP.csv')
    write_result({'mse': train_mse,
                  'is_oversamle': is_oversample,
                  'oversample_factor': sample_factor,
                  'undersampled_step': undersampled_step,
                  'is_generate': is_generate,
                  'generate_factor': generate_factor, 'modify_bit': modify_bit, 'modify_type': generate_type,
                  'test_mse': test_mse1, 'test_mse2': test_mse2,
                  'train_mse': train_mse, 'train_mse2': train_rmlse,
                  'valid_mse': valid_mse1, 'valid_mse2': valid_mse2,
                  'valid_acc': valid_acc, 'test_acc': test_acc,
                  'append_smi': [smiles[i]]
                  }, path=path)


if __name__ == '__main__':
    process()

