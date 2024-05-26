"""
@author: Harold Liang (https://lcsky.org)
"""

# high-level api:

# filename -> float np.array: raw_file_to_raw_image
# filename -> uint8 np.array: raw_file_to_image
# filename -> filename:       raw_file_to_file

from .video_reader import video_reader
from .spectrum import reduce_mean, fit_line_with_poly, frame_to_line, reconstruct
from .shape_correction import detect_edge_points, filter_out_invalid_points, fit_ellipse, warp_frame
from .postproc import normalize, color_map
from .utils import print
import cv2
import numpy as np
from einops import rearrange, reduce, repeat

def raw_file_to_file(file, output_file, shifts = [0], color_map_name = 'orange-enhanced', verbose = 0):
    """
    raw_file_to_file 从ser文件重建图像，输出重建图像文件
    raw_file_to_file reconstruct image from raw video (ser file), write reconstructed, normalized, color mapped image to file(s)

    :param file: 输入ser文件路径 
    :param file: input file path
    :param output_file: 输出文件路径。如果shifts有多个值，可通过参数{i:02d}、{shift:02d}指定文件名
    :param output_file: output file path
    :param shifts: 波长偏移，例如：[-0.5, 0, 0.5]将输出3张偏离谱线中心指定距离的图片，单位为像素
    :param shifts: the wavelength offsets in pixels, e.g. [-0.5, 0, 0.5] returns 3 images in corresponding wavelengths
    :param color_map_name: 色彩映射，取值范围：orange-enhanced (默认), enhanced, linear (不进行任何映射)
    :param color_map_name: color map, values: orange-enhanced (default), enhanced, linear
    :param verbose: 0~3，输出调试信息
    :param verbose: 0~3，log information level
    :return: None
    """ 
    imgs = raw_file_to_raw_image(file, shifts, verbose)

    for i,img in enumerate(imgs):
        img = normalize(img).astype(int)
        img = color_map(img, color_map_name)
        if len(img.shape) == 3:
            img = img[:,:,::-1]

        _file = output_file.format(i=i, shift=shifts[i])
        if verbose > 1:
            print(f'write to {_file} (i={i}, shift={shifts[i]})')
        cv2.imwrite(_file, img)

def raw_file_to_image(file, shifts = [0], color_map_name = 'orange-enhanced', verbose = 0):
    """
    raw_file_to_image 从ser文件重建图像，返回色彩映射后的重建图像，np.array(uint8)
    raw_file_to_image reconstruct image from raw video (ser file), return the reconstructed, normalized, color mapped image, np.array(uint8)

    :param file: 输入ser文件路径 
    :param file: input file path
    :param shifts: 波长偏移，例如：[-0.5, 0, 0.5]将输出3张偏离谱线中心指定距离的图片，单位为像素
    :param shifts: the wavelength offsets in pixels, e.g. [-0.5, 0, 0.5] returns 3 images in corresponding wavelengths
    :param color_map_name: 色彩映射，取值范围：orange-enhanced (默认), enhanced, linear (不进行任何映射)
    :param color_map_name: color map, values: orange-enhanced (default), enhanced, linear
    :param verbose: 0~3，输出调试信息
    :param verbose: 0~3，log information level
    :return: 色彩映射后的重建图像，np.array(uint8)
    :return: reconstructed, normalized, color mapped image, np.array(uint8)
    """ 
    imgs = raw_file_to_raw_image(file, shifts, verbose)
    imgs = [normalize(img).astype(int) for img in imgs]
    imgs = [color_map(img, color_map_name) for img in imgs]
    return imgs

def raw_file_to_raw_image(file, shifts = [0], verbose = 0, return_details = False):
    """
    raw_file_to_raw_image 从ser文件重建图像，返回原始值空间的重建图像，np.array(float64)
    raw_file_to_raw_image reconstruct image from raw video (ser file), return the reconstructed image, np.array(float64)

    :param file: 输入ser文件路径 
    :param file: input file path
    :param shifts: 波长偏移，例如：[-0.5, 0, 0.5]将输出3张偏离谱线中心指定距离的图片，单位为像素
    :param shifts: the wavelength offsets in pixels, e.g. [-0.5, 0, 0.5] returns 3 images in corresponding wavelengths
    :param verbose: 0~3，输出调试信息
    :param verbose: 0~3，log information level
    :param return_details: 是否返回重建过程中间步骤数据
    :param return_details: whether to return data from intermediate steps
    :return: 原始值空间的重建图像，np.array(float64)
    :return: reconstructed image, np.array(float64)
    """ 
    reader = video_reader.from_file(file, auto_rotate_vertical=True)

    # 全局平均帧
    img_mean = reduce_mean(reader)
    y1, y2 = 0, reader.height
    # plt.imshow(img_mean)
    # plt.show()

    # 谱线位置拟合
    fit = fit_line_with_poly(img_mean, y1, y2, verbose = verbose)

    # 重建
    imgs = reconstruct(reader, fit, shifts = shifts)
    if verbose > 0:
        print(imgs.shape)
    if verbose > 1:
        plt.imshow(imgs[0,:,:])
        plt.show()
    
    # 椭圆拟合
    edge_points, _ = detect_edge_points(reader, fit)
    edge_points = filter_out_invalid_points(edge_points, 10)
    ellipse = fit_ellipse(edge_points, verbose=verbose)

    ret = []
    sz = imgs.shape[1]
    # 图像变换
    for i in range(imgs.shape[0]):
        img = imgs[i,:,:].copy()

        # 叠加
        group_size = max(img.shape[1] // img.shape[0], 1)
        img = img[:,:img.shape[1]//group_size*group_size]
        if verbose > 0:
            print(f'stack: shape = {img.shape}, group_size = {group_size}')
        shape = img.shape
        img = reduce(img, f'h (w {group_size}) -> h w', 'mean')
        img = cv2.resize(img, shape[::-1])

        # 图像变换
        img = warp_frame(ellipse, img, sz)
        ret.append(img)
    
    if return_details:
        return {
            'result': np.array(ret),
            'uncalib': imgs,
            'edge_points': edge_points,
            'ellipse': ellipse,
        }
    return np.array(ret)
