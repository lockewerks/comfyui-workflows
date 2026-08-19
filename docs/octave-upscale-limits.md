# Where an octave upscale ladder stops paying

An octave ladder upscales by repeating one rung: run a 4x upscale model, scale the
result back down to exactly 2x, then re-diffuse it in tiles at low denoise. The upscale
model supplies clean geometry at the new size and the diffusion pass supplies surface
detail the upscale model cannot invent. Repeat per octave.

It works, and it stops working sooner than the arithmetic suggests. This records where,
and how to tell the difference from inside the graph. Measured on an RTX 4090 24.1 GB
with `photoreal-portrait-upscale.json`, a portrait, RealVisXL V5, tiled diffusion at
1024 with 192 overlap in Mixture of Diffusers mode.

## The measured ladder

| Rung | Size | Jump | Denoise | Wall time | VRAM peak | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| Base | 1248x1824 | | 1.0 / 0.45 | 14 s | 16.9 GB | |
| Octave 1 | 2496x3648 | 2.0x | 0.35 | 109 s | 16.1 GB | pays |
| Octave 2 | 4992x7296 | 2.0x | 0.30 | 389 s | 15.4 GB | pays |
| Octave 3 | 13976x20424 | 2.8x | 0.32 | 48 min | 14.3 GB | **cut** |

Octave 3 produced a 348 MB PNG at 285 MP that was worse than the 36 MP image below it.

## Keep every rung at 2x

The third rung was originally built at 2.8x and at the *lowest* denoise in the stack,
0.28. That is backwards twice over: the widest gap got the least capacity to cross it.
Rebalancing it to 0.32 and adding a ControlNet tile anchor, which it had been missing
while both rungs below it had one, improved it and did not save it.

One refine pass at low denoise cannot cross a wide gap. It has to hold onto the
structure it was given, and a 2.8x upscale hands it structure that is already soft. The
result is mush, and mush does not recover further up the ladder.

## Why the third rung fails, and why prompting cannot fix it

An octave prompt has to name no subject. At refine scale a tile is a patch of skin, and
a prompt reading "portrait of a woman" grows a second face inside that tile. So octave
prompts are texture nouns only: pore openings, vellus hair, pigment speckle, film grain.

That works while tiles still contain structure. It stops working when they do not.

At 285 MP a 1024 tile covers about 0.5% of the frame. Most tiles hold no recognisable
structure at all: flat cheek, out-of-focus background, a patch of wall. A texture prompt
handed a tile with nothing to reinforce does not decline. It invents. The observed
failures line up with that exactly:

- Eyelashes went soft. Fine existing structure got averaged rather than sharpened.
- Skin grew mottling that was not in the source.
- Texture appeared in the bokeh, where by definition there should be none.

The prompt has no way to know a given tile is background, so no wording fixes this.
Getting past it needs per-tile conditioning: a mask or a segmentation driving different
prompts, or a much stronger structural anchor. Neither is tested here.

## The metric trap

High-frequency energy, mean absolute adjacent-pixel difference, is the obvious way to
ask whether a rung added detail. On the cut third octave, measured against the same
region of octave 2 resampled to the same size:

| Region | Octave 2 resampled | Octave 3 native | Ratio |
| --- | --- | --- | --- |
| Eye | 2.056 | 3.145 | 1.53x |
| Lips | 1.668 | 3.364 | 2.02x |
| Hairline | 2.646 | 4.743 | 1.79x |

By that number octave 3 was the most detailed rung in the stack. It was the worst one.
The metric counts invented grain as detail and cannot tell it from structure.

The ratios even contain the answer once you know what happened. The eye scored lowest,
1.53x, and the eye is where the visible damage was: soft lashes. The rung added least
where real structure already existed and most where there was nothing. That is the
signature of invention rather than refinement, and it is legible only in hindsight.

Use high-frequency energy to confirm a pass did something. Never use it to decide
whether the something was good.

## Seams, which were not a problem

Worth recording because it is the failure everyone expects from tiled diffusion and it
did not happen. Tile boundaries at 1024 with 192 overlap fall every 832 px. Sampling a
600 px band across the full width of the 285 MP image and taking the mean adjacent-column
difference:

```
stride  832: boundary energy 1.933 vs median 1.894  ->  1.02x
stride 1024: boundary energy 1.928 vs median 1.894  ->  1.02x
stride  640: boundary energy 1.932 vs median 1.894  ->  1.02x
```

1.02x across all three candidate strides, including two that are not real tile
boundaries. There is no periodic signal to find. Mixture of Diffusers with 192 px of
overlap held across 425 tiles. Overlap is the setting to leave alone.

## How to judge a rung

Crop 1:1 and crop structure. At high magnification a patch of flat cheek looks soft no
matter how good the render is, because there is nothing in it: the first two crops taken
of octave 3 landed on featureless skin and said nothing either way. Crop the eye, the
lips, the hairline. Include the region where the previous rung was already good, because
a rung that damages existing structure is the failure mode that matters and it does not
show up anywhere else.

## VRAM runs backwards

Peak VRAM falls as the image grows: 16.9 GB at the 2 MP base, 15.4 GB at 36 MP, 14.3 GB
at 285 MP. Tiled diffusion holds one batch of tiles regardless of image size, so the
octaves are flat in VRAM and only slow. The binding constraint is the un-tiled hires fix
in the base band.

The practical consequence: a card that can render the base can run every octave above
it. What stops you is wall time, and system RAM for the decoded image, not VRAM. The
285 MP rung needed roughly 7 GB of host RAM just to hold the intermediate 583 MP tensor
that the 4x upscale produced before it was scaled back down.
