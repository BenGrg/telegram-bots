from PIL import Image, ImageDraw, ImageFont
from sys import stdout
stdout.reconfigure(encoding="utf-16")

txt = "Trending: 1 - ROT  |  2 - BOOB  |  3 - LUCKY  |  ⬆4  - NICE  |  ⬇5  - CHILL  |  ⬇6  - KP3R |  7  - SMARTCREDIT  |  8  - BTC  |  9  - CHONK"

font_size = 60
unicode_font = ImageFont.truetype("DejaVuSans.ttf", font_size, encoding="unic")

font = unicode_font

bounding_box = [0, 0, 4700, 200]
x1, y1, x2, y2 = bounding_box  # For easy reading

img = Image.new('RGB', (x2, y2), color=(255, 255, 255))

d = ImageDraw.Draw(img)


# Calculate the width and height of the text to be drawn, given font size
w, h = d.textsize(txt, font=font)

# Calculate the mid points and offset by the upper left corner of the bounding box
x = (x2 - x1 - w)/2 + x1
y = (y2 - y1 - h)/2 + y1

# Write the text to the image, where (x,y) is the top left corner of the text
d.text((x, y), txt, align='center', font=font, fill=(0, 0, 0))

# d.text((10,10), txt, font=unicode_font, fill=(0,0,0))

img.save('img/pil_text.png')
img.show()


def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst

get_concat_v(img, img).save('img/pillow_concat_v.jpg')

if __name__ == '__main__':
    pass