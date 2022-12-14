import matplotlib.pyplot as plt
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
# from rdkit.Chem.Draw import IPythonConsole
from rdkit.Chem import Draw
from rdkit.Chem.Draw.MolDrawing import MolDrawing, DrawingOptions  # Only needed if modifying defaults
import os
import numpy as np

opts = DrawingOptions()
opts.includeAtomNumbers = True
opts.bondLineWidth = 2.8

MOL_DIR = '../data/mol_CT73'
DATA_DIR_TRAINING = '../data/20220118/AI trainning'
CYCLE_DIR = '../data/20220110/cycle_data.csv'
TRAIN_DATA_DIR = '../data/train_data'

RESULT_DIR = '../result'
pd.set_option('max_columns', None)

if not os.path.exists(MOL_DIR):
    os.makedirs(MOL_DIR)


def get_img(obj, is_smile=True):
    print(obj)
    if is_smile:
        obj = Chem.MolFromSmiles(obj)
    img = Draw.MolToImage(obj, options=opts)
    return img


def draw_2D(obj, is_smile=True):
    if is_smile:
        obj = Chem.MolFromSmiles(obj)
    img = Draw.MolToImage(obj, options=opts)
    plt.imshow(img)
    plt.show()
    return img


def draw(smis):
    mols = []
    for smi in smis:
        mol = Chem.MolFromSmiles(smi)
        mols.append(mol)
    img = Draw.MolsToGridImage(mols, molsPerRow=4, subImgSize=(200, 200), legends=['' for x in mols])
    plt.imshow(img)
    plt.show()
    return img


def transfer(smile):
    mol = Chem.MolFromSmiles(smile)
    s = Chem.MolToSmarts(mol)
    return s


def sub_research_len(smile, smarts='[C](=O)-[OH]'):
    sucrose = smile
    sucrose_mol = Chem.MolFromSmiles(sucrose)
    primary_alcohol = Chem.MolFromSmarts(smarts)
    return len(sucrose_mol.GetSubstructMatches(primary_alcohol))


def extract(obj, is_smile=True):
    patt = Chem.MolFromSmarts(
        '[#6]1:[#6]:[#6]:[#6]2:[#6](:[#6]:1)-[#6](-[#6]1:[#6]:[#6]:[#6]:[#6]:[#6]:1-2)-[#6]-[#8]-[#6](=[#8])')
    if is_smile:
        m = Chem.MolFromSmiles(obj)
        rm = Chem.DeleteSubstructs(Chem.MolFromSmiles(obj), patt)
    else:
        rm = Chem.DeleteSubstructs(obj, patt)
    return rm


def react_mol_smi(obj, smi2):
    rxn = AllChem.ReactionFromSmarts(
        '[#6]1:[#6]:[#6]:[#6]2:[#6](:[#6]:1)-[#6](-[#6]1:[#6]:[#6]:[#6]:[#6]:[#6]:1-2)-[#6]-[#8]-[#6](=[#8])-[N:3].[C:1](=[O:2])-[OD1]>>[C:1](=[O:2])[N:3]')
    reactants = (obj, Chem.MolFromSmiles(smi2))
    products = rxn.RunReactants(reactants)
    return products[0][0]


def react_smi(smi1, smi2, type=1):
    # [NH2:3].[C:1](=[O:2])-[OD1]>>[C:1](=[O:2])[NH:3]
    if type == 1:
        rxn = AllChem.ReactionFromSmarts(
            '[#6]1:[#6]:[#6]:[#6]2:[#6](:[#6]:1)-[#6](-[#6]1:[#6]:[#6]:[#6]:[#6]:[#6]:1-2)-[#6]-[#8]-[#6](=[#8])-[N:3].[C:1](=[O:2])-[OH]>>[C:1](=[O:2])[N:3]')
        reactants = (Chem.MolFromSmiles(smi1), Chem.MolFromSmiles(smi2))
        products = rxn.RunReactants(reactants)
    else:
        rxn = AllChem.ReactionFromSmarts(
            '[#6]1:[#6]:[#6]:[#6]2:[#6](:[#6]:1)-[#6](-[#6]1:[#6]:[#6]:[#6]:[#6]:[#6]:1-2)-[#6]-[#8]-[#6](=[#8])-[N:3].[N:1]=[C:2]=[S:4]>>[N:1]-[C:2](=[S:4])-[N:3]')
        reactants = (Chem.MolFromSmiles(smi1), Chem.MolFromSmiles(smi2))
        products = rxn.RunReactants(reactants)
    return products[0][0]


