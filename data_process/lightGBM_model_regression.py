import matplotlib.pyplot as plt
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
import plotly
import plotly.graph_objs as go
from optuna import Trial
from datetime import date
from generate_data import *
from create_dataset import FPS_DataSet
from optuna import trial

DATA_DIR = '../data/train_data/TIGIT_trisython_smi_low.csv'
FPS_DIR = f'/home/ubuntu/project/tigit/data/train_data/fps/TIGIT_trisython_smi_low_radius_3.h5'
RESULT_DIR = f'../result/{date.today()}/light_GBM'
PATH = f'../result/{date.today()}/model_result.csv'
SEED = 2020
NAME = ''

if not os.path.exists(RESULT_DIR):
    os.makedirs(RESULT_DIR)

LOG_FILE = os.path.join('.', 'run.log')

seed0 = 2021
penalty_factor = 20
is_oversample = True


def main_modify(para, train_dataset, valid_dataset1, valid_dataset2):
    model = lgb.train(params=para,
                      num_boost_round=2000,
                      train_set=train_dataset,
                      valid_sets=[train_dataset, valid_dataset1, valid_dataset2],
                      verbose_eval=1000,
                      early_stopping_rounds=200,
                      )
    model.save_model(os.path.join(RESULT_DIR, f'model_{NAME}.h5'))
    return model


def fit_lgbm(trial, train, val, devices=(-1,), seed=None, cat_features=None, num_rounds=1500):
    X_train, y_train = train
    X_valid, y_valid = val
    params = {
        # 'num_leaves': trial.suggest_intrain_high (2).csvt('num_leaves', 2, 256),
        # 'objective': 'mse',
        'max_depth': -1,
        'learning_rate': trial.suggest_uniform('learning_rate', 1e-3, 0.1),
        "boosting": "rf",
        'lambda_l1': trial.suggest_loguniform('lambda_l1', 1e-8, 10.0),
        'lambda_l2': trial.suggest_loguniform('lambda_l2', 1e-8, 10.0),
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 200, 1000, step=100),
        "max_bin": trial.suggest_int("max_bin", 200, 300),
        "num_leaves": trial.suggest_int("num_leaves", 20, 3000, step=20),
        "bagging_freq": 5,
        "bagging_fraction": trial.suggest_uniform('bagging_fraction', 0.1, 1.0),
        "feature_fraction": trial.suggest_uniform('feature_fraction', 0.4, 1.0),
        "metric": 'mse',
        "verbosity": -1,
    }

    device = devices[0]
    if device == -1:
        pass
    else:
        print(f'using gpu device_id {device}...')
        params.update({'device': 'gpu', 'gpu_device_id': device})

    params['seed'] = seed

    early_stop = 50
    verbose_eval = 250

    d_train = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_features)
    d_valid = lgb.Dataset(X_valid, label=y_valid, categorical_feature=cat_features)
    watchlist = [d_train, d_valid]
    print('training LGB:')
    model = lgb.train(params,
                      train_set=d_train,
                      num_boost_round=num_rounds,
                      valid_sets=watchlist,
                      verbose_eval=verbose_eval,
                      early_stopping_rounds=early_stop,
                      )

    y_pred_valid = model.predict(X_valid, num_iteration=model.best_iteration)
    print('best_score', model.best_score)
    log = {'train/l2': model.best_score['training']['l2'],
           'valid/l2': model.best_score['valid_1']['l2']}
    return model, y_pred_valid, log


def plot(pre, true):
    ls = np.arange(len(pre))
    trace0 = go.Scatter(x=ls, y=pre, mode='lines+markers', name='pre')
    trace1 = go.Scatter(
        x=ls, y=true, mode='lines+markers', name='true')
    data = [trace0, trace1]
    plotly.offline.plot(data, filename='scatter-mode_log.html')
    plt.show()


