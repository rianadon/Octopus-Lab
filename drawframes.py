import cv2
import numpy as np
import json
from math import ceil

with open('segments.json', 'r') as f:
    shape = json.load(f)['compile']
height, width = shape

CHUNK_SIZE = 625

kernel = np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=np.uint8)

filled = []

with open('frames-rust.bin', 'rb') as f:
    buf = np.frombuffer(f.read(), np.uint8)
    frames = buf.size // (height*width // 8)
    print(f'{frames} frames found')
    data = np.unpackbits(buf, bitorder='little')
    data = data.reshape((-1, height, width))
    for frame in data:
        frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, kernel, iterations=1)

        if len(filled) < 90:
            last = np.argmax(frame[::-1] > 0, axis=0)
            for col in range(frame.shape[1]):
                frame[frame.shape[0] - last[col] - 20:, col] = 1

        filled.append(frame)
        # comment these two lines to drastically speed up the re-saving.
        cv2.imshow('a', frame*255)
        cv2.waitKey(1)

print('writing file...')

sizes = []
for i in range(ceil(len(filled)/CHUNK_SIZE)):
    with open(f'frames-{i}.bin', 'wb') as f:
        for frame in filled[i*CHUNK_SIZE:(i+1)*CHUNK_SIZE]:
            frame = frame > 0
            sizes.append(np.where(frame)[0].size)
            packed = np.packbits(frame, 1, 'little')
            s = b''
            for row in packed:
                f.write(row.tobytes())

print('Dimensions', frame.shape)
print('Max # of points:', max(sizes))
print('            *2 =', max(sizes) * 2)
cv2.destroyAllWindows()
