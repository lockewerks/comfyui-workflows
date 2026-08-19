# A portrait upscaled until the skin holds up

Renders a photoreal portrait and refines it up an octave ladder: upscale 4x, scale
back down to exactly 2x, then re-diffuse the result in tiles at low denoise. Each rung
adds real surface detail rather than resampling, so what comes out has pores, vellus
hair and capillary redness instead of a smooth gradient with freckles painted on it.

Ships enabled to 2496x3648 in about two minutes. A second octave to 4992x7296, 36 MP,
is one keystroke away and costs six and a half minutes more.

Reach for it when the subject is skin. A plain ESRGAN pass on a face gives you plastic,
and that failure survives any amount of sharpening, because the detail was never there
to sharpen. The ladder itself is subject-neutral and was originally built on an interior
scene. Only the prompts are tuned for skin: replace them and keep the structure.

## Requires

- Checkpoint: `realvisxlV50_v50Bakedvae.safetensors` in `models/checkpoints`
  (https://huggingface.co/SG161222/RealVisXL_V5.0, 6.94 GB)
- Upscale model: `4xNomos8kDAT.pth` in `models/upscale_models`
  (https://openmodeldb.info/models/4x-Nomos8kDAT, 310 MB). A DAT model, not ESRGAN,
  loaded through the same `ImageUpscaleWithModel` node.
- ControlNet: `controlnet-union-sdxl-promax.safetensors` in `models/controlnet`
  (https://huggingface.co/xinsir/controlnet-union-sdxl-1.0, promax file, 2.51 GB)
- Custom nodes: [ComfyUI-TiledDiffusion](https://github.com/shiimizu/ComfyUI-TiledDiffusion),
  for `TiledDiffusion`. Tested at `a155b1b`.

## Cost

Measured on an RTX 4090 24.1 GB, warm model, seed fixed.

| Band | Output | Wall time | VRAM peak |
| --- | --- | --- | --- |
| Base render | 1248x1824, 3.1 MB | 14 s | **16.9 GB** |
| Octave 1 | 2496x3648, 11.8 MB | 109 s | 16.1 GB |
| Octave 2 | 4992x7296, 44.4 MB | 389 s | 15.4 GB |

Default state, base plus octave 1, is 123 s end to end. Everything enabled is 512 s.
Add roughly 20 s on the first run of a session to load the checkpoint off disk.

**VRAM falls as resolution rises**, which is the opposite of what the numbers look like
they should do. The octaves run through tiled diffusion, so their working set is one
batch of tiles and does not grow with the image. The base band's hires fix pass is a
single un-tiled 1248x1824 latent, and that is the binding constraint. If the base render
fits your card, every octave above it fits.

## Knobs that matter

- **`Load checkpoint` decides whether skin looks real, and it is not a free choice.**
  It feeds the base render and every octave refiner, so it sets skin character all the
  way up. Measured on one seed and one prompt: RealVisXL V5 gives pore structure and
  freckles that sit in the skin; CyberRealistic XL is punchy but waxy on the nose and
  smooth between freckles; Juggernaut XI paints freckles onto a smooth plastic gradient
  with no pore structure at all. Juggernaut is a fine general SDXL and a bad skin SDXL.
- **`Load upscale model` is Nomos8kDAT, not UltraSharp.** UltraSharpV2 has more apparent
  bite in a single pass and etches dark speckle and hard edges into skin. In a ladder
  that artifact compounds once per rung. Nomos is softer per pass and the refiners put
  the detail back.
- **Octave prompts must name no subject.** At refine scale one tile is a patch of cheek.
  A prompt reading "portrait of a woman" grows a second face inside that tile. Both
  octave prompts here are texture nouns only, and `Negative prompt: refine octaves`
  carries `duplicate face, second face, extra eye, tiling seam` for the same reason.
- **Every rung is exactly 2x.** ESRGAN 4x then `scale_by 0.5`. This is the design, not a
  coincidence: one refine pass at low denoise cannot cross a wider gap without going to
  mush, and the mush is not recoverable further up.
- **ControlNet `end_percent` is 0.8.** Guidance releases for the last 20% of steps, which
  is when the model adds detail of its own. Taking it to 1.0 locks the texture out and
  gives you a clean, sharp, empty upscale.
- **Denoise falls and ControlNet strength falls together going up**: 0.35 at 0.6, then
  0.30 at 0.45. Higher octaves need less invention because they start from more.
- **Tiles are 1024 with 192 overlap, Mixture of Diffusers.** No measurable seam: across
  425 tiles the mean adjacent-pixel difference at tile boundaries came out at 1.02x the
  median for the surrounding texture, which is undetectable. Dropping the overlap is the
  first thing that will bring seams back.

## Switching octaves on and off

Each octave is a group band. Select the band and press Ctrl+M.

**Disable from the top down and never leave a hole.** Every octave eats the previous
octave's decoded image, so muting a middle band strips the input from the band above it
and the run fails validation. Verified rather than assumed: with octave 1 muted and
octave 2 live, octave 1 drops out of the submitted prompt and octave 2's upscale node
survives with its `image` input gone.

This is a property of the ladder, not a limitation to route around. A switch node could
physically skip a middle octave, and the result would be a rung making a 4x jump at low
denoise, which is the failure the 2x spacing exists to prevent.

## Known limits

**Two octaves is the ceiling. A third goes backwards.** A 2.8x third rung to 13976x20424,
285 MP, was built, run and cut. It degraded the image: eyelashes went soft, skin grew
mottling that was not in the source, and texture appeared in the bokeh, where by
definition there should be none.

The cause is structural. At that scale a 1024 tile covers about 0.5% of the frame, so
most tiles contain nothing recognisable. The octave prompt has to be texture-only, and a
texture prompt applied to a tile with nothing to reinforce invents instead. Prompting
cannot fix it, because the prompt has no way to know a given tile is background. Adding
ControlNet tile to the rung and raising its denoise to match the wider jump did not save
it. It cost 48 minutes and produced a 348 MB PNG worse than the 36 MP one above it.

Full writeup in `docs/octave-upscale-limits.md`, including the measured ladder, the
seam numbers, and why a sharpness metric rates the worst rung the best.

**Do not let a sharpness metric arbitrate this.** High-frequency energy, mean absolute
adjacent-pixel difference, measured 1.5x to 2.0x *higher* on that third octave than on a
resampled octave 2. By that number it was the most detailed rung in the stack. It was the
worst one. The metric counts invented grain as detail. Use it to confirm a pass did
something, never to judge whether the something was good, and look at a 1:1 crop before
believing any of it.

**Judge on 1:1 crops of structure, not flat skin.** At high magnification a crop of plain
cheek is uninformative no matter how good the render is. Crop the eye, the lips and the
hairline, where there is something to get right or wrong.

**The base render is where a bad face is cheapest to fix.** Nothing above it will correct
anatomy, expression or lighting, only add surface. Mute both octaves, iterate seeds at
14 s each, and only climb the ladder once the base is worth the eight minutes.
