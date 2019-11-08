"""
Makes animated gif with all '.png' files in current directory
"""
import glob
import imageio
import argparse
import a107

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    args = parser.parse_args()
    filenames = glob.glob("*.png")
    images = []
    for filename in filenames:
        images.append(imageio.imread(filename))
    outputfilename = a107.new_filename("movie", "gif")
    imageio.mimsave(outputfilename, images)
    print(f"Saved '{outputfilename}")
