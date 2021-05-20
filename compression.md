# How to compress bitmap (each pixel is 0 or 1) videos

Each frame is broken down into 4px x 4px blocks. Notational note: `B(f,i)` = block `i` of frame `f`. String concatenation is ++.

| if                                                                      | emit                        |
|:------------------------------------------------------------------------|:----------------------------|
| `B(f,i)` != `B(f-1,i)` (new block)                                      | `\x00` ++ `B(f,i)`          |
| `B(f,i..j)` = `B(f-1,i..j`) and `j`-`i` ≤ 255 (consecutive same blocks) | (`j` - `i`)                 |
| `B(f,i..j)` = `B(f-1,i..j`) and 256 ≤ `j`-`i` ≤ 510                     | `\xff` ++ (`j` - `i` - 255) |
| ... etc (prepend 255s as necessary)                                     |                             |

For example, frame 1 with blocks `AAAA,AAAA,AAAA,AAAA` and frame 2 with blocks `BBBB,AAAA,AAAA,BBBB` are encoded as

    00AAAA 00AAAA 00AAAA 00AAAA 00BBBB 02 00BBBB

That looks really long, but the savings from being to encode up to 255 unchanged blocks into a single byte is incredible. The downside is every frame relies on the previous frame to be decoded, so the only efficient way to read the frames is forward. There is no rewinding, sadly.

## More info if you please

The first thing to try is to just compress the images one by one. If I want lossless, the solution is just something like Gzip (both PNG and Gzip use DEFLATE compression). Or you use lossy compressions, which leads to *many* different options, but in a bitmap image any lossy compression is going to be very visible. It's not like you can just choose a slighly browner red and hope no one sees it, because there's only two colors!

Since this is encoding a video, the other option is to run motion compression. Modern video compression (e.g. H264 or AV1) goes bananas with this; images are split into blocks of blocks of variable sizes that can be predicted by other blocks or blocks of blocks in other frames, other blocks in the frame moved along motion vectors, and that's barely just the start! So if you are waving the camera around like a buffoon it will still find a way to fit your video into an ant brain.

Eschewing all that complexity, I'm just using uniform-sized blocks (4x4 pixels to be exact), and no block nesting blocks-of-blocks super-block super-confusingness. I collect every block left-to-right and compare these blocks with the blocks of the previous frame. If block `i` is a new block (different than block `i` of previous frame), `'\x00' + block_contents[i]` are emitted (the byte zero + 2 bytes of the bits in the block). Otherwise, if blocks `i` to `j` are repeated blocks, the byte `j-i` is emitted. In case `i-j` is say, 511, `\xff\xff\x01` is emitted (all three add to 511; as many 255s as needed are prepended).

This seems very wasteful, expecially for new blocks. You're adding an extra byte for every one! That's true, but the space saved by being able to encode 255 blocks that didn't change into a single byte is *very* powerful. And efficient!
