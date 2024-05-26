"""
@author: Harold Liang (https://lcsky.org)
@contributors: Valerie Desnoux, Matt Considine, Andrew Smith

references:
1. SER file definition: https://free-astro.org/index.php?title=File:SER_Doc_V3b.pdf
2. https://github.com/thelondonsmiths/Solex_ser_recon_EN/blob/main/video_reader.py
"""
import numpy as np
import mmap
from .utils import print

class video_reader:
    def __init__(self, file, auto_rotate_vertical = False):
        self.f = open(file, "r+b")
        self.mm = mmap.mmap(self.f.fileno(), 0)
        self.auto_rotate_vertical = auto_rotate_vertical

    @staticmethod
    def from_file(file, *args, **kwargs):
        if file.split('.')[-1].lower() == 'ser':
            obj = video_reader_ser(file, *args, **kwargs)
        else:
            raise Exception('unsupportted input file type')
        if obj.auto_rotate_vertical:
            obj.rotate = obj._width > obj._height
        else:
            obj.rotate = False
        return obj

    @property
    def width(self):
        return self._width if not self.rotate else self._height

    @property
    def height(self):
        return self._height if not self.rotate else self._width
    
    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < self.frames:
            img = self.get_frame(self.i)
            if self.rotate:
                img = np.rot90(img)
            self.i += 1
            return img
        else:
            raise StopIteration

class video_reader_ser(video_reader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        offset = 0

        sz = 14
        self.fourcc = self.mm[offset:offset+sz]
        offset += sz
        sz = 4
        self.lu_id = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self.color_id = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self.little_endian = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self._width = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self._height = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self.depth = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz
        sz = 4
        self.frames = int.from_bytes(self.mm[offset:offset+sz], byteorder='little', signed=False)
        offset += sz

        if self.depth == 8:
            self.dtype = np.uint8
        elif self.depth == 16:
            self.dtype = np.uint16
        elif self.depth == 32:
            self.dtype = np.uint32
        else:
            raise Exception(f'unsupportted depth ({self.depth})')
        self.frame_size = self._width * self._height * self.depth // 8
        self.offset = 178

        # print(self.fourcc, self.lu_id, self.color_id, self.little_endian, self._width, self._height, self.depth, self.frames)

    def get_frame(self, i):
        offset = self.offset + i * self.frame_size
        img = np.frombuffer(self.mm[offset:offset+self.frame_size], dtype=self.dtype)
        img = np.reshape(img, (self._height, self._width))
        return img
