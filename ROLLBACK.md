# Procedimiento de Rollback y Despliegue

Este documento describe la estrategia de despliegue y el procedimiento de recuperación en caso de fallos (Rollback) para la plataforma **EPS Digital**.

---

## 1. Estrategia de Despliegue (Rolling Update)

Render ejecuta automáticamente despliegues de tipo **Rolling Update** (Zero-Downtime Deployments):
* Al recibir el evento de despliegue desde el pipeline de GitHub Actions, Render levanta un nuevo contenedor con la última versión del código.
* Se realizan verificaciones de salud (*Health Checks*).
* Si el nuevo contenedor responde correctamente, Render redirige el tráfico hacia la nueva versión y apaga la versión anterior sin interrumpir el servicio.

---

## 2. Procedimiento de Rollback

Si una versión recién desplegada en la rama `main` presenta fallos críticos en producción, se deben seguir estos pasos:

### Opción A: Rollback Manual desde Render (Inmediato)
1. Ingresar a [dashboard.render.com](https://dashboard.render.com/).
2. Seleccionar el servicio afectado (ej. `eps-auth-service` o `eps-digital`).
3. Ir a la pestaña **Events** en el menú lateral.
4. Identificar el último despliegue exitoso y estable.
5. Hacer clic en el menú de opciones (`...`) al lado de dicho evento y seleccionar **Rollback to this deploy**.

### Opción B: Rollback en Git (Para mantener la coherencia del repositorio)
1. Localizar el commit estable previo en la rama `main`.
2. Crear una rama de corrección desde `develop` o un `hotfix`.
3. Revertir el commit defectuoso:
   ```bash
   git revert <commit-hash-defectuoso>
   ```
4. Abrir un Pull Request hacia main para que el pipeline ejecute las pruebas y vuelva a desplegar la versión corregida de forma segura.