def eva(model, X_train, X_valid1, X_valid2, Y_train, Y_valid1, Y_valid2, X_test1, X_test2, Y_test1, Y_test2):

    def predict(model, input, actual, cal_pre=False):
        scores = model.predict(input)
        mse = mean_squared_error(actual, scores)
        if cal_pre:
            result = enumerate(scores)
            dict_ = {i: s for i, s in result}
            dict_sort = sorted(dict_.items(), key=lambda x: x[1], reverse=True)
            pre_top = [x[0] for x in dict_sort[:6]]
            res = len(list(set(pre_top) & set(range(6))))
            res = res / 6
            return mse, res
        return mse

    train_mse = predict(model, X_train, Y_train)
    valid_mse1 = predict(model, X_valid1, Y_valid1)
    valid_mse2, valid_acc = predict(model, X_valid2, Y_valid2, True)
    test_mse1 = predict(model, X_test1, Y_test1)
    test_mse2, test_acc = predict(model, X_test2, Y_test2, True)
    return train_mse, valid_mse1, valid_mse2, test_mse1, test_mse2, valid_acc, test_acc


def write_result(content, path=PATH):
    if not os.path.exists(path):
        data = pd.DataFrame(
            columns=['parameters', ])
        data.to_csv(path, index=False)
    data = pd.read_csv(path)
    data = data.append(content, ignore_index=True)
    data.to_csv(path, index=False)


def process():
    if not os.path.exists(os.path.join(RESULT_DIR, 'best')):
        os.mkdir(os.path.join(RESULT_DIR, 'best'))

    data = pd.read_csv('/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv')
    smiles = [s[:s.find('<')] for s in data['smile']][::2]
    Y = data['Y'].to_list()[::2]

    undersampled_step = 8
    is_generate = False
    generate_factor = 0
    generate_type = 0
    is_oversample = True
    sample_factor = 800
    modify_bit = 0
    radius = 3
    fpsize = 2048
    lr = 0.5

    global NAME
    params0 = {'learning_rate': lr, 'lambda_l1': 10, 'lambda_l2': 10,
               'bagging_fraction': 0.8, 'feature_fraction': 0.7677334484902486, 'verbose': -1,
               'max_depth': -1, 'objective': 'mse', 'num_iterations': 3000, 'n_estimators': 1000}
    for i in range(6):
        value = ['O=C(O)COC1=CC=C(C(C2=CC=C(OC)C=C2OC)NC([C@@H](NC(C3=CC=C(C=C(OC)C=C4)C4=C3)=O)CC5=CSC=C5)=O)C=C1']
        value.append(smiles[i])
        NAME = f'f78,smile_{i}'
        dataset = FPS_DataSet(undersampled_step=undersampled_step, value=value, is_generate=is_generate,
                              generate_factor=generate_factor,
                              generate_type=generate_type,
                              is_oversample=is_oversample, sample_factor=sample_factor, modify_bit=modify_bit,
                              append_smi=value, append_y=[0.9, Y[i]], fpsize=fpsize, radius=radius)
        x, y = dataset.get_train_data_set()
        X_train, Y_train, = x, y
        X_valid1, X_valid2, Y_valid1, Y_valid2 = dataset.get_valid_data_set(num=100000)
        X_test1, X_test2, Y_test1, Y_test2 = dataset.get_test_data_set(num=100000)

        train_dataset = lgb.Dataset(X_train, Y_train)
        valid_dataset1 = lgb.Dataset(X_valid1, Y_valid1)
        valid_dataset2 = lgb.Dataset(X_valid2, Y_valid2)
        test_dataset1 = lgb.Dataset(X_test1, Y_test1)
        test_dataset2 = lgb.Dataset(X_test2, Y_test2)

        model = main_modify(params0, train_dataset, valid_dataset1, valid_dataset2, test_dataset1, test_dataset2)
        train_mse, valid_mse1, valid_mse2, test_mse1, test_mse2, valid_acc, test_acc = eva(model,
                                                                                           X_train,
                                                                                           X_valid1,
                                                                                           X_valid2,
                                                                                           Y_train,
                                                                                           Y_valid1,
                                                                                           Y_valid2,
                                                                                           X_test1, X_test2,
                                                                                           Y_test1, Y_test2)

        path = os.path.join(RESULT_DIR, 'result.csv')
        print(
            f'current para   sample_factor:{sample_factor},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid loss:{valid_mse1 + valid_mse2},valid_acc:{valid_acc},test_acc{test_acc}')
        write_result({'parameters': params0,
                      'is_oversamle': is_oversample,
                      'oversample_factor': sample_factor,
                      'undersampled_step': undersampled_step,
                      'is_generate': is_generate,
                      'generate_factor': generate_factor, 'modify_bit': modify_bit, 'modify_type': generate_type,
                      'test_mse1': test_mse1, 'test_mse2': test_mse2,
                      'train_mse': train_mse,
                      'valid_mse1': valid_mse1, 'valid_mse2': valid_mse2,
                      'test_mse1': test_mse1, 'test_mse2': test_mse2,
                      'valid_acc': valid_acc, 'test_acc': test_acc,
                      'fpsize': fpsize,
                      'radius': radius,
                      'append_smi': value if value else 'None', 'tag': NAME
                      }, path=path)
    return valid_acc - valid_mse2 - valid_mse1


