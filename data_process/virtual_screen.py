import lightgbm as lgb
from rdkit import DataStructs
from cluster import *
import rdkit.Chem as Chem
from rdkit.Chem import Descriptors,AllChem
from data import Data
import os
import numpy as np
import pickle
from fingerprint import FPS

FP_SIZE = 2048
RESULT_DIR = '../result'
LOG_FILE = os.path.join('.', 'run.log')
FPS_DIR = f'../data/library/filter_l_5{FP_SIZE}.h5'
TRAIN_DIR = '../data/train_data/train_high.csv'


class Screen():

    def __init__(self):
        self.data = Data()
        self.x = self.data.get_mcule_library_fps()[:1000000]
        print('mcule fps shape:',len(self.x))
        self.smi = np.array(self.data.get_mcule_library_smi()['smi'][:1000000])
        self.id =  np.array(self.data.get_mcule_library_smi()['id'][:1000000])
        self.exist = []
        self.get_exist()
        print('mcule smi shale',len(self.smi))
        self.train_smi = self.data.get_train_smi()
        self.train_fps = self.data.get_train_fps()
        self.models = []
        for i in range(5):
            model = lgb.Booster(model_file=os.path.join(RESULT_DIR, f'model_re_{i}.h5'))
            self.models.append(model)
        self.get_predict_mcule()

    def get_train_top_smi(self, n_top=200):
        scores = np.zeros(self.train_fps.shape[0])
        for m in self.models:
            scores += m.predict(self.train_fps)
        scores /= 5
        sort_order = self.data.sorted_with_index(scores)
        scores_top =  np.array([i[1] for i in sort_order[:n_top]])
        print('train top score:',scores_top)
        smi = [self.train_smi[i[0]] for i in sort_order[:n_top]]

        x = [self.train_fps[i[0]] for i in sort_order[:n_top]]
        index = [[i[0]] for i in sort_order[:n_top]]

        self.predict(smi,'train top')
        with open('../data/train_data/train_smi_top.smi','wb') as fp:
            pickle.dump(index,fp)
        return smi, index

    def get_predict_mcule(self):
        scores = np.zeros(self.x.shape[0])
        for m in self.models:
            scores += m.predict(self.x)
        self.scores = scores / 5

    def get_screen_smi_top(self, n_top):
        dict_result = {k: v for k, v in zip(range(self.x.shape[0]), self.scores)}
        dict_sort = sorted(dict_result.items(), key=lambda x: x[1], reverse=True)[:n_top]
        print('mcule top scores', dict_sort)

        self.screen_smi = [self.smi[i[0]] for i in dict_sort[:n_top]]
        index = [i[0] for i in dict_sort[:n_top]]
        self.predict(self.screen_smi,'top mcule score')
        return self.screen_smi,index

    def screen_similarity_top(self, smi, index, n_top=200):
        train_top_smi, train_top_fps = self.get_train_top_smi(n_top)
        result_smi = []
        result_index = []
        result_sim_smi = []
        for index, smi in zip(index, smi):
            max = 0
            score = self.scores[index]
            fp1 = AllChem.GetMorganFingerprintAsBitVect(
                Chem.MolFromSmiles(smi),
                radius=2,
                nBits=FP_SIZE,
                useChirality=True,
            )
            for tr_smi in train_top_smi:
                fp2 = AllChem.GetMorganFingerprintAsBitVect(
                    Chem.MolFromSmiles(tr_smi),
                    radius=2,
                    nBits=FP_SIZE,
                    useChirality=True,
                )
                sim = DataStructs.TanimotoSimilarity(fp1, fp2)
                if sim > max:
                    max = sim
                    sim_smi = tr_smi
            if 0.9 > max > 0.3:
                result_smi.append(smi)
                result_index.append(index)
                result_sim_smi.append(tr_smi)
        return result_smi, result_index

    def screen_by_kmeans(self):
        kmeans_pre = Cluster().k_means()
        kmeans_label_count = set(kmeans_pre)
        kmeans_pre_en = tuple(enumerate(kmeans_pre))
        result = {}
        for lable in kmeans_label_count:
            tmp = []
            for i, pre in kmeans_pre_en:
                if pre == lable:
                    tmp.append(i)
            result[lable] = tmp

        result_smi = []
        result_indexs = []
        result_scores = []
        keys = list(result.keys())
        for lable in keys:
            l = result[lable]
            score = self.scores[l]
            index_and_score = list(zip(l, score))
            sort_result = sorted(index_and_score, key=lambda x: x[1], reverse=True)[:2]

            smi = [self.smi[index] for index, score in sort_result]
            ind = [index for index, score in sort_result]
            score = [score for index, score in sort_result]
            result_smi.extend(smi)
            result_indexs.extend(ind)
            result_scores.extend(score)

        result_sort = Data.sorted_with_index(result_scores, result_indexs)
        result_smi = [self.smi[ind] for ind, score in result_sort]
        result_indexs = [ind for ind, score in result_sort]
        return result_smi, result_indexs

    def screen_by_Murcko_Scaffold(self, smis, indexes):
        y_pre_scaffold = Cluster.Murcko_Scaffold_cluster(smis)
        result_index = []
        scaffold_screen_list = []

        for index in indexes:
            scaffold = y_pre_scaffold[index]
            if scaffold not in scaffold_screen_list:
                scaffold_screen_list.append(scaffold)
                smi = self.smi[index]
                score = self.scores[index]
                if smi in self.exist or score <= 1300:
                    continue
                result_index.append(index)
            if len(result_index) == 30:
                break
        result_smi = self.smi[result_index]
        result_id = self.id[result_index]
        self.predict(result_smi,'finaly score')
        self.save(result_smi,result_id)
        return result_smi

    def screen_by_Murcko_Scaffold_top(self):
        pass

    def process(self):
        smis, indexes = self.screen_by_kmeans()
        smis, indexes = self.screen_similarity_top(smis, indexes)
        self.screen_by_Murcko_Scaffold(smis, indexes)

    def predict(self, smis,log):
        x = FPS(fp_size=FP_SIZE).get_fps(list(smis))
        scores = np.zeros(len(x))
        for m in self.models:
            scores += m.predict(x)
        scores /= 5
        print(log,scores)

    def save(self, smis,id=None):
        writer = Chem.SDWriter('../result/screen/result.sdf')
        writer.SetProps(['LOGP', 'MW'])
        for i, smi in enumerate(smis):
            mol = Chem.MolFromSmiles(smi)
            mw = Descriptors.ExactMolWt(mol)
            logp = Descriptors.MolLogP(mol)
            mol.SetProp('MW', '%.2f' % (mw))
            mol.SetProp('LOGP', '%.2f' % (logp))
            mol.SetProp('_Name', 'No_%s' % (i))
            writer.write(mol)
        writer.close()

        with open(os.path.join(RESULT_DIR, 'screen_smi'), 'wb') as fp:
            pickle.dump(smi, fp)

    def get_exist(self):
        list_dir = os.listdir(os.path.join(RESULT_DIR,'screen'))
        for dir in list_dir:
            smi = dir[:dir.index('.')]
            self.exist.append(smi)
        print(self.exist)

screen = Screen()
screen.get_train_top_smi()
