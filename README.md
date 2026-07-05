# Golden Media API

Microservicio FastAPI para procesar imágenes desde n8n y otros clientes.

## Endpoints

- GET /
- GET /health
- POST /heic-to-jpg
- POST /convert-to-jpg
- POST /resize
- POST /compress
- POST /thumbnail
- POST /instagram-feed
- POST /instagram-story
- POST /card  (tarjeta 1080×1080 con overlay de texto — Golden brand)

## /card — tarjeta de carrusel con texto (JSON)

Renderiza server-side (Pillow) una tarjeta 1080×1080 con la foto de fondo + kicker + headline
en el sistema de marca Golden (gradiente de legibilidad, marco hairline, wordmark GOLDEN,
regla dorado-gold). Reemplaza el render HTML de Browserless. Requiere las fuentes en `fonts/`
(ver `fonts/DOWNLOAD.md`).

```http
POST http://goldenflyfihing_golden-image-api:8000/card
Content-Type: application/json
```

Body:
```json
{
  "image_url": "https://goldenflyfishing.com/.../foto.jpg",
  "kicker": "GOLDEN DORADO",
  "headline": "The strike that clears the water",
  "sub_text": "",
  "location": "Upper Paraná · AR",
  "role": "hook",
  "wordmark": "GOLDEN",
  "mode": "auto"
}
```
- `mode`: `auto` (default, decide cover/contain según el aspecto) | `cover` | `contain`.
- `role`: `cta` o `cta_cover` centran el bloque y oscurecen (para la portada del lead magnet).
- `design_variant` (opcional): `cinematic_hero` | `editorial_dark` | `technical_guide` | `lodge_warm` | `premium_minimal` | `story_proof` | `cta_clean`. Ajusta intensidad de overlay y layout (cta_clean centra).
- `overlay_strength` (opcional): `light` | `medium` | `strong` — intensidad del gradiente de legibilidad.
- `typography_style` (opcional): `premium_serif` (default, Playfair) | `modern_sans` (Inter en la headline).
- Devuelve `image/jpeg`.

## Ejemplos desde n8n

### 1) Convertir HEIC a JPG

```http
POST http://goldenflyfihing_golden-image-api:8000/heic-to-jpg
Content-Type: multipart/form-data
```

Form-data:
- file: imagen.heic

### 2) Crear imagen para Instagram Feed

```http
POST http://goldenflyfihing_golden-image-api:8000/instagram-feed?blur_background=true&quality=92
Content-Type: multipart/form-data
```

Form-data:
- file: imagen
- background_color: opcional, por ejemplo FFFFFF

### 3) Crear imagen para Instagram Story

```http
POST http://goldenflyfihing_golden-image-api:8000/instagram-story?blur_background=true&quality=92
Content-Type: multipart/form-data
```

Form-data:
- file: imagen
- background_color: opcional, por ejemplo FFFFFF

### 4) Redimensionar imagen

```http
POST http://goldenflyfihing_golden-image-api:8000/resize?width=800&height=600&keep_aspect_ratio=true&quality=90
Content-Type: multipart/form-data
```

Form-data:
- file: imagen

### 5) Comprimir imagen

```http
POST http://goldenflyfihing_golden-image-api:8000/compress?quality=85
Content-Type: multipart/form-data
```

Form-data:
- file: imagen

## Notas

- El servicio corre en el puerto 8000.
- El endpoint /heic-to-jpg sigue siendo compatible.
- Se aceptan imágenes hasta 25 MB.
```
