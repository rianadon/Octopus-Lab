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
        df = np.unpackbits(buf, bitorder='little').reshape((-1, HEIGHT, WIDTH))
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
