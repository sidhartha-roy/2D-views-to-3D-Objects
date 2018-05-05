#!/usr/bin/python
# -*- coding: utf-8 -*-
# 
# Developed by Haozhe Xie <cshzxie@gmail.com>
#
# References:
# - https://github.com/shawnxu1318/MVCNN-Multi-View-Convolutional-Neural-Networks/blob/master/mvcnn.py

import torch

class VGG(torch.nn.Module):
    def __init__(self, cfg):
        super(VGG, self).__init__()
        self.cfg = cfg
        self.features = self.make_layers()

    def make_layers(self):
        in_channels = self.cfg.CONST.IMG_C
        layer_cfg   = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M']
        layers      = []
        
        for index, x in enumerate(layer_cfg):
            if x == 'M':
                layers += [torch.nn.BatchNorm2d(layer_cfg[index-1]),
                           torch.nn.MaxPool2d(kernel_size=2, stride=2),
                           torch.nn.Dropout(p=0.2)]
            else:
                layers += [torch.nn.Conv2d(in_channels, x, kernel_size=3),
                           torch.nn.ELU(inplace=True)]
                in_channels = x

        return torch.nn.Sequential(*layers)

    def forward(self, x):
        return self.features(x)


class ImageEncoder(torch.nn.Module):
    def __init__(self, cfg):
        super(ImageEncoder, self).__init__()
        self.cfg = cfg

        # Layer Definition
        self.vgg = VGG(cfg)
        self.layer1 = torch.nn.Sequential(
            torch.nn.Dropout(p=0.2),
            torch.nn.Conv2d(self.cfg.CONST.N_VIEWS * 256, 512, kernel_size=1),
            torch.nn.ELU(inplace=True)
        )
        self.layer2 = torch.nn.Sequential(
            torch.nn.Conv2d(512, 256, kernel_size=3),
            torch.nn.BatchNorm2d(256),
            torch.nn.ELU(inplace=True),
            torch.nn.Dropout(p=0.2)
        )
        self.layer3 = torch.nn.Sequential(
            torch.nn.Conv2d(256, 128, kernel_size=3),
            torch.nn.BatchNorm2d(128),
            torch.nn.ELU(inplace=True),
            torch.nn.AvgPool2d(kernel_size=19)
        )

    def forward(self, x):
        # print(x.size())  # torch.Size([batch_size, n_views, img_c, img_h, img_w])
        x                  = x.permute(1, 0, 2, 3, 4).contiguous()
        rendering_images   = torch.split(x, 1, dim=0)
        rendering_features = []

        for view_idx, img in enumerate(rendering_images):
            features = self.vgg(img.view(-1, self.cfg.CONST.IMG_C, self.cfg.CONST.IMG_H, self.cfg.CONST.IMG_W))
            rendering_features.append(features)

        rendering_features = torch.cat(rendering_features, 1)
        rendering_features = self.layer1(rendering_features)
        rendering_features = self.layer2(rendering_features)
        rendering_features = self.layer3(rendering_features)

        return rendering_features.view(self.cfg.CONST.BATCH_SIZE, -1)
