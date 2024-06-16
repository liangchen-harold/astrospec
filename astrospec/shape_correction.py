"""
@author: Harold Liang (https://lcsky.org)
"""

import cv2
import numpy as np
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse
except:
    pass
from einops import rearrange, reduce, repeat
from ellipse import LsqEllipse
from .spectrum import reduce_mean, fit_line_with_poly, frame_to_line, reconstruct
from .utils import print

def cross_points(arr, thd):
    # TODO: 施密特触发
    idxes = [
        np.argmax((arr[:-1] <= thd) & (arr[1:] > thd)),
        np.argmax((arr[:-1] >= thd) & (arr[1:] < thd)),
    ]
    ret = []
    for idx in idxes:
        a, b = arr[idx], arr[idx+1]
        # print(a, b, thd)
        ret.append(idx + (thd-a)/(b-a))
    return ret

def detect_edge_points(reader, fit, shifts=[10], verbose=0):
    lines = []
    raw_lines = []
    line_maxval = []
    for i,img in enumerate(reader):
        # line = gaussian_filter(reduce(img.astype(float), 'h w -> h', 'mean'), sigma=3)
        # print(i)
        line = frame_to_line(img, fit, shifts=shifts)
        line = line.astype(float)[0,:]
        # line = gaussian_filter(line, sigma=3)
        raw_lines.append(line)
        # 变化最快
        # line = line[:-1] - line[1:]
        # lines.append([np.argmin(line), np.argmax(line)])
        # 穿过1/4最大强度
        _min = np.min(line)
        thd_val = (np.max(line) - _min)
        line_maxval.append(thd_val)
        thd_val = _min + thd_val/4
        lines.append(cross_points(line, thd_val))
        if verbose > 3 and (i%50) == 0:
            plt.plot(line, color='r')
            plt.show()

    line_maxval = np.array(line_maxval)
    lines = np.array(lines)
    raw_lines = np.array(raw_lines)
    
    # 去除太暗的结果
    invalid = line_maxval < np.max(line_maxval) / 4
    lines[invalid,:] = np.nan

    return lines, raw_lines

def filter_out_invalid_points(x, thd):
    x = x.copy()
    # print(x.shape)
    invalid = np.zeros((x.shape[0]), dtype=bool)
    for i in range(x.shape[1]):
        ma = np.convolve(x[:, i], np.ones(3)/3, mode='same')
        invalid |= abs(x[:,i] - ma) > thd

    invalid |= abs(x[:,0] - x[:,1]) < 10

    x[invalid,:] = np.nan

    return x

def fit_ellipse(edge_points, raw_lines, verbose=0):
    points = []
    for x, ys in enumerate(edge_points):
        for y in ys:
            if not np.isnan(y):
                points.append([x, y])
    points = np.array(points)

    reg = LsqEllipse().fit(points)
    center, width, height, phi = reg.as_parameters()
    phi = np.rad2deg(phi)

    if verbose > 0:
        print(center, width, height, phi)
        
    if verbose > 1:
        # fig = plt.figure(figsize=(6, 6))
        ax = plt.subplot()
        print(raw_lines.shape)
        ax.imshow(raw_lines.T)
        
        ax.scatter(points[:,0], points[:,1], marker='x', c='r')
        ellipse = Ellipse(
            xy=center, width=2*width, height=2*height, angle=phi,
            edgecolor='b', fc='None', lw=1, label='Fit', zorder=2
        )
        ax.add_patch(ellipse)
        plt.show()

    return (center, width, height, phi)

def warp_frame(ellipse, img, sz, sun_percentage = 0.8):
    center, width, height, phi = ellipse
    
    # TODO: 旋转
    dx, dy = center
    _M = [
        # 中心移到0,0
        np.float64([
            [1, 0, -dx],
            [0, 1, -dy],
            [0, 0, 1],
        ]),
        # 椭圆转正
        np.concatenate([cv2.getRotationMatrix2D((0, 0), phi, 1), [[0,0,1]]]),
        # 椭圆缩放到圆
        np.float64([
            [height/width, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ]),
        # 转回原角度
        np.concatenate([cv2.getRotationMatrix2D((0, 0), -phi, 1), [[0,0,1]]]),
        # 缩放到目标大小
        np.float64([
            [sz*sun_percentage/(height*2), 0, 0],
            [0, sz*sun_percentage/(height*2), 0],
            [0, 0, 1],
        ]),
        # 中心移到sz/2,sz/2
        np.float64([
            [1, 0, sz/2],
            [0, 1, sz/2],
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

    img = cv2.warpAffine(img, M[:2,:], (sz, sz))
    return img
