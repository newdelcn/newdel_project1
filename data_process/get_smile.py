import os
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
import numpy as np
import pandas as pd
from functools import partial
from multiprocessing import Pool
import multiprocessing
import warnings

warnings.filterwarnings('ignore')
os.chdir('/home/ubuntu/project/tigit/data_process')
DATA_DIR = os.path.join('../','data','20220110')
file_list = os.listdir('../data/20220110')
cycle_list = [f for f in file_list if f.find('cycle')>-1]
cycle_data = pd.DataFrame()

for cycle in cycle_list:
    cycle_name = cycle[:cycle.find('-')]
    cycle = pd.read_excel(os.path.join(DATA_DIR,cycle),engine='openpyxl')
    cycle.loc[:,'cycle'] = cycle_name
    cycle.loc[:,'cycle_id'] = cycle[cycle_name]
    cycle.loc[:,'cycle_id'] = cycle['cycle_id'].apply(lambda x:str(x)[2:-1])
    cycle = cycle.reset_index()
    cycle = cycle[['cycle','cycle_id','Cas#']]
    cycle.dropna(subset=['Cas#'],inplace=True)
    cycle_data = pd.concat([cycle_data,cycle])

# get smile from pubChem
def find_smile(Cas_No):
    SMILE_Formula = 0
    try:
        service_args = []
        service_args.append('--load-images=no')
        service_args.append('--disk-cache=yes')
        service_args.append('--ignore-ssl-errors=true')
        driver = webdriver.PhantomJS(service_args=service_args)
        wait = WebDriverWait(driver, 30, 0.3)

        driver.get('https://pubchem.ncbi.nlm.nih.gov/#query=' + Cas_No)
        smile_path = '//*[@id="featured-results"]/div/div[2]/div/div[1]/div[2]/div[5]/div/span/span[2]/span'
        CID_path = '/html/body/div[1]/div/div/main/div[2]/div[1]/div/div[2]/div/div[1]/div[2]/div[2]/div/span/a/span/span'
        wait.until(lambda driver: driver.find_element_by_xpath(CID_path))
        wait.until(lambda driver: driver.find_element_by_xpath(smile_path))
        SMILE_Formula = driver.find_element_by_xpath(smile_path).text
        print('Smile:', SMILE_Formula)

    except TimeoutException as e:
        print('Error', Cas_No)
        with open('error.log', 'a') as fp:
            fp.write(Cas_No + '\n')
        SMILE_Formula = 0

    finally:
        driver.close()
        return SMILE_Formula

def parallelize_dataframe(df, func):
    CPUs = multiprocessing.cpu_count()
    num_partitions = CPUs
    num_cores = CPUs

    df_split = np.array_split(df, num_partitions)
    with Pool(num_cores) as pool:
        func = partial(func)
        df_part = pool.map(func, df_split)
    df = pd.concat(df_part)
    return df

def parall_func(df):
    df['smile'] = df.apply(lambda x: find_smile(x['Cas#']), axis=1)
    return df


cas = cycle_data['Cas#']
dict_ = {}
smiles = []
for c in tqdm(cas):
    if c not in dict_.keys():
        dict_[c] = find_smile(c)
    smiles.append(dict_[c])

cycle_data['smile'] = smiles
cycle_data.loc[:,'Cas#'] = cycle_data['Cas#'].str.strip()
cycle_data.to_csv('../data/train_data/cycle_smi.csv',encoding='utf-8')


