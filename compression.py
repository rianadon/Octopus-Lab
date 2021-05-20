CHUNK_SIZE = 4 # Found though trying a few possibilities
               # Powers of 2 are nice because each chunk can be
               # stored in a short or long int

for i in range(3):
    with open(f'frames-{i}.bin', 'rb') as f:
        print(f'-- file {i} --')
        fdata = f.read()
        print('uncompressed size', len(fdata)/1e6, 'MB')
        print('compressed size', len(gzip.compress(fdata))/1e6, 'MB')

        buf = np.frombuffer(fdata, np.uint8)
        df = np.unpackbits(buf, bitorder='little')
        df = df.reshape((-1, HEIGHT, WIDTH))
        plt.imshow(df[0])
        plt.show()

        zero_chunk = b'\x00' * (CHUNK_SIZE**2 // 8)
        last_chunks = itertools.repeat(zero_chunk)

        datas = []

        for ck in chunk_iter(df):
            ndata = []
            streak = 0
            for now, last in zip(ck, last_chunks):
                if now == last:
                    streak += 1
                    if streak > 255:
                        ndata.append(b'\xff')
                        streak -= 255
                else:
                    if streak > 0:
                        ndata.append(bytes([streak]))
                    ndata.append(b'\x00')
                    ndata.append(now)
                    streak = 0
            last_chunks = ck
            if streak > 0:
                ndata.append(bytes([streak]))
            datas.append(b''.join(ndata))

        lengths = [len(d) for d in datas]
        lengthtable = b''.join(struct.pack('<H', l) for l in lengths)
        ndata = lengthtable + b''.join(datas)
        print('new uncompressed size', len(ndata)/1e6, 'MB')
        print('new compressed size', len(gzip.compress(ndata))/1e6, 'MB')
        with open(f'frames-{i}c.bin', 'wb') as f:
            f.write(ndata)

"""Sample decompression code below

WIDTH = 400
HEIGHT = 332
BLOCKS = WIDTH*HEIGHT//16
BEGINNING = 625*2

with open(f'frames-0c.bin', 'rb') as f:
    frames = np.frombuffer(f.read(), np.uint8)

lastframe = np.zeros(BLOCKS, dtype=np.uint16)
for fno, chunks_correct in zip(range(20), chunk_iter(data_frames)):

    startl, starth = 0, 0
    for i in range(fno):
        startl += frames[i*2]
        starth += frames[i*2+1]
        #print(startl, starth, (frames[i*2+1]<<8)+frames[i*2])
    start = (starth<<8)+startl + BEGINNING
    print('start', start)
    print(frames[start:start+10])

    blockn = 0
    i = 0
    while blockn < BLOCKS:
        if frames[start + i] == 0:
            #print(frames[start+i+1 : start+i+3])
            lastframe[blockn] = frames[start + i+1] + (frames[start + i+2] << 8)
            blockn += 1
            i += 3
        else:
            #print(frames[start+i], 'skip')
            for k in range(frames[start+i]):
                blockn += 1
            i += 1

    img = np.zeros((HEIGHT, WIDTH))
    for i, block in enumerate(lastframe):
        k = 0
        while block > 0:
            if block & 1:
                x = i%(WIDTH//4)*4 + (k%4)
                y = i//(WIDTH//4)*4 + (k//4)
                img[y][x] = 255
            k += 1
            block >>= 1

    plt.figure(figsize=(5,3), dpi=100)
    plt.imshow(img)
    plt.show()

    for i, (n, c) in enumerate(zip(lastframe, chunks_correct)):
        if struct.pack('<H', n) != c:
            # Validates there are no errors
            # But there will be none! Because this code works!
            print('oops', i, struct.pack('<H', n), c)
"""
