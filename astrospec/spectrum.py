"""
@author: Harold Liang (https://lcsky.org)
@contributors: Valerie Desnoux, Jean-Francois Pittet, Jean-Baptiste Butet, Pascal Berteau, Matt Considine, Andrew Smith

references: 
1. https://github.com/thelondonsmiths/Solex_ser_recon_EN/blob/main/solex_util.py

"""

import cv2
import math
import numpy as np
try:
    import matplotlib.pyplot as plt
except:
    pass
from numpy.polynomial.polynomial import polyval
from .utils import print

def reduce_mean(reader):
    n = 0
    imgs = np.zeros((reader.height, reader.width), dtype='uint64')
    for img in reader:
        imgs += img
        n += 1
    return (imgs / n).astype('uint16')

# TODO: 自转导致的多普勒效应，会被拟合抹平，要单独拍一个天光进行曲线拟合
def fit_line_with_poly(img, y1, y2, denoise=False, verbose = 0):
    ih, iw = img.shape
    if denoise:
        blur_x = 3
        blur_y = int((y2 - y1) * 0.01)
        img = cv2.blur(img, ksize=(blur_x, blur_y))

    x_ymins_int = np.argmin(img, axis = 1)

    x_ymins = []
    # 通过左右各n_fit_pixels个点拟合
    n_fit_pixels = 2
    for y in range(y1, y2):
        x1 = max(0, x_ymins_int[y]-n_fit_pixels)
        x2 = min(iw, x_ymins_int[y]+n_fit_pixels+1)
        row = img[y, x1:x2]
        # 一元二次方程
        # print(x1, x2)
        poly = np.polyfit(np.arange(x1, x2), row, 2)
        a, b, c = poly
        # 最小值
        x_ymin = -b/(2*a)
        x_ymins.append(x_ymin)
        # print(poly, x_ymin)

        if verbose > 3 and y == (y2-y1)//2+y1:
            xx = np.arange(x1, x2, 0.1)
            # print(xx)
            curve = polyval(xx, np.flip(poly))
            plt.plot(np.arange(x1, x2), row, 'x-')
            plt.plot(xx, curve, 'g--')
            plt.axvline(x_ymin, color='r')
            # print(row)
            plt.show()

    x_ymins = np.array(x_ymins)
    filter_size = 20
    filter_threshold = 10
    inlier = np.where([abs(x-np.quantile(x_ymins[max(0, i-filter_size):i+filter_size], 0.5)) < filter_threshold for i,x in enumerate(x_ymins)])
    # print([np.abs(x-xm) < 10 for x in x_ymins])
    # print(inlier)
    if verbose > 0:
        print(f'outlier filter found {len(x_ymins)-len(inlier[0])} ({(len(x_ymins)-len(inlier[0]))/len(x_ymins)*100:.2f}%) bad points!')
    poly = np.polyfit(np.arange(y1, y2)[inlier], x_ymins[inlier], 3)
    curve = polyval(np.arange(ih), np.flip(poly))

    fit = np.array([curve[y] for y in range(ih)])
    fit = np.clip(fit, 0, iw)
    if verbose > 2:
        plt.figure(figsize=(64,64))
        s = (y2-y1)//100 + 1
        plt.imshow(img.T)
        plt.axvline(x=y1, color='r')
        plt.axvline(x=y2, color='b')
        plt.plot(np.arange(y1, y2)[inlier][::s], x_ymins[inlier][::s], 'rx', label='line detection')
        # plt.plot(np.arange(ih), curve, label='polynomial fit')
        plt.plot(np.arange(ih), fit, label='polynomial fit')
        plt.show()
        # plt.plot(curve, np.arange(ih), label='polynomial fit')
    if verbose > 3:
        plt.plot(fit, label='polynomial fit')
        plt.show()
    return fit

def frame_to_line(img, fit, shifts = [0], verbose = 0):
    ih, iw = img.shape
    lines = []
    for shift in shifts:
        fit_with_shift = fit + np.ones(ih)*shift
        idx_l = fit_with_shift.astype(int)
    
        # 防止超出图像边缘
        idx_l[idx_l < 0] = 0
        idx_l[idx_l > iw - 2] = iw - 2
        idx_r = (idx_l + np.ones(ih)).astype(int)
        
        # TODO: 亚像素偏移拟合先验分布？
        left_weights = np.ones(ih) - (fit_with_shift - fit_with_shift.astype(int))
        right_weights = np.ones(ih) - left_weights
        
        left_col = img[np.arange(ih), idx_l]
        right_col = img[np.arange(ih), idx_r]
        value = left_col * left_weights + right_col * right_weights
        lines.append(value)
    if verbose > 1:
        for line in lines:
            plt.plot(line)
        plt.show()
    return np.array(lines)

def reconstruct(reader, fit, shifts=[0]):
    imgs = []
    for img in reader:
        lines = frame_to_line(img, fit, shifts = shifts, verbose = 0)
        imgs.append(lines)
    return np.transpose(np.array(imgs), (1,2,0))
