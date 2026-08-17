# Fast image-to-video from a still

Animates an existing still with LTX-Video 2B. The start frame supplies the subject and
the text supplies only the motion. Reach for it when you already have an image you like
and want it to move, which is most of the time.

Ships set to 1280x704 ("720p") at 345 frames, 13.8 s, which is the longest length
verified clean at that resolution. See `docs/ltx-clip-length-limits.md` before changing
either number, because past the limit the job still reports success.

The reason the graph is shaped this way: LTX 2B in pure text-to-video has motion but no
motion control and thin concept coverage. Asked for a "brass diving helmet" it produced a
smooth featureless dome with no portholes or bolts, and asked for a slow push-in it
trucked sideways and carried the subject out of frame. Handing it a start frame removed
the identity problem completely and made camera direction land. Same model, same steps,
same seed; only the conditioning changed.

## Requires

- Checkpoint: `ltxv-2b-0.9.8-distilled.safetensors` in `models/checkpoints`
  (https://huggingface.co/Lightricks/LTX-Video, ungated, 6.34 GB)
- Text encoder: `t5xxl_fp8_e4m3fn_scaled.safetensors` in `models/text_encoders`
  (https://huggingface.co/comfyanonymous/flux_text_encoders, 5.16 GB)
- Custom nodes: ComfyUI-VideoHelperSuite, for `VHS_VideoCombine`
- A start frame in `input/`. The graph points at `helmet-start-frame.png`; swap in your
  own, cropped to the aspect you are rendering or LTX will squash it.

## Cost

Measured on an RTX 4090 24 GB, 8 steps, warm model.

At 768x512, wall time is **4.0 s fixed plus 48 ms per frame**, a fit that predicts 289
frames at 17.96 s against 17.9 s measured. Marginal cost rises with length, reaching
about 75 ms per frame by 769 frames as attention starts to matter. That is 0.53x to 0.68x
realtime. Higher resolutions cost proportionally more per frame.

VRAM peaks at **21.7 GB of 24.1 GB** while the T5 encoder is resident alongside the
transformer, then settles near 10 to 14 GB once the encoder is offloaded and sampling
begins. The 21.7 GB figure is the one that decides whether this fits your card. Clip
length barely moves it.

First run of a session costs an extra ~20 s to load the checkpoint and encoder off disk.

Output is H.264 Main, yuv420p, via libx264. Switching `Save video` to
`video/nvenc_h264-mp4` moves encoding onto the GPU and is faster; the result is still
browser-playable.

## Knobs that matter

- **`Sampler` cfg must stay 1.0.** This is a distilled checkpoint trained to run without
  classifier-free guidance. Raising cfg degrades the image instead of adding control. The
  consequence is that **the negative prompt does nothing at all**, because there is no
  unconditional pass. Do not try to fix motion by editing it.
- **`LTX sigma schedule` steps: 8.** Distilled, so this is the intended range, not a
  quality compromise.
- **`Start frame to latent` width, height and length are the risky ones.** Both axes must
  be multiples of 32, so 1280x720 and 1920x1080 are illegal; use 1280x704 and 1920x1088.
  Length must be 8n+1. Every resolution has its own maximum length and exceeding it
  produces damage with no error. Verified clean maxima: 1920x1088 at 145 frames,
  1280x704 at 345, 768x512 at 817.
- **`Motion prompt` carries everything that must persist.** The start frame anchors frame
  one and argues for nothing after it. Name the camera direction, what moves, what stays
  still, and say it continues for the whole shot. Implicit motion does not survive.
- **`LTX conditioning: 25 fps` must match `Save video` frame_rate.** Mismatch them and
  motion speed reads wrong even though nothing errors.
- `LTX sampling shift` and `LTX sigma schedule` both take the latent so the sigma curve
  adapts to clip shape. Leave those wired.

## Verify every run

A `success` status means nothing here. Run `tools/inspect_clip.sh <clip.mp4>` and read
the last frame, not the first: in image-to-video the first frame is baked in from the
start frame and is guaranteed to look right.

Mean luma catches two of the three failure modes and misses the third. Flat 16.0 is
black; a drop to the mid 80s that stays flat is mud. Melting reads as perfectly normal
luma, so you have to look.

## Known limits

Camera direction lands but precision does not. Asking for a centered push-in gives a
push-in with lateral drift, and there is no way to specify a rate or an easing curve from
text. For exact camera moves, drive the geometry elsewhere and use video-to-video.

Motion is a fixed budget rather than a rate. Doubling the length spreads the same
movement thinner instead of doubling it, so long shots read slower and eventually nearly
static. For a sequence that keeps moving, cut several short shots.

Silent. LTX-Video 2B has no audio path. Joint audio and video needs the LTX-2 22B
generation, which does not fit a 24 GB card in any usable configuration.
