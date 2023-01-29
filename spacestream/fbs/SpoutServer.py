import logging
from argparse import ArgumentParser, Namespace
from typing import Optional

import SpoutGL
import cv2
import numpy as np
from OpenGL import GL

from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer


class SpoutServer(FrameBufferSharingServer):
    def __init__(
        self, sender_name: str = "SpoutSender", receiver_name: str = "SpoutReciever"
    ):
        super().__init__(sender_name)
        self.sender: Optional[SpoutGL.SpoutSender] = None
        self.reciever: Optional[SpoutGL.SpoutReciever] = None

    def setup(self):
        # setup spout
        self.sender = SpoutGL.SpoutSender()
        self.sender.setSenderName(self.sender_name)
        self.reciever = SpoutGL.SpoutReciever()
        self.reciever.set(self.sender_name)

    def send(self, frame: np.array):
        h, w = frame.shape[:2]

        success = self.sender.sendImage(frame, w, h, GL.GL_RGBA, False, 0)

        # This fixes the CPU receiver (first frame is discarded)
        # More information: https://github.com/jlai/Python-SpoutGL/issues/15
        self.sender.setCPUshare(True)

        if not success:
            logging.warning("Could not send spout image.")
            return

        # Indicate that a frame is ready to read
        self.sender.setFrameSync(self.sender_name)

    def receive(self):
        w, h = self.reciever.getSenderSize()
        frame = np.zeros((h, w, 4), dtype=np.uint8)
        self.reciever.receiveImage(frame, w, h, GL.GL_RGBA, False, 0)
        return frame

    def release(self):
        self.sender.releaseSender()
        self.reciever.releaseReceiver()

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
