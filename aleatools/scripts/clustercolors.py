"""
Reconstructs image using only a handful of colors and saves HTML report with color codes. Based on a sklearn example.
"""
from PIL import Image
import a107
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.utils import shuffle
from time import time
import argparse
import os

def recreate_image(codebook, labels, w, h):
    d = codebook.shape[1]
    aimg = np.zeros((h, w, d))
    labelidx = 0
    for i in range(h):
        for j in range(w):
            aimg[i][j] = codebook[labels[labelidx]]
            labelidx += 1
    return aimg

def save_htmlreport(outputfilename, colors, fn0, fn1):
    with open(outputfilename, "w") as f:
        f.write(f"<h1>Color clustering</h1>\n")
        f.write(f"<h2>Before & after</h2>\n")
        f.write(f'<img src="{fn0}" width="50%"><img src="{fn1}" width="50%">\n')

        colors = [tuple(x) for x in (colors*255).astype(int)]

        # as tuple of tuples
        _s = ",\n".join([repr(x) for x in colors])
        s = f"COLORMAP_ = np.array((\n{_s}))"

        f.write(f"<h2>numpy output</h2>\n<pre>{s}</pre>\n")

        f.write("<table>\n")
        i = 0
        for color in colors:
            hexcolor = "".join([hex(int(x))[2:].rjust(2, "0") for x in color])
            f.write(f"<tr><td>{i:03d}<td style=\"background-color: #{hexcolor}; width: 50\">#{hexcolor}</td><td>#{hexcolor}</td><td>{color}</td>\n")
            i += 1
            if i == 100:
                break
        f.write("</table>\n")


def main(args):
    _, filenameonly = os.path.split(args.inputfilename)
    htmlfilename = a107.sequential_filename(f"{filenameonly}-{args.num_clusters:02d}colors", "html")
    pngfilename = a107.sequential_filename(f"{filenameonly}-{args.num_clusters:02d}colors", "png")
    img = Image.open(args.inputfilename, "r")
    aimg = np.asarray(img, dtype=np.float64) / 255
    h, w, d = originalshape = tuple(aimg.shape)
    assert d == 3
    aimg2 = np.reshape(aimg, (w * h, d))
    t0 = time()
    print("Fitting model...")
    aimg2s = shuffle(aimg2,)[:args.sample_size]
    kmeans = KMeans(n_clusters=args.num_clusters).fit(aimg2s)
    print(f"Done in {time() - t0:0.3f}s")
    t0 = time()
    print("Predicting shit")
    labels = kmeans.predict(aimg2)
    print(f"Done in {time() - t0:0.3f}s")

    save_htmlreport(htmlfilename, kmeans.cluster_centers_, args.inputfilename, pngfilename)
    print(f"Saved file '{htmlfilename}")

    t0 = time()
    print("Reconstructing image...")
    aimg4 = recreate_image(kmeans.cluster_centers_, labels, w, h)
    print(f"Done in {time() - t0:0.3f}s")
    img = Image.fromarray((aimg4 * 255).astype(np.uint8), "RGB")
    img.save(pngfilename)
    print(f"Saved file {pngfilename}")

    if args.plot:
        plot_shit(aimg, h, kmeans, labels, w, aimg4)


def plot_shit(aimg, h, kmeans, labels, w, aimg4):
    plt.subplot(1, 2, 1)
    plt.axis("off")
    plt.title("Original")
    plt.imshow(aimg)
    plt.subplot(1, 2, 2)
    plt.axis("off")
    plt.title("Reconstructed")
    plt.imshow(aimg4)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("-n", "--num-clusters", default=2, type=int, help="Number of clusters/colors")
    parser.add_argument("-s", "--sample-size", default=10000, type=int, help="Number of points in image to sample for clustering")
    parser.add_argument("-p", "--plot", action="store_true", help="Show original vs. reconstructed")
    parser.add_argument("inputfilename", help="Input filename")
    args = parser.parse_args()

    main(args)

