import pandas as pd
import os
from tools import process_by_smi_tri
from tqdm import tqdm


TRAIN_DATA_PATH = ''

pd.set_option('max_columns',None)

class CycleData():

    def __init__(self,flag='low'):
        self.CYCLE_PATH1 = '../data/20220110/cycle 1-201805(1).xlsx'
        self.CYCLE_PATH2 = '../data/20220110/cycle 2-final(1).xlsx'
        self.CYCLE_PATH3 = '../data/20220110/cycle 3-1new(1).xlsx'

        self.trisython1 = '../data/TIGIT/t15.txt'
        self.trisython2 = '../data/TIGIT/T85.txt'
        self.trisython3 = '../data/TIGIT/T75.txt'
        self.flag = flag

    def read_data_trisython(self):
        cycle1_data = pd.read_csv(self.trisython1, sep='   ', header=None)
        cycle1_data.columns = ['count', 'EF', 'cycle1', 'cycle2', 'cycle3']
        cycle2_data = pd.read_csv(self.trisython2, sep='   ', header=None)
        cycle2_data.columns = ['count', 'EF', 'cycle1', 'cycle2', 'cycle3']
        cycle3_data = pd.read_csv(self.trisython3, sep='   ', header=None)
        cycle3_data.columns = ['count', 'EF', 'cycle1', 'cycle2', 'cycle3']

        for column in ['cycle1','cycle2','cycle3']:
            cycle1_data.loc[:,column] = cycle1_data[column].apply(lambda x:str(x))
            cycle2_data.loc[:,column] = cycle2_data[column].apply(lambda x:str(x))
            cycle3_data.loc[:,column] = cycle3_data[column].apply(lambda x:str(x))

        cycle1_data.loc[:,'cycle'] = cycle1_data.cycle1.str.cat(cycle1_data.cycle2,sep='_').str.cat(cycle1_data.cycle3,sep='_')
        cycle2_data.loc[:, 'cycle'] = cycle2_data.cycle1.str.cat(cycle2_data.cycle2, sep='_').str.cat(
            cycle2_data.cycle3, sep='_')
        cycle3_data.loc[:, 'cycle'] = cycle3_data.cycle1.str.cat(cycle3_data.cycle2, sep='_').str.cat(
            cycle3_data.cycle3, sep='_')

        all = cycle3_data.copy()
        all = pd.merge(all, cycle1_data, how='left', on='cycle', suffixes=(f'_exp_{self.flag}', '_control_1'))
        all = pd.merge(all, cycle2_data, how='left', on='cycle', suffixes=('_', '_control_2'))
        print(all.head())
        print(
            all[[f'EF_exp_{self.flag}', 'EF_control_1', 'EF', f'count_exp_{self.flag}', 'count_control_1', 'count']].describe())
        print(all.shape)
        print(all.info())

        def read_the_smile_data():
            CYCLE_DIR = os.path.join('../data/train_data/cycle_smi.csv')
            smile_data = pd.read_csv(CYCLE_DIR)
            smile_data.loc[:, 'cycle'] = smile_data['cycle'].apply(lambda x: x[-1])
            smile_data = smile_data.dropna(subset=['cycle_id'], axis=0)
            smile_data.loc[:, 'cycle_id'] = smile_data['cycle_id'].apply(lambda x: str(int(str(x).replace('A-',''))))
            return smile_data

        smile_data = read_the_smile_data()
        cycle_1 = smile_data[smile_data.cycle == '1']
        cycle_2 = smile_data[smile_data.cycle == '2']
        cycle_3 = smile_data[smile_data.cycle == '3']

        cycle_1_d = {k: v for k, v in zip(cycle_1.cycle_id, cycle_1.smile)}
        cycle_2_d = {k: v for k, v in zip(cycle_2.cycle_id, cycle_2.smile)}
        cycle_3_d = {k: v for k, v in zip(cycle_3.cycle_id, cycle_3.smile)}

        all.loc[:, 'smile1'] = all[f'cycle1_exp_{self.flag}'].apply(
            lambda x: cycle_1_d[str(x)] if str(x).strip() in cycle_1_d.keys() else 0)
        all.loc[:, 'smile2'] = all[f'cycle2_exp_{self.flag}'].apply(
            lambda x: cycle_2_d[str(x)] if str(x).strip() in cycle_2_d.keys() else 0)
        all.loc[:, 'smile3'] = all[f'cycle3_exp_{self.flag}'].apply(
            lambda x: cycle_3_d[str(x)])
        all.to_csv(f'../data/train_data/TIGIT_trisython_{self.flag}.csv', index=False)


    def react_smi(self):
        data = pd.read_csv(f'../data/train_data/TIGIT_trisython_{self.flag}.csv')
        print(data.shape)
        data = data[~(data['smile1'] == '0') & (~(data['smile2'] == '0')) & (~(data['smile3'] == '0'))]
        print(data.shape)
        smile1 = list(data['smile1'])
        smile2 = list(data['smile2'])
        smile3 = list(data['smile3'])
        smile_m_list = []
        smile_list = []
        for i in tqdm(range(len(smile1))):
            smile,smile_m =  process_by_smi_tri(smile1[i], smile2[i],smile3[i])
            smile_list.append(smile)
            smile_m_list.append(smile_m)
        data['smile'] = smile_list
        data['smile_m'] = smile_m_list
        data.to_csv(f'../data/train_data/TIGIT_trisython_smi_{self.flag}.csv', index=False)


    def cal_diff(self):
        data = pd.read_csv(f'../data/train_data/TIGIT_trisython_smi_{self.flag}.csv')
        data = data.fillna(0)
        print(data[f'count_exp_{self.flag}'].max(),data['count_control_1'].max(),data['count'].max())
        data.loc[:,'count_'] = data[f'count_exp_{self.flag}']/data[f'count_exp_{self.flag}'].max() \
                               - data['count_control_1']/data['count_control_1'].max() - data['count']/data['count'].max()
        data.loc[:,'EF_'] = data[f'EF_exp_{self.flag}']/data[f'EF_exp_{self.flag}'].max() \
                               - data['EF_control_1']/data['EF_control_1'].max() - data['EF']/data['EF'].max()
        data.loc[:,'Y'] = (4*data['count_'] + data['EF_'])/5
        data = data[~(data.smile=='0')]
        print(data.describe())
        data = data.sort_values(by=['Y'],ascending=True)
        data.to_csv(f'../data/train_data/TIGIT_trisython_smi_{self.flag}.csv', index=False)



data = CycleData()
data.read_data_trisython()
data.react_smi()
data.cal_diff()

