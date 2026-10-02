# Labelling rules (Phase 1.2)

How to label screenshots in Label Studio so that two people produce the same boxes.
Config: `workshop/labels/ls_config.xml`. Output: `data/labels/screens.json` (ScreenLabel v1.0).

## Rules

1. **Box every cat and every spider that is at least 30% visible.** Less than 30% visible: do not box it.
2. **Cartoons, drawings and stickers count.** Pick the matching `kind` (photo, cartoon, drawing, sticker, emoji, text, other).
3. **The emoji** (a cat face) gets the label `cat-emoji`; the spider emoji gets `spider-emoji`. Their kind is `emoji`.
4. **The word "cat"** (text on screen) gets the label `cat-text`. Its kind is `text`.
5. **Scope.** `object` = the animal only. `wholeElement` = the whole post or card around it should be covered. Choose `wholeElement` when the animal is the point of the post (for example a photo post); choose `object` when it is a small part of a bigger item.
6. **Clean must be ticked explicitly.** A screenshot with no cat or spider box must have `clean` ticked. A screenshot with boxes must not. An image with neither is "unlabelled" and the converter rejects it.
7. **Tick every lookalike present** (dog, fox, lion, tiger, stuffed-toy, cat-logo, crab, other), whether or not the image also has boxes. Lookalikes are never boxed.
8. **The box is tight around the visible part** of the animal. Do not include the card, caption or border.
9. **One box per animal.** Two cats = two boxes. A group that overlaps is still one box per animal.

## Label vocabulary

| Label | Concept | Default kind | Tag |
| --- | --- | --- | --- |
| cats | cats | photo | - |
| cat-emoji | cats | emoji | cat-emoji |
| cat-text | cats | text | cat-text |
| spiders | spiders | photo | - |
| spider-emoji | spiders | emoji | spider-emoji |

## Changes

Log every rule update made after the second-person review here (date, rule number, what changed, why).

| Date | Rule | Change | Reason |
| --- | --- | --- | --- |
| - | - | (none yet) | - |
