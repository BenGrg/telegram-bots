import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageStat


class Ocr(object):

    def __init__(self, path_image):
        self.path = path_image
        self.start_ocr()

    def detect_bright(self):
        im = Image.open(self.path)
        stat = ImageStat.Stat(im)
        s_mean = stat.mean
        avg_stat = int(s_mean[0] + s_mean[1] + s_mean[2]) / 3
        return avg_stat

    def with_white(self, img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def with_black(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        gray, img_bin = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        gray = cv2.bitwise_not(img_bin)
        kernel = np.ones((2, 1), np.uint8)
        img = cv2.erode(gray, kernel, iterations=1)
        img = cv2.dilate(img, kernel, iterations=1)
        return img

    def start_ocr(self):
        image = cv2.imread(self.path)

        if self.detect_bright() > 128.0:
            res = self.with_white(image)
        else:
            res = self.with_black(image)

        text = pytesseract.image_to_string(res)
        return text
