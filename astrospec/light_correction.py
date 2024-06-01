"""
@author: Harold Liang (https://lcsky.org)
"""

import cv2
import math
from einops import rearrange, reduce, repeat
import numpy as np
from numpy.polynomial.polynomial import polyval
import matplotlib.pyplot as plt
from .utils import print

def find_center(arr):
    ret = []
    n = len(arr)//8
    a = len(arr)//2-n
    b = len(arr)//2+n
    for x in range(a, b):
        ret.append(np.sum([abs(arr[x + i] - arr[x - i]) for i in range(n)]))
    # plt.plot(ret)
    # plt.show()
    return np.argmin(ret)+a

def find_rising(arr):
    arr = arr.copy()
    for i in range(3, len(arr)//2):
        _arr = arr[:i]
        if np.count_nonzero(~np.isnan(_arr)) < 3:
            continue
        std = np.nanstd(_arr)
        mean = np.nanmean(_arr)
        # 去除离群点
        _arr[abs(_arr-mean) > std * 3] = np.nan
        if np.count_nonzero(~np.isnan(_arr)) < 3:
            continue
        # 计算去除离群点后的均值、标准差
        std = max(1, np.nanstd(_arr))
        mean = np.nanmean(_arr)
        # print(i, arr[i], mean, std, _arr[~np.isnan(_arr)])
        if arr[i] > mean + std * 6:
            return i
    raise(Exception('no rising edge detected!'))

def rotate(img, angle):
    dy, dx = img.shape
    _M = [
        # 中心移到0,0
        np.float64([
            [1, 0, -dx/2],
            [0, 1, -dy/2],
            [0, 0, 1],
        ]),
        # 椭圆转正
        np.concatenate([cv2.getRotationMatrix2D((0, 0), angle, 1), [[0,0,1]]]),
        # 中心移到dx/2,dy/2
        np.float64([
            [1, 0, dx/2],
            [0, 1, dy/2],
            [0, 0, 1],
        ]),
    ]
    # chain
    M = None
    for _m in _M:
        if M is None:
            M = _m
        else:
            M = _m @ M

    img = cv2.warpAffine(img, M[:2,:], (dx, dy))
    return img

def correct_one_axis(img, brd_percentage=0.05, verbose=0):
    h = img.shape[0]
    w = img.shape[1]
    brd_height = int(h * brd_percentage)
    brd_a = img[:brd_height, :]
    brd_a_curve_x = reduce(brd_a, 'x y -> y', np.nanmean)
    brd_a_curve_y = reduce(brd_a, 'x y -> x', np.nanmean)
    brd_b = img[-brd_height:, :]
    brd_b_curve_x = reduce(brd_b, 'x y -> y', np.nanmean)
    brd_b_curve_y = reduce(brd_b, 'x y -> x', np.nanmean)

    ca = find_rising(brd_a_curve_x)
    cb = find_rising(brd_b_curve_x)
    curve_shift = (cb-ca)
    brd_a_curve_x_unshift = brd_a_curve_x
    brd_b_curve_x_unshift = brd_b_curve_x
    brd_a_curve_x = np.roll(brd_a_curve_x, curve_shift//2)
    brd_b_curve_x = np.roll(brd_b_curve_x, -curve_shift//2)

    brd_curve_x_unshift = np.vstack([brd_a_curve_x_unshift, brd_b_curve_x_unshift])
    brd_curve_x = np.vstack([brd_a_curve_x, brd_b_curve_x])
    if verbose>1:
        plt.figure(figsize=(6*2, 3))
        ax = plt.subplot(1, 2, 1)
        # print(brd_curve_x.shape)
        plt.plot(brd_curve_x_unshift.T)
        plt.axvline(ca, c='b')
        plt.axvline(cb, c='r')
        ax = plt.subplot(1, 2, 2)
        plt.plot(brd_curve_x.T)
        plt.axvline(ca+curve_shift//2, c='b')
        plt.axvline(cb-curve_shift//2, c='r')
        plt.show()

    # y方向梯度
    # brd_a_curve_y_i = np.arange(brd_height)
    # brd_b_curve_y_i = np.arange(h-brd_height, h)
    # brd_curve_y = np.concatenate([brd_a_curve_y, brd_b_curve_y])
    # brd_curve_y_i = np.concatenate([brd_a_curve_y_i, brd_b_curve_y_i])
    # poly = np.polyfit(brd_curve_y_i, brd_curve_y, 3)
    # curve = polyval(np.arange(h), np.flip(poly))

    # plt.scatter(brd_curve_y_i, brd_curve_y)
    # plt.plot(curve)
    # plt.show()

    # 增加高度，避免旋转后无法覆盖
    _h = int(h*1.2)
    # 方法一：
    # plane = cv2.resize(brd_curve_x, (w, h), interpolation=cv2.INTER_CUBIC)
    # 方法二（速度快，依赖少）：
    plane = np.array([brd_a_curve_x*(1-y/_h) + brd_b_curve_x*(y/_h) for y in range(_h)])
    # 方法三
    # plane = np.array(
    #     [
    #         [
    #             v
    #             +(brd_b_curve_x[x]-v)*y/h
    #             # +curve[x]
    #             for y in range(h)
    #         ]
    #         for x,v in enumerate(brd_a_curve_x)
    #     ]
    # ).T

    bg_level = np.nanquantile(plane, 0.001)
    if verbose>0:
        print(f'background level: {bg_level}')
    # 边缘没有炫光的地方（背景）不受影响
    plane -= bg_level

    # 旋转
    plane = rotate(plane, math.atan2(curve_shift/2, h/2)*180/math.pi)
    # 裁切到原大小
    plane = plane[_h//2-h//2:_h//2+h//2, :]

    if verbose>2:
        # plt.figure(figsize=(8,8))
        plt.imshow(np.concatenate([brd_a, brd_b]), cmap='gray')
        plt.show()

        plt.figure(figsize=(8,8))
        plt.imshow(plane, cmap='gray')
        plt.show()

    _img = img - plane
    return _img, bg_level

def correct_light(img, brd_percentage=0.05, n_axis=2, verbose=0):
    img = img.astype(float)
    # 忽略黑边（没有扫描到的地方）
    img[img<1] = np.nan
    bg_level = 0

    try:
        img, bg_level = correct_one_axis(img, brd_percentage, verbose)
    except Exception as e:
        print(e)

    if n_axis == 2:
        try:
            img, bg_level = correct_one_axis(img.T, brd_percentage, verbose)
            img = img.T
        except Exception as e:
            print(e)

    img = np.nan_to_num(img, nan=bg_level)
    return img