# get smile from pubChem
def find_smile(Cas_No):
    from selenium import webdriver
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    print('Current Cas_NO:', Cas_No)
    try:
        service_args = []
        service_args.append('--load-images=no')
        service_args.append('--disk-cache=yes')
        service_args.append('--ignore-ssl-errors=true')
        driver = webdriver.PhantomJS(service_args=service_args)
        wait = WebDriverWait(driver, 30, 0.3)

        driver.get('https://pubchem.ncbi.nlm.nih.gov/#query=' + Cas_No)
        CID_path = '/html/body/div[1]/div/div/main/div[2]/div[1]/div/div[2]/div/div[1]/div[2]/div[2]/div/span/a/span/span'
        wait.until(lambda driver: driver.find_element_by_xpath(CID_path))
        CID = driver.find_element_by_xpath(CID_path).text

        driver.get('https://pubchem.ncbi.nlm.nih.gov/compound/' + CID)

        SMILE_Formula_path = '//*[@id="Canonical-SMILES"]/div[2]/div[1]/p'
        wait.until(lambda driver: driver.find_element_by_xpath(SMILE_Formula_path))
        SMILE_Formula = driver.find_element_by_xpath(SMILE_Formula_path).text

    except TimeoutException as e:
        print('Error', Cas_No)
        with open('error.log', 'a') as fp:
            fp.write(Cas_No + '\n')
        SMILE_Formula = 0
    finally:
        print('Smile:', SMILE_Formula)
        driver.close()
        return SMILE_Formula


def process_by_cas_disython(cas1, cas2):
    smi1 = find_smile(cas1)
    smi2 = find_smile(cas2)

    draw_2D(smi1)
    draw_2D(smi2)

    pic1 = get_img(smi1)
    pic2 = get_img(smi2)

    mol1 = extract(smi1, True)

    result = react_mol_smi(mol1, smi2)
    result_end = extract(result, False)
    smi = Chem.MolToSmiles(result_end)
    pic3 = get_img(smi)
    print("smi", smi)
    return smi, pic1, pic2, pic3


def process_by_smi(smi1, smi2, is_draw=False):
    if is_draw:
        draw_2D(smi1)
        draw_2D(smi2)
    print('smile 1 :', smi1)
    print('smile 2 :', smi2)

    try:
        if sub_research_len(smi2) == 1:
            result = react_smi(smi1, smi2, type=1)
            result_end = extract(result, False)
            smi = Chem.MolToSmiles(result_end)
        else:
            result = react_smi(smi1, smi2, type=0)
            draw_2D(result, False)
            result_end = extract(result, False)
            smi = Chem.MolToSmiles(result_end)
            draw_2D(smi)
    except:
        return 0
    print("smi", smi)
    if is_draw:
        draw_2D(result_end, False)
    return smi


def process_by_smi_tri(smi1, smi2, smi3, is_draw=False):
    if is_draw:
        draw_2D(smi1)
        draw_2D(smi2)
        draw_2D(smi3)

    smi_m = 0
    try:
        if sub_research_len(smi3) == 1:
            result = react_smi(smi1, smi2, type=1)
            if is_draw:
                draw_2D(result, False)
            smi_m = Chem.MolToSmiles(result)
            result = react_smi(smi_m, smi3, type=1)
            if is_draw:
                draw_2D(result, False)
            smi = Chem.MolToSmiles(result)
        else:
            result = react_smi(smi1, smi2, type=1)
            smi_m = Chem.MolToSmiles(result)
            if is_draw:
                draw_2D(smi_m)
            result = react_smi(smi_m, smi3, type=0)
            smi = Chem.MolToSmiles(result)

    except Exception as e:
        print(e)
        return 0, smi_m

    if is_draw:
        draw_2D(result, False)
    return smi, smi_m


def get_react_data_high(cycle1, cycle2):
    print('current cycle:', cycle1, cycle2)

    def read_the_smile_data():
        CYCLE_DIR = os.path.join('../data/train_data/cycle.csv')
        smile_data = pd.read_csv(CYCLE_DIR)
        smile_data.loc[:, 'cycle'] = smile_data['cycle'].apply(lambda x: x[-1])
        smile_data = smile_data.dropna(subset=['cycle_id'], axis=0)
        smile_data.loc[:, 'cycle_id'] = smile_data['cycle_id'].apply(lambda x: str(int(x)))
        return smile_data

    smile_data = read_the_smile_data()

    cycle_1 = smile_data[smile_data.cycle == cycle1]
    cycle_2 = smile_data[smile_data.cycle == cycle2]

    cycle_1_d = {k: v for k, v in zip(cycle_1.cycle_id, cycle_1.smile)}
    cycle_2_d = {k: v for k, v in zip(cycle_2.cycle_id, cycle_2.smile)}

    beads_control_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'beads control-{cycle1}{cycle2}.rs'))
    high_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'high con protein{cycle1}{cycle2}.rs'))
    low_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'low con protein{cycle1}{cycle2}.rs'))
    protein_control_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'protein control-{cycle1}{cycle2}.rs'))

    assert np.all(beads_control_data.CodeA == high_data.CodeA)
    assert np.all(beads_control_data.CodeA == protein_control_data.CodeA)

    result = high_data.copy()
    result.loc[:, 'count_beads'] = beads_control_data.S1
    result.loc[:, 'count_protain'] = protein_control_data.S1
    result.loc[:, 'cycle'] = f'{cycle1}+{cycle2}'

    result.loc[:, 'smile1'] = result.apply(
        lambda x: cycle_1_d[str(x['CodeA'])] if str(x['CodeA']) in cycle_1_d.keys() else 0, axis=1)
    result.loc[:, 'smile2'] = result.apply(
        lambda x: cycle_2_d[str(x['CodeB'])] if str(x['CodeB']) in cycle_2_d.keys() else 0, axis=1)
    result = result[(result['smile1'] != '0') & (result['smile2'] != '0')].reset_index()
    result.loc[:, 'smile'] = result.apply(
        lambda x: process_by_smi(x['smile1'], x['smile2']) if x['smile1'] != 0 and x['smile2'] != 0 else 0, axis=1)
    print(result)

    if not os.path.exists(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}')):
        os.mkdir(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}'))
    result.to_csv(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}', 'smi_high.csv'))
    return result


