from abc import ABC, abstractmethod
from sys import platform

import numpy as np
import visiongraph as vg


class FrameBufferSharingServer(vg.GraphNode, ABC):
    def __init__(self, sender_name: str, receiver_name: str):
        self.sender_name = sender_name
        self.receiver_name = receiver_name

    @abstractmethod
    def send(self, frame: np.array):
        pass

    def process(self, data: np.ndarray) -> None:
        self.send(data)

    @staticmethod
    def create(sender_name: str):
        if platform.startswith("darwin"):
            from spacestream.fbs.SyphonServer import SyphonServer
            return SyphonServer(sender_name, receiver_name)
        elif platform.startswith("win"):
            from spacestream.fbs.SpoutServer import SpoutServer
            return SpoutServer(sender_name, receiver_name)
        else:
            raise Exception(f"Platform {platform} is not supported!")
