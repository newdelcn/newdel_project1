import functools
from rdkit.Chem.Draw import SimilarityMaps
from rdkit.Chem import AllChem
import rdkit.Chem as Chem
import numpy as np
from tqdm import tqdm
import os
import h5py
import pandas as pd

TRAIN_DIR = '../data/train_data/train_high.csv'
SMI_DIR = '../data/library/mcule_HTS_library_210206.smi'
FPS_DIR = '../data/train_data/fps'
RES_DIR = '../data/library/'


class FPS():

    def __init__(self, fpsize=2048, radius=3):
        self.fpsize = fpsize
        self.radius = radius
        self.sim_featurizer = functools.partial(SimilarityMaps.GetMorganFingerprint, radius=self.radius,
                                                   nBits=self.fpsize, useChirality=True
                                                   )

    def cal_single(self, smi, Info=False):
        try:
            if Info:
                mol = Chem.MolFromSmiles(smi)
                info = {}
                fp = np.array(
                    AllChem.GetMorganFingerprintAsBitVect(mol, radius=self.radius, nBits=self.fpsize, useChirality=True,
                                                          bitInfo=info, ), dtype='bool')
                return fp, info
            else:
                return np.array(AllChem.GetMorganFingerprintAsBitVect(Chem.MolFromSmiles(smi), radius=self.radius,
                                                                      nBits=self.fpsize, useChirality=True, ),
                                dtype='bool'), None
        except:
            print('error:', smi)
            return 0

    def get_fps(self, data, Info=False):
        x = np.zeros((len(data), self.fpsize), dtype=np.bool)
        if not isinstance(data, list):
            data = data['smile'].to_list()
        if Info:
            info_all = []
            for i, smi in enumerate(tqdm(data)):
                fps, info = self.cal_single(smi, Info=True)
                x[i, :] = fps
                info_all.append(info)
            return x, info_all
        else:
            for i, smi in enumerate(tqdm(data)):
                fps,info = self.cal_single(smi, Info=False)
                x[i, :] = fps
            return x


def main(fpsize, train_dir, save_path, radius=2, type=2):
    if type == 1:
        data = pd.read_csv(train_dir, header=None, sep='\t')
        data.columns = ['smile', 'id']
    else:
        data = pd.read_csv(train_dir)
    print(data.shape[0])

    featurizer = FPS(fpsize=fpsize, radius=radius)
    x = featurizer.get_fps(data)
    try:
        hf = h5py.File(save_path, 'w')
        hf.create_dataset('all_fps', data=x, dtype=np.bool)
        hf.close()
    except Exception as e:
        print(str(e))


if __name__ == '__main__':
    main(2048, '../data/train_data/TIGIT_trisython_smi_low.csv',
         os.path.join(FPS_DIR, 'TIGIT_trisython_smi_low_radius_3_2048.h5'), type=0, radius=3)
