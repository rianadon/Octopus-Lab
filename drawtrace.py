import xml.etree.ElementTree as ET
import numpy as np
import cv2
from cairosvg import svg2png
import potrace
from rdp import rdp
import matplotlib.pyplot as plt
import json
import sys

if len(sys.argv) < 2:
    print('Usage: drawtrace.py [file]')
    print('  Optional switches are -e to edit rasterized octopus')
    print('  and -k to use rasterized octopus')
    sys.exit(1)

tree = ET.parse(sys.argv[1])
root = tree.getroot()

eyepaths = []
ids = []

# Locate layer with the octopus body
for child in root[:]:
    if 'id' not in child.attrib or child.attrib['id'] != 'Layer_1':
        root.remove(child)
    else:
        for elem in child:
            elem.set('fill', '#fff')

root.set('viewBox', "0 -16 714 593.13")
svg = ET.tostring(root)

# Save to png, then load the saved png
png = svg2png(svg, write_to=None)
nparr = np.frombuffer(png, np.uint8)
fram = cv2.imdecode(nparr, 0)

if len(sys.argv) > 2:
    if sys.argv[2] == '-e':
        cv2.imwrite('./editthis.png', fram)
        input('Press enter once you finish edtting ./editthis.png')
    if sys.argv[2] == '-e' or sys.argv[2] == '-k':
        fram = cv2.imread('./editthis.png', 0)
        print(fram)

cv2.imshow('k', fram)
fram = fram[::-1, ::-1]

# Create position mask for frame
kernel = np.ones((3, 3), np.uint8)
# erode = cv2.erode(fram, kernel, iterations=10) # python
erode = cv2.erode(fram, kernel, iterations=5)

density = 1.2 # density of points to spawn particles
erode = cv2.resize(erode, None, fx=1/density, fy=1/density)

x, y = np.where(erode > 100)
pointcoords = []
for x,y in zip(x.tolist(), y.tolist()):
    if x*density < 400:
        continue
    p0 = round(y*density - fram.shape[1]/2, 2)
    p1 = round(x*density - fram.shape[0]/2, 2)
    pointcoords.append([p0, p1])

print(len(pointcoords), 'pointcoords')
cv2.imshow('e', erode)
# cv2.waitKey(0)

# Create bitmap from the array
fram = fram > 100
bmp = potrace.Bitmap(fram)
path = bmp.trace(alphamax=0, opttolerance=1e10)

# Find the start and end position of each segment in the octopus
# Box2D wants a center, width, height, and rotation to draw boxes
# So for each segment, this computes the center and rotation
offset = (0,0)
ptanglesssss = []
for i, curve in enumerate(path):
    # x, y = curve.tesselate().T
    # plt.plot(x, y)
    # plt.show()
    points = []
    for segment in curve:
        points.append(segment.c)
        points.append(segment.end_point)
    points = np.array(points)
    if i == 0:
        offset = np.min(points[:,0]), np.min(points[:,1])
    points = points.tolist()
    points.append(points[0])
    for p in points:
        # Remove the bottom line of the octopus and save for later
        if p[0]-offset[0]<3 and p[1]-offset[1] < 3:
            pi = points.index(p)
            print('gotcha!', pi, len(points)) #, x, y)
            points = points[pi+2:] + points[:pi+1]
            print(points[0], points[-1])
            assert abs(points[0][1] - points[-1][1]) < 2
            special = [abs(points[0][0] - points[-1][0]), (points[0][0] + points[-1][0])/2-fram.shape[1]/2, points[0][1]-fram.shape[0]/2, 0]
            break

    before = len(points)
    points = rdp(points, epsilon=1)
    print(before, '-->', len(points), 'points')

    plt.plot(*np.array(points).T)

    ptangles = []
    points = np.array(points)
    for p1,p2 in zip(points, points[1:]):
        center = (p1+p2)/2
        ptangles.append([
            .1,
            np.linalg.norm(p1-p2),
            center[0],
            center[1],
            np.arctan2(p2[1]-p1[1], p2[0]-p1[0])])
    ptanglesssss.append(np.array(ptangles).round(2).tolist())

# flip everything
for p in ptanglesssss:
    for k in p:
        k[2] = fram.shape[1] - k[2]
        k[4] = -k[4] + np.pi # flip angle across y axis
special[1] *= -1
for p in pointcoords:
    p[0] *= -1

print('original', fram.shape)
width = 400
height = round(fram.shape[0] * width / fram.shape[1])
print('scaled to', [height, width])

with open('pointgen/segments.json', 'w') as f:
    json.dump({
        'segments': ptanglesssss,
        'size': fram.shape,
        'compile': [height, width],
        'special': special,
        'points': pointcoords,
    }, f)

plt.show()
