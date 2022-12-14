import random
from fingerprint import *

def generate(smile, modify_bit, type, fp_size=2048, radius=3, is_smile=True):
    if is_smile:
        fps = np.squeeze(FPS(fp_size=fp_size, radius=radius).get_fps([smile]))
    else:
        fps = smile.copy()

    all = set(range(fp_size))
    indices = {index for index in range(fp_size) if fps[index] == 1}
    zero_indices = all.difference(indices)

    if type == 1:
        lucky = random.sample(list(zero_indices), modify_bit)
        fps[lucky] = 1
    elif type == 2:
        lucky = random.sample(list(zero_indices), modify_bit)
        fps[lucky] = 1
        unlucky = random.sample(list(indices), modify_bit)
        fps[unlucky] = 0
    return fps


if __name__ == '__main__':
    print(generate('c1ccccc1', 5, 1))