def optuna_params(trial: Trial):
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
    i = 4
    radius = trial.suggest_categorical('radius', [2, 3])
    fpsize = trial.suggest_categorical('fpsize', [1024, 2048])

    params = {
        # 'num_leaves': trial.suggest_intrain_high (2).csvt('num_leaves', 2, 256),
        # 'objective': 'mse',
        'max_depth': -1,
        'learning_rate': trial.suggest_uniform('learning_rate', 1e-3, 0.1),
        "boosting": 'gbdt',
        "bagging_freq": 5,
        "bagging_fraction": 0.8,
        "feature_fraction": 0.8,
        "metric": 'mse',
        "verbosity": -1,
        'n_estimators': trial.suggest_int('n_estimators', 100, 2000),
    }
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

    train_dataset = lgb.Dataset(X_train, Y_train)
    valid_dataset1 = lgb.Dataset(X_valid1, Y_valid1)
    valid_dataset2 = lgb.Dataset(X_valid2, Y_valid2)
    test_dataset1 = lgb.Dataset(X_test1, Y_test1)
    test_dataset2 = lgb.Dataset(X_test2, Y_test2)

    model = main_modify(params, train_dataset, valid_dataset1, valid_dataset2, test_dataset1, test_dataset2)
    train_mse, valid_mse1, valid_mse2, test_mse1, test_mse2, valid_acc, test_acc = eva(model,
                                                                                       X_train,
                                                                                       X_valid1,
                                                                                       X_valid2,
                                                                                       Y_train,
                                                                                       Y_valid1,
                                                                                       Y_valid2,
                                                                                       X_test1, X_test2,
                                                                                       Y_test1, Y_test2)

    path = os.path.join(RESULT_DIR, 'result.csv')
    print(
        f'current para   sample_factor:{0},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid loss:{valid_mse1 + valid_mse2},valid_acc:{valid_acc},test_acc{test_acc}')
    write_result({'parameters': params,
                  'is_oversamle': is_oversample,
                  'oversample_factor': sample_factor,
                  'undersampled_step': undersampled_step,
                  'is_generate': is_generate,
                  'generate_factor': generate_factor, 'modify_bit': modify_bit, 'modify_type': generate_type,
                  'test_mse1': test_mse1, 'test_mse2': test_mse2,
                  'train_mse': train_mse,
                  'valid_mse1': valid_mse1, 'valid_mse2': valid_mse2,
                  'test_mse1': test_mse1, 'test_mse2': test_mse2,
                  'valid_acc': valid_acc, 'test_acc': test_acc,
                  'fpsize': fpsize,
                  'radius': radius,
                  'append_smi': value, 'tag': NAME
                  }, path=path)

    return 2 * valid_acc - 2 * valid_mse2 - valid_mse1


