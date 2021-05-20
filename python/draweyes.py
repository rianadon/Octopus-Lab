import xml.etree.ElementTree as ET
import os
import re
import numpy as np
import random
from itertools import accumulate
from svg.path import *

number = re.compile(r'[a-z](?: [-\d.]+,[-\d.]+)+')

eyelid = 'M -1 -1 H 1 V 1 A 2 6 0 0 0 -1 1 Z'

def points(path):
    parsed = parse_path(path)
    points = []
    for p in parsed:
        l = p.length(error=1e-5)
        if l == 0:
            continue
        for i in range(int(l)):
            points.append(p.point(i / l))
    return points

def center(path):
    p = points(path)
    return sum(p) / len(p)

def radius(path):
    p = points(path)
    c = sum(p) / len(p)
    dist = [abs(x - c) for x in p]
    return sum(dist) / len(dist)

def maxradius(path):
    p = points(path)
    c = sum(p) / len(p)
    dist = [abs(x - c) for x in p]
    return max(dist)

def transform(path, scale, rot, translate):
    parsed = parse_path(path)
    c = center(path)

    def t(p):
        return p * scale * np.exp(rot*1j) + translate

    for p in parsed:
        p.start = t(p.start)
        p.end = t(p.end)
        if isinstance(p, CubicBezier):
            p.control1 = t(p.control1)
            p.control2 = t(p.control2)
        if isinstance(p, Arc):
            p.radius *= scale
    return parsed.d()

ET.register_namespace('','http://www.w3.org/2000/svg')
tree = ET.parse('../../art/perswebsite-v2.svg')
root = tree.getroot()

eyepaths = []
ids = []

for child in root:
    if 'id' in child.attrib and child.attrib['id'] == 'g2239':
        g = child

toremove = []
toadd = []
defs = ET.SubElement(root, 'defs')
for i, element in enumerate(g):
    path = element.get('d')
    print(element.attrib)

    for e in list(element.attrib.keys()):
        if e != 'd':
            del element.attrib[e]
    eyepaths.append(path)
    element.set('id', 'e'+str(i))
    ids.append(element.get('id'))

g.set('fill', '#e9fa00')

g2 = ET.SubElement(root, 'g')
g2.set('fill', '#000')

g3 = ET.SubElement(root, 'g')
g3.set('fill', '#000')

lids = []

for i, path in enumerate(eyepaths):
    cp = ET.SubElement(defs, 'clipPath')
    cp.set('id', ids[i]+'e')

    p = ET.SubElement(cp, 'path')
    epath = random.choice(eyepaths)

    scale = radius(path) / radius(epath)
    tx = 0.8 * (random.random()-.5)*radius(path)
    ty = 0.8 * (random.random()-.5)*radius(path)
    epath = transform(epath, 1, 0, -center(epath))
    epath = transform(epath, 0.5*scale, random.random() * 2*np.pi, 0)
    epath = transform(epath, 1, 0, center(path) + tx + ty*1j)
    p.set('d', epath)
    p.set('id', ids[i]+'p')

    use = ET.SubElement(g2, 'use')
    use.set('href', '#' + ids[i])
    use.set('clip-path', 'url(#' + ids[i] + 'e)')

    cp = ET.SubElement(defs, 'clipPath')
    cp.set('id', ids[i]+'k')

    if random.random() < 0.2:
        rotation = (random.random()-.5) * np.pi
        lidscale = maxradius(path)
        lidpath = transform(eyelid, lidscale, rotation, center(path))
        lp = ET.SubElement(cp, 'path')
        lp.set('d', lidpath)
        lp.set('id', ids[i]+'l')

        use = ET.SubElement(g3, 'use')
        use.set('href', '#' + ids[i])
        use.set('clip-path', 'url(#' + ids[i] + 'k)')
        lids.append(ids[i])

style = """
@keyframes blink {
0%, 1% {transform: translateY(-20px)}
2%, 3.5% {transform: translateY(0)}
4%, 100% {transform: translateY(-20px)}
}
@keyframes look1 {
0%, 1% {transform: translateX(0)}
1.5%, 29% {transform: translateX(-2px)}
29.5%, 100% {transform: translateX(0)}
}
@keyframes look2 {
0%, 1% {transform: translateXY(0,0)}
1.5%, 39% {transform: translateXY(-1px,2px)}
39.5%, 100% {transform: translateXY(0,0)}
}
"""

time = 15
for i in lids:
    delay = str(random.random()*time)
    style += '#'+i+'l { transform: translateY(-20px); animation: ' + str(time) + 's linear ' + delay + 's infinite blink; }\n'


time = 5
for i in ids:
    if random.random() > 0.4:
        continue
    delay = str(random.random()*time)

    anim = 'look1' if random.random() < 0.5 else 'look2'
    style += '#'+i+'p { animation: ' + str(time) + 's linear ' + delay + 's infinite ' + anim + '; }\n'

st = ET.SubElement(root, 'style')
st.text = style

tree.write('./web-out.svg')
os.system('open -a Firefox web-out.svg')
