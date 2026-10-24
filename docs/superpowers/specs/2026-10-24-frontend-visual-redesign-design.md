# EPS Digital — Rediseño visual del frontend

## Objetivo

Actualizar visualmente todo el frontend para que EPS Digital se sienta como una
plataforma médica moderna, confiable y cercana para usuarios jóvenes y adultos
mayores, sin cambiar comportamiento, lógica ni contratos existentes.

## Dirección visual aprobada

La dirección es **cercana y humana**: una experiencia serena, clara y amable,
sin perder la autoridad clínica necesaria. El navy `#2B3E59` permanece como
ancla de marca. El sistema incorpora un teal clínico sobrio para acciones
secundarias y estados positivos, fondos marfil muy claros para evitar una
sensación fría, texto azul carbón de alto contraste y estados semánticos
accesibles.

Inter continuará en títulos y navegación; Roboto continuará en lectura y
formularios. La escala tipográfica, pesos, tracking y line-height se ajustarán
para mejorar legibilidad, especialmente en móvil y para adultos mayores.

La forma abandona el uso excesivo de pills: los CTAs principales pueden
conservar una forma redondeada reconocible, mientras cards, campos y controles
usan radios moderados. La profundidad se expresa con bordes sutiles y sombras
ambientales; no se usarán sombras duras ni efectos decorativos innecesarios.

## Alcance visual

1. **Tokens y base:** actualizar `theme.css`, `index.css` y `fonts.css`, además
   de estados globales de foco, selección, scrollbar y movimiento reducido.
2. **Componentes UI:** alinear Button, Card, Input, Label, Badge, Alert, Dialog,
   Select, Tabs, Table, Skeleton, Tooltip y Sonner con los mismos tokens,
   estados y radios.
3. **Shell público:** mejorar Navbar, Footer y Layout, incluyendo jerarquía,
   estado activo, menú móvil, espaciado y legibilidad.
4. **Shells internos:** mejorar AdminLayout y MedicoLayout con navegación activa,
   superficies, encabezados y composición responsive.
5. **Páginas:** propagar el sistema a páginas públicas, paciente,
   administración y portal médico con cambios de clases Tailwind y estructura
   JSX exclusivamente visual.

## Restricciones

- No modificar lógica, hooks, llamadas API, stores, rutas, validaciones, props,
  nombres de funciones ni nombres de archivos.
- No modificar textos: todo permanece en español.
- Mantener contraste WCAG 2.1 AA, focus visible y targets táctiles cómodos.
- Las animaciones solo usarán transform, opacity, color o sombra; serán sutiles,
  de bajo costo y estarán desactivadas para `prefers-reduced-motion`.
- No introducir nuevos patrones de interacción ni cambios de flujo.

## Verificación

- Ejecutar `npm run build` desde `frontend`.
- Revisar el diff para confirmar que los cambios son visuales.
- Inspeccionar escritorio y móvil cuando el entorno de ejecución esté disponible.
- Comprobar estados hover, focus, disabled, loading, error y empty en las
  superficies modificadas.
- Al finalizar, informar todos los archivos modificados.
