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
