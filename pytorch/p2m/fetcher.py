#  Copyright (C) 2019 Nanyang Wang, Yinda Zhang, Zhuwen Li, Yanwei Fu, Wei Liu, Yu-Gang Jiang, Fudan University
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import numpy as np
import pickle
import threading
import queue
import sys
from skimage import io, transform
import os


class DataFetcher(threading.Thread):

    def __init__(self, file_list, stereo=False, compute_f1=-1):
        super(DataFetcher, self).__init__()
        if stereo:
            self.work = self.work_stereo
        else:
            self.work = self.work_non_stereo
        self.stopped = False
        self.queue = queue.Queue(64)

        self.pkl_list = []
        with open(file_list, 'r+', encoding="utf-8") as f:
            while (True):
                line = f.readline().strip()
                if not line:
                    break
                if (not stereo) and os.path.isfile(line):
                    self.pkl_list.append(line)
                if stereo and all([os.path.isfile(l) for l in line.split(',')]):
                    self.pkl_list.append(line)
        np.random.shuffle(self.pkl_list)
        if compute_f1 > 0:
            self.pkl_list = self.pkl_list[:compute_f1]
        self.index = 0
        self.number = len(self.pkl_list)

    def work_non_stereo(self, idx):
        pkl_path = self.pkl_list[idx]
        label = pickle.load(open(pkl_path, 'rb'), encoding='bytes')
        img_path = pkl_path.replace('.dat', '.png')
        img = io.imread(img_path)
        img[np.where(img[:, :, 3] == 0)] = 255
        img = transform.resize(img, (224, 224))
        img = img[:, :, :3].astype('float32')

        return img, label, pkl_path.split('/')[-1]

    def work_stereo(self, idx):
        pkl_path = self.pkl_list[idx]
        label, img_1, img_2 = pkl_path.split(',')
        label = pickle.load(open(label, 'rb'), encoding='bytes')
        img = io.imread(img_1)
        img[np.where(img[:, :, 3] == 0)] = 255
        img = transform.resize(img, (224, 224))
        img_1 = img[:, :, :3].astype('float32')
        img = io.imread(img_2)
        img[np.where(img[:, :, 3] == 0)] = 255
        img = transform.resize(img, (224, 224))
        img_2 = img[:, :, :3].astype('float32')
        return img_1, img_2, label, pkl_path.split('/')[-1]

    def run(self):
        while self.index < 90000000 and not self.stopped:
            self.queue.put(self.work(self.index % self.number))
            self.index += 1
            if self.index % self.number == 0:
                np.random.shuffle(self.pkl_list)

    def fetch(self):
        if self.stopped:
            return None
        return self.queue.get()

    def shutdown(self):
        self.stopped = True
        while not self.queue.empty():
            self.queue.get()
