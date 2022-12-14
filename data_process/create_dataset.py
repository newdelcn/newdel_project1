from fingerprint import *
import logging
from datetime import date
import os
from generate_data import generate
from sklearn.utils import shuffle


train_data_path = '/home/ubuntu/project/tigit/data/train_data/TIGIT_trisython_smi_low.csv'
train_data_fps_path = f'/home/ubuntu/project/tigit/data/train_data/fps/TIGIT_trisython_smi_low_radius_3.h5'
test_data_path = '/home/ubuntu/project/tigit/data/train_data/data_modify_20220611.csv'
log_path = f'/home/ubuntu/project/tigit/result/tmp/{date.today()}'
data_path = '/home/ubuntu/project/tigit/data/train_data'

if not os.path.exists(log_path):
    os.makedirs(log_path)

logging.basicConfig(filename=os.path.join(log_path, 'fps_data_set.log'),
                    format='%(asctime)s - %(name)s - %(levelname)s -%(module)s:  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()
KZT = logging.StreamHandler()
KZT.setLevel(logging.DEBUG)
logger.addHandler(KZT)

def return_fps_path(radius=3, fpsize=2048):
    FPS_DIR = f'/home/ubuntu/project/tigit/data/train_data/fps/TIGIT_trisython_smi_low_radius_{radius}_{fpsize}.h5'
    return FPS_DIR


def log_write(content, path=os.path.join(log_path, 'fps_data_set.log')):
    with open(path, 'a') as log:
        log.write(content)
    logging.info(content)


class FPS_DataSet():
    def __init__(self, undersampled_step, value, is_generate=1, generate_factor=20, generate_type=1, modify_bit=4,
                 generate_num=100,
                 is_oversample=0,
                 sample_factor=5,
                 append_smi=None, append_y=None, fpsize=2048, radius=3, clf=0, is_smile=False, seed=5):
        print(return_fps_path(radius=radius, fpsize=fpsize))
        np.random.seed(1024)
        print(return_fps_path(radius=radius, fpsize=fpsize))
        hf = h5py.File(return_fps_path(radius=radius, fpsize=fpsize))
        self.fps = np.array(hf['all_fps'])
        hf.close()
        self.is_smile = is_smile

        self.undersampled_step = undersampled_step
        data = pd.read_csv(train_data_path)
        tmp = data[:-10000:self.undersampled_step]
        self.data_ori = data
        self.data = pd.concat([tmp, data[-10000:]])
        self.Y = np.array(data.Y)
        self.seed = seed
        self.valid_data = pd.read_csv(test_data_path, encoding='gbk')
        if value:
            for v in [value[0]]:
                self.valid_data = self.valid_data[~(self.valid_data.smile.str.contains(v, regex=False))]
        log_write(f'valid data shape {self.valid_data.shape}\n')
        log_write(f'Loaded fingerprints from {train_data_fps_path}\n')
        log_write(f'fps_shape: {self.fps.shape}\n')

        log_write(f'Loaded fingerprints from {train_data_fps_path}\n')
        log_write(f'fps_shape: {self.fps.shape}\n')

        self.is_generate = is_generate
        self.generate_factor = generate_factor
        self.generate_type = generate_type
        self.is_oversample = is_oversample
        self.sample_factor = sample_factor
        self.modify_bit = modify_bit
        self.append_x = append_smi
        self.append_y = np.array(append_y)
        self.fpsize = fpsize
        self.radius = radius
        self.clf = clf
        indices = range(data.shape[0])
        seleted = indices[::self.undersampled_step]
        self.other = list(set(indices).difference(set(seleted)))
        self.generate_num = generate_num

    def get_train_data_set(self):
        tmp = self.fps[-10000:]
        result = self.fps[:-10000:self.undersampled_step]

        tmp_y = self.Y[-10000:]
        result_y = self.Y[:-10000:self.undersampled_step]

        self.train_X = np.concatenate((result, tmp), axis=0)
        self.train_X_ori = self.train_X.copy()

        self.train_Y = np.concatenate((result_y, tmp_y), axis=0)
        self.train_Y_ori = self.train_Y.copy()

        log_write(f'undersampled data_set,step:{self.undersampled_step}\n')
        log_write(f'undersampled data_set size:{self.train_X.shape}\n')
        log_write(f'undersampled data_set size:{self.train_Y.shape}\n')

        if self.append_x:
            append_fps = FPS(fpsize=self.fpsize, radius=self.radius).get_fps(self.append_x)
            self.train_X = np.concatenate((self.train_X, append_fps), axis=0)
            add = pd.DataFrame([[self.append_x[i], self.append_y[i]] for i in range(len(self.append_x))],
                               columns=['smile', 'Y'])
            self.data = pd.concat([self.data, add])
            self.train_X_ori = self.train_X.copy()
            self.train_Y = np.concatenate((self.train_Y, self.append_y), axis=0)
            self.train_Y_ori = self.train_Y.copy()

            log_write(f'append smile:{self.append_x}\n')
            log_write(f'after append, the size of data_set:{self.train_X.shape}\n')
            log_write(f'after append, the size of data_set:{self.data.shape}\n')
            log_write(f'after append, the size of data_set:{self.train_Y.shape}\n')

        if self.is_oversample:
            if not self.is_smile:
                for i in range(self.sample_factor):
                    self.train_X = np.append(self.train_X, self.train_X_ori[-100:], axis=0)
                    self.train_Y = np.append(self.train_Y, self.train_Y_ori[-100:], axis=0)
                log_write(f'oversample factor:{self.sample_factor}\n')
                log_write(f'oversample data_sate size:{self.train_X.shape}\n')
            else:
                self.data_re = self.data[::].copy()
                for i in range(self.sample_factor):
                    self.data_re = pd.concat([self.data_re, self.data_re[-100:]])
                log_write(f'oversample factor:{self.sample_factor}\n')
                log_write(f'oversample data_sate size:{self.data_re.shape}\n')
                return self.data_re['smile'].tolist(), self.data_re['Y'].tolist()

        self.generate_targe_Y = list(self.train_Y_ori[-self.generate_num:])
        self.generate_targe_X = list(self.train_X_ori[-self.generate_num:])

        if self.is_generate:
            self.train_X = list(self.train_X)
            self.train_Y = list(self.train_Y)
            for j in tqdm(range(len(self.generate_targe_Y))):
                for i in range(self.generate_factor):
                    gernerate_x = generate(self.generate_targe_X[j], self.modify_bit,
                                           self.generate_type, fp_size=self.fpsize, radius=self.radius,
                                           is_smile=False)
                    self.train_X.append(gernerate_x)
                    if self.clf:
                        self.train_Y.append(self.generate_targe_Y[j])
                    else:
                        self.train_Y.append(self.generate_targe_Y[j] + np.random.uniform(-0.1, 0.1))
            self.train_X = np.array(self.train_X)
            self.train_Y = np.array(self.train_Y)
            log_write(f'generate factor:{self.generate_factor}\n')
            log_write(f'generate data_sate size:{self.train_X.shape}\n')
            log_write(f'generate data_sate size:{self.train_Y.shape}\n')

        self.train_X, self.train_Y = shuffle(self.train_X, self.train_Y, random_state=0)

        return self.train_X, self.train_Y

    def get_valid_data_set(self, num=80, smile=False):
        print('other shape', len(self.other))
        self.valid_ind = list(np.random.choice(self.other, num, replace=False))

        valid_X1 = np.array(self.data_ori.loc[self.valid_ind]['smile'])
        valid_X2 = np.array(self.valid_data['smile'][::2])

        valid_Y1 = np.array(self.data_ori.loc[self.valid_ind]['Y'])
        valid_Y2 = np.array(self.valid_data['Y'][::2])

        result1 = []
        result2 = []
        for s in valid_X1:
            if s.find('<') > 0:
                s = s[:s.find('<')]
            result1.append(s)

        for s in valid_X2:
            if s.find('<') > 0:
                s = s[:s.find('<')]
            result2.append(s)

        if not smile:
            valid_X1 = FPS(fpsize=self.fpsize, radius=self.radius).get_fps(result1)
            valid_X2 = FPS(fpsize=self.fpsize, radius=self.radius).get_fps(result2)

        log_write(f'valid data_set: {valid_X1.shape},{valid_X2.shape}')
        return valid_X1, valid_X2, valid_Y1, valid_Y2

    def get_test_data_set(self, num=80, smile=False):
        other = list(set(self.other).difference(set(self.valid_ind)))
        self.test_ind = list(np.random.choice(other, num, replace=False))

        test_X1 = np.array(self.data_ori.loc[self.test_ind]['smile'])
        test_X2 = np.array(self.valid_data['smile'][1::2])
        test_Y1 = np.array(self.data_ori.loc[self.test_ind]['Y'])
        test_Y2 = np.array(self.valid_data['Y'][1::2])

        result1 = []
        result2 = []
        for s in test_X1:
            if s.find('<') > 0:
                s = s[:s.find('<')]
            result1.append(s)

        for s in test_X2:
            if s.find('<') > 0:
                s = s[:s.find('<')]
            result2.append(s)

        if not smile:
            test_X1 = FPS(fp_size=self.fpsize, radius=self.radius).get_fps(result1)
            test_X2 = FPS(fp_size=self.fpsize, radius=self.radius).get_fps(result2)

        log_write(f'test data_set: {test_X1.shape},{test_X2.shape}')
        return test_X1, test_X2, test_Y1, test_Y2


