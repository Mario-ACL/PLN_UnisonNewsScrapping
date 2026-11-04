# Historia: post de Medium

El entregable de la historia: *"Cómo la pandemia cambió la manera de escribir de la Universidad de Sonora"*.

- `post_medium.md`: el texto del post, con las gráficas en su lugar.
- `graficas/`: las 8 gráficas en PNG.

El análisis y las gráficas se generan en el notebook `06_historia_medium.ipynb` (en la carpeta principal),
que sigue el post sección por sección y termina con una tabla de todas las cifras que cita el texto.
Para volver a generar las gráficas hay que correr ese notebook (necesita el archivo completo de noticias).

## Pasarlo a Medium

Medium no importa archivos Markdown, así que el post se arma a mano:

1. Abrir `post_medium.md` en una vista previa (VS Code o GitHub) y copiar el texto sección por sección.
2. El título va como título del post y la línea de abajo como subtítulo.
3. Donde aparece cada gráfica, subir el PNG de `graficas/` y pegar como pie de foto la línea en cursiva que le sigue.
