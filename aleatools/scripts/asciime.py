from PIL import Image
import numpy as np
import os


def load_image( infilename ) :
    img = Image.open( infilename )
    img.load()
    data = np.asarray( img, dtype="int32" )
    return data

path = os.path.join(os.path.split(__file__)[0], "logo1.png")

data = load_image(path)

a, b = data.shape
map_ = ["  ", "..", "@@"]
for i in range(a):
    for j in range(b):
        print(map_[data[i, j]], end="")
    print("")
