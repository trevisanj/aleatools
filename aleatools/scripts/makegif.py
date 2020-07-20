#!/usr/bin/env python
"""
Makes animated gif with all '.png' files in current directory
"""
import glob
import imageio
import argparse
import a107

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("-d", "--duration", default=100, type=int, help="Frame duration in miliseconds")
    parser.add_argument("-b", "--backwardsbind", action="store_true", help="Repeats frames backwards to bind end of loop with beginning")
    args = parser.parse_args()
    filenames = glob.glob("*")
    filenames.sort()
    images = []
    allimages = [imageio.imread(filename) for filename in filenames]
    for image in allimages:
        images.append(image)
    if args.backwardsbind:
        for image in allimages[:0:-1]:
            images.append(image)
    outputfilename = a107.new_filename("movie", "gif")
    imageio.mimsave(outputfilename, images, duration=args.duration/1000)
    print(f"Saved '{outputfilename}")
