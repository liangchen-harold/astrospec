"""
@author: Harold Liang (https://lcsky.org)
"""

import os
import argparse
from tqdm import tqdm
from glob import glob
from pathlib import Path
from astrospec import raw_file_to_file

def files_to_mp4(folder, output_folder, frame_rate=30):
    os.system(f"""
        ffmpeg -framerate {frame_rate} -pattern_type glob -i '{folder}/*.png' -c:v libx264 -pix_fmt yuv420p '{output_folder}/output.mp4' -y
    """)

def process_folder(input_folder, output_folder, color_map_name, output_video, verbose, **kwargs):
    output_path = os.path.join(input_folder, output_folder)
    os.makedirs(output_path, exist_ok=True)
    for i, file in enumerate(tqdm(sorted(glob(os.path.join(input_folder, '*.SER'))), ncols=80)):
        file_out = os.path.join(output_path, Path(file).stem + '.png')
        if os.path.isfile(file_out):
            print(f'skipped: {file}, output file exists')
            continue
        # print(i, file, file_out)
        try:
            raw_file_to_file(file, file_out, color_map_name = color_map_name, verbose = verbose)
        except Exception as e:
            print(e)
    
    if output_video:
        files_to_mp4(output_path, os.path.dirname(output_path))

def process_single_file(input_file, output_folder, color_map_name, verbose, **kwargs):
    output_path = os.path.join(os.path.dirname(input_file), output_folder)
    os.makedirs(output_path, exist_ok=True)
    file_out = os.path.join(output_path, Path(input_file).stem + '.png')
    raw_file_to_file(input_file, file_out, color_map_name = color_map_name, verbose = verbose)

def main():
    parser = argparse.ArgumentParser(description='astronomy spectroheliograph reconstruct tool')
    parser.add_argument('-i', '--input_file', help='Path to the input raw video file(.SER file)', default=None)
    parser.add_argument('-f', '--input_folder', help='Folder of the input raw video file(.SER file)', default=None)
    parser.add_argument('-o', '--output_folder', help='Output folder(relative to the input file)', default='output/img')
    parser.add_argument('-ov', '--output_video', help='Whether to generate video', action='store_true', default=False)
    parser.add_argument('-c', '--color_map_name', help='Color map', default='orange-enhanced')
    parser.add_argument('-v', '--verbose', help='verbose', default=0)
    args = parser.parse_args()
    print(vars(args))

    if args.input_file is not None:
        process_single_file(**vars(args))
    elif args.input_folder is not None:
        process_folder(**vars(args))
    else:
        parser.print_help()
        raise Exception('Neither -i (single file) nor -f (folder) was specified')

if __name__ == "__main__":
    main()
