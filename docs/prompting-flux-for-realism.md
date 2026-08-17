# Getting photographic realism out of Flux

Notes from producing a hard science fiction space scene with `flux1-dev-fp8`. The subject
was a spacecraft, but nothing here is specific to spacecraft: it is about beating a
model's genre prior when you want a photograph and the genre wants an illustration.

## The problem

Asking for "a large deep-space vessel with white thermal panels, an exposed aluminium
truss spine, gold multi-layer insulation blankets and flat black radiator arrays, harsh
unfiltered sunlight, pitch-black shadows with no fill" produced a streamlined white space
yacht with a windshield, soft warm light, fill on the shadow side, a bloom wash, and
gibberish lettering on the hull. Every realism marker in the prompt was dropped.

This is the fixed attention budget problem. The prompt asked for three material types, a
lighting condition, a planet, stars and a lens. The model satisfied the easy, high-prior
parts (big ship, planet, stars, cinematic) and discarded the specific ones. Adding more
words about realism just rotates which requirement loses.

## What actually worked

### Genre nouns pull toward concept art. Replace them.

"Vessel" and "spaceship" carry a strong illustration prior. Engineering and photography
nouns do not. Swapping to "documentary photograph", "pressure module", "orbital station",
"truss", "radiator panel" moved the output from concept art toward hardware in one step,
with no other change.

### Structural negations are obeyed. Optical negations are ignored.

This was the single most useful finding and it is not obvious.

| Negation | Result |
| --- | --- |
| "no windshield, no wings, no windows" | obeyed, they disappeared |
| "boxy and unstreamlined" | obeyed |
| "no lens flare, no bloom, no glow" | **ignored**, bloom appeared anyway |
| "no fill light at all" | **ignored**, shadow sides stayed lit |

The fix is to convert an optical negation into a structural one. Instead of asking for no
bloom, remove the cause: **"the sun is off frame to the left and out of shot."** Instead of
asking for no fill, state the result positively: **"the shadowed side of the hull is solid
black."** Both landed where the negations had failed.

Do not spend words telling the model what an image should not look like. Spend them on
what is and is not present in the scene.

### Tighter framing buys realism

A detail shot of a truss joint, cable runs and creased foil came out dramatically more
photographic than any full-ship composition, on the same model, prompt style and seed
range. A close shot gives the genre prior almost nothing to grab, so the model spends its
capacity rendering materials, which it is very good at.

The usable middle is a mid shot with the subject filling roughly two thirds of frame.
Enough scene to be a scene, tight enough that the illustration prior does not take over.

### It is seed-dependent, so generate several

The off-frame sun constraint worked on one seed out of three. The other two put the sun
back in frame with a bloom despite identical wording. Treat these techniques as strong
levers rather than guarantees: run three or four seeds and keep the one where the
constraint landed. Hold the seed fixed only when the prompt is the variable you are
testing.

## Mechanics

`flux1-dev-fp8.safetensors` is a 17 GB all-in-one checkpoint carrying model, text encoder
and VAE, so `CheckpointLoaderSimple` gives all three and there is no loader juggling.

**Flux is guidance-distilled, so there is no negative prompt.** The graph uses
`BasicGuider`, which takes only a model and one conditioning, feeding
`SamplerCustomAdvanced`. If you reach for `CFGGuider` or `KSampler` you will be asked for a
negative that does nothing. Guidance is set with `FluxGuidance` on the conditioning
instead; 3.0 to 3.5 suits photoreal, and higher gets glossier.

Flux 1 uses `BasicScheduler` with `simple`, and `EmptySD3LatentImage` rather than
`EmptyLatentImage`, because its latents are 16 channel.

**Flux 2 does not fit a 24 GB card.** `flux2_dev_fp8mixed.safetensors` is 34 GB and its
`mistral_3_small_flux2_fp8` text encoder is another 17 GB. That is 51 GB of weights, so it
block-swaps over PCIe on every step rather than failing outright. `flux-2-klein-4b` is only
7.3 GB and would fit alongside the encoder sequentially, but it is untested here.

Flux writes gibberish text on any surface that looks like it wants lettering. Either
accept it, keep such surfaces out of frame, or plan to paint it out.