def get_react_data_low(cycle1, cycle2):
    print('current cycle:', cycle1, cycle2)

    def read_the_smile_data():
        CYCLE_DIR = os.path.join('../data/train_data/cycle.csv')
        smile_data = pd.read_csv(CYCLE_DIR)
        smile_data.loc[:, 'cycle'] = smile_data['cycle'].apply(lambda x: x[-1])
        smile_data = smile_data.dropna(subset=['cycle_id'], axis=0)
        smile_data.loc[:, 'cycle_id'] = smile_data['cycle_id'].apply(lambda x: str(int(x)))
        return smile_data

    smile_data = read_the_smile_data()

    cycle_1 = smile_data[smile_data.cycle == cycle1]
    cycle_2 = smile_data[smile_data.cycle == cycle2]

    cycle_1_d = {k: v for k, v in zip(cycle_1.cycle_id, cycle_1.smile)}
    cycle_2_d = {k: v for k, v in zip(cycle_2.cycle_id, cycle_2.smile)}

    beads_control_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'beads control-{cycle1}{cycle2}.rs'))
    high_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'high con protein{cycle1}{cycle2}.rs'))
    low_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'low con protein{cycle1}{cycle2}.rs'))
    protein_control_data = pd.read_csv(
        os.path.join(DATA_DIR_TRAINING, f'{cycle1}+{cycle2}', f'protein control-{cycle1}{cycle2}.rs'))

    assert np.all(beads_control_data.CodeA == high_data.CodeA)
    assert np.all(beads_control_data.CodeA == protein_control_data.CodeA)

    result = low_data.copy()
    result.loc[:, 'count_beads'] = beads_control_data.S1
    result.loc[:, 'count_protain'] = protein_control_data.S1
    result.loc[:, 'smile1'] = result.apply(
        lambda x: cycle_1_d[str(x['CodeA'])] if str(x['CodeA']) in cycle_1_d.keys() else 0, axis=1)
    result.loc[:, 'smile2'] = result.apply(
        lambda x: cycle_2_d[str(x['CodeB'])] if str(x['CodeB']) in cycle_2_d.keys() else 0, axis=1)
    result = result[(result['smile1'] != '0') & (result['smile2'] != '0')].reset_index()
    result.loc[:, 'smile'] = result.apply(
        lambda x: process_by_smi(x['smile1'], x['smile2']) if x['smile1'] != 0 and x['smile2'] != 0 else 0, axis=1)
    print(result)


    if not os.path.exists(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}')):
        os.mkdir(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}'))
    result.to_csv(os.path.join(DATA_DIR_TRAINING, 'smi', f'{cycle1}+{cycle2}', 'smi_low.csv'))
    return result


def extract_EF(name):
    result = pd.read_csv(os.path.join(TRAIN_DATA_DIR, f'data_{name}.csv'))
    result.loc[:, 'count_norm_beads_control'] = result.count_beads / result.count_beads.sum() * 1e+8
    result.loc[:, f'count_norm_{name}'] = result.S1 / result.S1.sum() * 1e+8
    result.loc[:, 'count_norm_pro_control'] = result.count_protain / result.count_protain.sum() * 1e+8

    for idx, row in result.iterrows():
        if result.iloc[idx]['count_norm_beads_control'] == 0 or result.iloc[idx]['count_norm_pro_control'] == 0:
            if result.loc[idx, f'count_norm_{name}'] == 0:
                result.loc[idx, 'EF'] = 0
            else:
                result.loc[idx, 'EF'] = result.loc[idx, f'count_norm_{name}'] * 8
        else:
            result.loc[idx, 'EF'] = result.loc[idx, f'count_norm_{name}'] / result.loc[
                idx, 'count_norm_beads_control'] * result.loc[idx, f'count_norm_{name}'] / result.loc[
                                        idx, 'count_norm_pro_control']

    result = result[~result.smile.isin(['0', 0])]
    result.reset_index(inplace=True)
    result = result[['CodeA', 'CodeB', 'smile1', 'smile2', 'smile', f'count_norm_{name}', 'count_norm_beads_control',
                     'count_norm_pro_control', 'S1', 'count_beads', 'count_protain', 'EF', 'cycle']]
    result = result.sort_values(by=['EF'])
    result.to_csv(os.path.join(TRAIN_DATA_DIR, f'train_{name}.csv'))
    return result
