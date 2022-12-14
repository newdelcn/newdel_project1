import warnings
from tools import *

warnings.filterwarnings('ignore')
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 设置字体
plt.rcParams["axes.unicode_minus"] = False


class Analysis():

    def __init__(self, path):
        self.data_orgin = pd.read_csv(path)
        self.data = self.data_orgin.copy()
        print(self.data.shape[0])
        self.data = self.data[(~self.data.cycle1_control_1.isin([np.nan])) & (~self.data.cycle3.isin([np.nan]))]
        print(self.data.shape[0])


    def plot_exp_EF(self):
        counter_ef = pd.cut(self.data_orgin.EF_exp_low,  # 分箱数据
                            bins=[0, 3, 6, 10, 50],  # 分箱断点
                            right=True,
                            labels=['0-3', '3-6', '6-10', '10-50']).value_counts()
        sns.countplot(pd.cut(self.data_orgin.EF_exp_low,  # 分箱数据
                             bins=[0, 3, 6, 10, 50],  # 分箱断点
                             right=True,
                             labels=['0-3', '3-6', '6-10', '10-50']))
        print('EF distribution:', counter_ef)
        plt.title('EF distribution')
        plt.xlabel('EF distribution')
        plt.show()

    def plot_exp_count(self):
        counter_ef = pd.cut(self.data_orgin.count_exp_low,  # 分箱数据
                            bins=[4, 10, 20, 40, 60],  # 分箱断点
                            right=True,
                            labels=['4-10', '10-20', '20-40', '40-70']).value_counts()
        sns.countplot(pd.cut(self.data_orgin.count_exp_low,  # 分箱数据
                             bins=[4, 10, 20, 40, 60],  # 分箱断点
                             right=True,
                             labels=['4-10', '10-20', '20-40', '40-70']))
        print('count distribution:', counter_ef)
        plt.title('count distribution')
        plt.xlabel('count')
        plt.show()

    def plot_control_1_count(self):
        counter_ef = pd.cut(self.data_orgin.count_control_1,  # 分箱数据
                            bins=[10, 20, 50, 100],  # 分箱断
                            right=True,
                            labels=['10-20', '20-50', '50-100']).value_counts()
        sns.distplot(np.clip(self.data_orgin.count_exp_low, a_min=6, a_max=73))
        plt.show()
        sns.countplot(pd.cut(self.data_orgin.count_control_1,
                             bins=[10, 20, 50, 100],
                             right=True, ))
        plt.title('count_control_1 distribution')
        print('count_control_1:', counter_ef)
        plt.show()

    def plot_Y(self):
        sns.distplot()

    def plot_EF_control_beads(self):
        sns.distplot(x=self.data_orgin.EF_control_beads, kde=True)
        plt.title('EF_control_beads distribution')
        plt.show()

        sns.countplot(pd.cut(self.data_orgin.EF_control_beads,
                             bins=[0, 20, 40, 60, 80, 100, 150, 200],
                             right=True,
                             labels=['0-20', '20-40', '40-60', '60-80', '80-100', '100-150', '150-200']))

    def plot_EF_control_protain(self):
        sns.distplot(x=self.data_orgin.EF, kde=True)
        plt.title('EF_control_protain distribution')
        plt.show()

        sns.countplot(pd.cut(self.data_orgin.EF,
                             bins=[0, 20, 40, 60, 80, 100, 150, 200],
                             right=True,
                             labels=['0-20', '20-40', '40-60', '60-80', '80-100', '100-150', '150-200']))
        plt.show()

    def plot_EF_exp_low(self):
        sns.distplot(x=self.data_orgin.EF_exp_low, kde=True)
        plt.title('EF_exp_low distribution')
        plt.show()

        sns.countplot(pd.cut(self.data_orgin.EF_exp_low,
                             bins=[0, 20, 80, 100, 150, 200, 800],
                             right=True,
                             labels=['0-20', '20-80', '80-100', '100-150', '150-200', '200-800']))

    def plot_count_tri(self):
        sns.distplot(x=self.data_orgin.count_exp_low, kde=True)
        plt.title('count distribution')
        plt.show()

    def plot_Y(self):
        sns.distplot(x=self.data_orgin.Y, kde=True)
        plt.title('Y distribution')
        plt.show()


a = Analysis('../data/train_data/TIGIT_trisython_smi_low.csv')
a.plot_exp_EF()
a.plot_exp_count()
a.plot_Y()
