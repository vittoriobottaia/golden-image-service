# Fonts for /card renderer

The `/card` endpoint expects these TTFs in this folder. If any are missing the
renderer falls back to Pillow's default font (it won't crash, but it won't look
on-brand), so add them before deploying.

Required files:
- `PlayfairDisplay-SemiBold.ttf`  (headlines)
- `Inter-SemiBold.ttf`            (kicker, wordmark, CTA pill)
- `Inter-Regular.ttf`            (location, sub text)

## Quick download (run inside this `fonts/` folder)

```bash
# Inter
curl -L -o Inter.zip "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
unzip -j Inter.zip "extras/ttf/Inter-SemiBold.ttf" "extras/ttf/Inter-Regular.ttf" -d .
rm Inter.zip

# Playfair Display (from Google Fonts repo)
curl -L -o PlayfairDisplay-SemiBold.ttf \
  "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
```

> Note: the Playfair file above is a variable font named `PlayfairDisplay[wght].ttf`.
> Rename it to `PlayfairDisplay-SemiBold.ttf` (Pillow uses the default instance,
> which reads as a semibold-ish weight). For exact SemiBold, download the static
> instance from https://fonts.google.com/specimen/Playfair+Display and place it here.

These fonts are OFL-licensed (free for commercial use).