def search():
    if not os.path.exists(os.path.join(RESULT_DIR, 'best')):
        os.mkdir(os.path.join(RESULT_DIR, 'best'))

    data = pd.read_csv('/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv')
    smiles = [s[:s.find('<')] for s in data['smile']][::2]
    smiles.append(None)
    Y = data['Y'].to_list()[::2]
    Y.append(None)
    params0 = {'learning_rate': 0.5, 'lambda_l1': 3.346471256872204e-08, 'lambda_l2': 0.16139837598406515,
               'bagging_fraction': 0.8, 'feature_fraction': 0.7677334484902486, 'verbose': -1,
               'max_depth': -1, 'objective': 'mse', 'num_iterations': 3000, 'n_estimators': 1000}
    undersampled_steps = [2, 4, 6, 8]
    is_generate = False
    generate_factor = 100
    generate_type = 0
    modify_bit = 0
    is_oversample = True
    sample_factors = [200, 400, 600, 800]
    radius = [2, 3]
    fpsizes = [1024, 2048]


    global NAME
    i = trial.suggest_int('i', 0, 6, step=1)
    value = smiles[i]
    print(i, smiles[i], Y[i])
    for sample_factor in sample_factors:
        for undersampled_step in undersampled_steps:
            for radiu in radius:
                for fpsize in fpsizes:
                    NAME = f'{undersampled_step}_{sample_factor}_{radiu}_{fpsize}'
                    dataset = FPS_DataSet(undersampled_step=undersampled_step, value=value, is_generate=is_generate,
                                          generate_factor=generate_factor,
                                          generate_type=generate_type,
                                          is_oversample=is_oversample, sample_factor=sample_factor,
                                          modify_bit=modify_bit,
                                          append_smi=value, append_y=[0.9], fpsize=fpsize, radius=radiu)

                    x, y = dataset.get_train_data_set()
                    X_train, Y_train, = x, y
                    X_valid1, X_valid2, Y_valid1, Y_valid2 = dataset.get_valid_data_set(num=100000)
                    X_test1, X_test2, Y_test1, Y_test2 = dataset.get_test_data_set(num=100000)

                    train_dataset = lgb.Dataset(X_train, Y_train)
                    valid_dataset1 = lgb.Dataset(X_valid1, Y_valid1)
                    valid_dataset2 = lgb.Dataset(X_valid2, Y_valid2)
                    test_dataset1 = lgb.Dataset(X_test1, Y_test1)
                    test_dataset2 = lgb.Dataset(X_test2, Y_test2)
                    model = main_modify(params0, train_dataset, valid_dataset1, valid_dataset2, test_dataset1,
                                        test_dataset2)
                    train_mse, valid_mse1, valid_mse2, test_mse1, test_mse2, valid_acc, test_acc = eva(model,
                                                                                                       X_train,
                                                                                                       X_valid1,
                                                                                                       X_valid2,
                                                                                                       Y_train,
                                                                                                       Y_valid1,
                                                                                                       Y_valid2,
                                                                                                       X_test1, X_test2,
                                                                                                       Y_test1, Y_test2)

                    path = os.path.join(RESULT_DIR, 'result.csv')
                    print(
                        f'current para radius:{radius},fpsize:{fpsize},sample_factor:{sample_factor},train_set:{undersampled_step},generate_factor:{generate_factor},modify_bit:{modify_bit},valid loss:{valid_mse1 + valid_mse2},valid_acc:{valid_acc},test_acc{test_acc}')
                    write_result({'parameters': params0,
                                  'is_oversamle': is_oversample,
                                  'oversample_factor': sample_factor,
                                  'undersampled_step': undersampled_step,
                                  'is_generate': is_generate,
                                  'generate_factor': generate_factor, 'modify_bit': generate_type,
                                  'modify_type': generate_type,
                                  'test_mse1': test_mse1, 'test_mse2': test_mse2,
                                  'train_mse': train_mse,
                                  'valid_mse1': valid_mse1, 'valid_mse2': valid_mse2,
                                  'test_mse1': test_mse1, 'test_mse2': test_mse2,
                                  'valid_acc': valid_acc, 'test_acc': test_acc,
                                  'fpsize': fpsize,
                                  'radius': radiu,
                                  'append_smi': value, 'tag': NAME
                                  }, path=path)


if __name__ == '__main__':
    process()
