# How long an LTX shot can be

LTX-Video has no documented maximum clip length. It has a limit you have to find by
measurement, and past it the model does not error, it quietly returns damage.

Everything here was measured on LTX-Video 2B 0.9.8 distilled, 8 steps, cfg 1.0, on an
RTX 4090 24 GB, image-to-video from a fixed start frame.

## What to do

Look up your resolution and stay at or under the clean maximum. Both axes must be
multiples of 32 and frames must be 8n+1, so 1280x720 and 1920x1080 are not legal sizes;
use 1280x704 and 1920x1088.

Then check the result before trusting it. See "verifying a run" below, because a run over
the limit reports `success`.

## Measured limits

| Resolution | Clean maximum | Duration @25fps | Degrades at | Black at |
| --- | --- | --- | --- | --- |
| 480x320 | at least 2561 frames | 102.4 s | not found | not found |
| 768x512 | 817 frames | 32.7 s | 841 (mud) | 1057 |
| 1024x576 | not bracketed | | 577 (soft) | not found |
| 1280x704 | 345 frames | 13.8 s | 385 (soft), 433 (melt) | 521 |
| 1920x1088 | 145 frames | 5.8 s | not seen | 193 |
| 2560x1440 | not bracketed | | 97 (melt) | not found |
| 3840x2176 | at least 25 frames | 1.0 s | not found | not found |

Gaps are gaps in the testing, not zeros.

## The budget: about 38,700 tokens

```
tokens = (width / 32) * (height / 32) * ((frames - 1) / 8 + 1)
```

The three bracketed clean maxima land within two percent of each other despite completely
different splits between space and time:

| Resolution | Clean max frames | Tokens |
| --- | --- | --- |
| 1280x704 | 345 | 38,720 |
| 1920x1088 | 145 | 38,760 |
| 768x512 | 817 | 39,552 |

So budget **38,700 tokens** and size clips from the formula. Divide 38,700 by
`(width/32) * (height/32)` to get latent frames, then real frames are
`(latent_frames - 1) * 8 + 1`, rounded down to 8n+1.

Getting here took a wrong turn worth recording. The budget looked refuted when 2560x1440
came back "healthy" at 46,800 tokens, but that judgement came from mean luma, which only
detects black. The frame was melted. Later 480x320 looked genuinely clean at 48,150
tokens, above the budget, and that one is still unexplained. The likely answer is that
melting is a loss of high-frequency structure and 480x320 has very little to lose, so the
damage is present and invisible at that size. Treat any apparent headroom at low
resolution with suspicion rather than as free duration.

## Failure modes

Three distinct outcomes past the limit, none of which raise an error.

**Mud.** Frame 0 is perfect and every frame after it is a flat uniform field, mean luma
around 85 to 90. Frame 0 survives because `LTXVImgToVideo` bakes the start frame into
that latent at strength 1.0, so it was never generated. Everything the model produced is
gone. Seen at 768x512 from 841 frames up.

**Black.** The whole tensor dies, including frame 0. Every frame reads mean luma 16.0,
which is video black. Seen at 768x512 from 1057 frames up. Deterministic: the same length
produced black on repeated runs.

**Melting.** Numerically alive but structurally wrong. The subject stays recognisable
while losing high-frequency detail: surfaces go soft, small features smear and drift out
of position. Mean luma stays completely normal. Seen at 2560x1440, and mildly at
1024x576 with 577 frames.

Mud and black are useless. Melting is directable, and deliberately overrunning on the
spatial axis while staying short is a usable route to abstraction.

## Verifying a run

A job that reports `success` proves nothing. It writes a valid file with the right frame
count, the right codec and the right duration whether or not there is anything in it.

Two checks, and you need both:

**Mean luma catches mud and black, and nothing else.** A healthy 768x512 clip reads
105 to 130 and drifts by under about 10 percent. A flat 16.0 is black. A drop to the
mid 80s that then stays flat is mud.

**Only looking catches melting.** Melting reads as perfectly normal luma. There is no
number for it. Extract frames and look at them.

Sample the END of the clip. The first frame is anchored by the start frame and is
guaranteed to look right, so it tells you nothing.

```
tools/inspect_clip.sh <clip.mp4> [samples] [cols]
```

That prints mean luma per sample, flags which frame is the baked-in first and which is the
last, and writes a tiled montage next to the clip so you can look at the tail.

## Time cost

At 768x512, 8 steps, warm model: roughly **4.0 s fixed plus 48 ms per frame** in the 145
to 385 frame range, rising to about 75 ms per frame by 769 frames as attention starts to
matter. That is 0.53x to 0.68x realtime, so a 30-second shot costs about 50 seconds.

Higher resolutions cost proportionally more per frame.

## Motion is a fixed budget, independent of length

Doubling the frame count does not buy twice the movement, it spreads the same movement
over twice the duration. A 385-frame push-in ends tight on the subject. The identical
prompt at 769 frames ends barely closer than it began, and at 2049 frames the camera
drifts so slowly the shot reads as locked off.

Nothing in the prompt sets the rate. If you want a long sequence that keeps moving, cut
several shorter shots instead of asking for one long one. This limit bites well before
the technical ceiling does.

## Going bigger without paying for it

Generate inside the range where the model is strong and upscale afterwards. The upscale
happens after sampling so it does not count against whatever the real limit is.

`LatentUpscaleModelLoader` feeding `LTXVLatentUpsampler` does this in latent space with
`ltxv-spatial-upscaler-0.9.8.safetensors` and `ltxv-temporal-upscaler-0.9.8.safetensors`,
about 0.5 GB each from https://huggingface.co/Lightricks/LTX-Video. The temporal
upsampler is the correct way to add frame rate. Frame interpolation does not belong in a
per-shot graph.
