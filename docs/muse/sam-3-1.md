# SAM 3.1 (Segment Anything Model) on Meta Model API

Verified 2026-10-26

**SAM 3.1 returns geometry (boxes and pixel masks), NOT text.** It cannot read a label, name a drug, caption a scene or answer a question. To get text from a crop, send the crop to Muse Spark ([media segmentation](https://dev.meta.ai/docs/media-segmentation), [segmenting](https://dev.meta.ai/docs/sam/segmenting)).

Model id `sam-3.1`. Endpoint `POST https://api.meta.ai/v1/responses`, same Bearer key; upload clips with `POST /v1/files` ([SAM overview](https://dev.meta.ai/docs/sam/overview)). Price $2.50 per 1,000 images and $0.20 per 1,000 video frames, minimum 50 frames per video request. Rate limit 3,000 RPM, no TPM ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)).

## Inputs

- Prompt types, exactly one kind per request ([segmenting](https://dev.meta.ai/docs/sam/segmenting)):
  - **Text concept**: a short noun phrase naming ONE concept ("blister pack", "red box"). Commands, questions, comma lists, "A and B", negation, OR and spatial phrasing ("on the left") are unreliable or return nothing. Plurals, case and punctuation are ignored. Add attributes to narrow ("red square").
  - **Box and point prompts**: text of the form `<0f>1<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>,2<|point;x=..;y=..;w=..;h=..|>-<|point;...|>`. You choose object ids; `-` before a point makes it negative (negative boxes are rejected). Up to 16 objects. Always return `one_bit` masks.
  - A phrase and box/point prompts in one request return 400.
- Media part: `input_image` (`image_url`) or `input_video` (`video_url` or `file_id`). URL is a public URL or base64 data URL.
- Images: one image per request, frame index `<0f>`. Accepted image formats, size cap and resolution cap for SAM specifically: Not documented (the generic Spark image list is JPEG, PNG, GIF, WebP).
- Video: MP4 or MOV, H.264, H.265 or MPEG-4. VP9 and WebM are rejected. Up to 15,000 frames (about 10 minutes). Tracks up to 16 objects per frame. Direction for box/point prompts: `metadata.propagation_direction` = `both` (default), `forward`, `backward`.
- Prompt coordinates `w` and `h` must be the media's size as displayed, after EXIF/rotation. A different aspect ratio returns 400. Prompt coordinates must lie inside the frame.

## Minimal request (from the docs)

```python
import os
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
with client.responses.stream(
    model="sam-3.1",
    input=[{"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": "glasses"},
        {"type": "input_image", "image_url": "https://example.com/photo.png"}]}],
    # metadata={"mask_encoding": "one_bit", "include_confidence": "true"},
) as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="")
```

Source: [media segmentation](https://dev.meta.ai/docs/media-segmentation). Streaming is recommended for video, optional for images. `metadata` values are strings: send `"true"`, not a boolean.

## Output format

The result is special-token text in the `output_text` lane, one line per frame (an image is frame `<0f>`) ([reading output](https://dev.meta.ai/docs/sam/reading-segmentation)):

```text
<0f>0<|box;x1=353;y1=382;x2=453;y2=427;w=537;h=561|><|mask;x=0;y=0;data=46,101,~...|>,1<|box;...|><|mask;...|>
```

- Each record = object id, one box, one mask. Box corners are source pixels (inclusive `x2,y2`); `w,h` is the source size.
- Mask: `data=<H>,<W>,<enc>payload`, height first, base85 payload (not base64). `~` = lossless (default), `!` = one_bit (several times smaller; set `metadata.mask_encoding="one_bit"`). The mask raster is smaller than the frame; how it maps onto the frame beyond the box is Not documented in the prose pages (use `@meta-sam/graphics` or verify empirically).
- Confidence: only with `metadata.include_confidence="true"`, field `c` from 0 to 1 on box and mask.
- Object ids are stable across video frames but not dense or 0-based. Frames with no object emit no line; frame order is not always ascending.
- Zero matches = stream completes with empty `output_text`. That is a valid result, not an error.
- Results can vary slightly between identical runs (box coordinates, mask edges, occasionally which objects).

## Decoding: masks, RLE, polygons

Native output is a raster mask, not polygons and not RLE. Client libraries convert it ([SAM client libraries](https://dev.meta.ai/docs/sam/client-libraries)):

- TypeScript: `npm install @meta-sam/parser` (`parseImageStream`, `decodeMaskToRaster`, `decodeMaskToRLE`, `decodeMaskToSVGPath`); optional `@meta-sam/graphics`, `@meta-sam/video`, `@meta-sam/react`.
- Python: `pip install meta-sam-parser`, import `meta_sam_parser` (`decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path`, `build_object_prompt`).
- `decodeMaskToRLE` gives COCO RLE `{size: [h, w], counts}` (column-major); `decodeMaskToSVGPath` gives a polygonal `M/L/Z` path string.

## What it does not do

- No OCR, no labels, no class names, no captions. A mask carries no identity beyond the prompt that produced it.
- One concept per request: segmenting several object types means several calls ([segmenting](https://dev.meta.ai/docs/sam/segmenting#prompting)).
- No stated accuracy numbers for small, curved or tilted text-bearing objects like foil blisters: Not documented.

## Pairing with Muse Spark

The docs' own pattern: let Muse Spark decide what to segment, then pass the concept to SAM 3.1 for masks ([media segmentation](https://dev.meta.ai/docs/media-segmentation)). For Anamnesis: SAM crops the pack; Spark (or another VLM) reads the crop; keep the SAM object id, box and frame size as the provenance link. Cookbook: [SAM API basics](https://dev.meta.ai/docs/cookbook/sam-api-basics). Model page: [dev.meta.ai/models/sam-3-1](https://dev.meta.ai/models/sam-3-1).
