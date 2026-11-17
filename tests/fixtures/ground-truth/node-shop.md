# node-shop

Monorepo de una tienda chica de merchandising con npm workspaces (`package.json` raíz con `"workspaces": ["packages/*"]`). Tiene tres paquetes:

- **`packages/api`:** API en Express 5 y JavaScript CommonJS.
  - **Datos:** knex sobre SQLite o Postgres.
  - **Código:** catálogo con disponibilidad, carritos de invitado en memoria, pedidos con totales y estados, y reserva de stock.
  - **Tests y migraciones:** tests en jest y migraciones knex en `packages/api/migrations/`.
  - **Contrato e infraestructura:** `openapi.json` y un `Dockerfile`.
- **`packages/web`:** tienda en React con TypeScript y Vite.
  - **Configuración:** alias `@/` en el `tsconfig.json`.
  - **Código:** catálogo, cajón del carrito, checkout con validación de tarjeta, y una pantalla de back office que se carga aparte.
  - **Tests:** vitest.
- **`packages/shared`:** TypeScript sin build.
  - **Contenido:** límites de negocio (`limits.ts`), cálculo de totales (`pricing.ts`) y tipos.
  - **Cómo se consume:** su `main` es `src/index.ts`. Node 24 lo corre desde el fuente con type stripping, y por eso sus imports internos llevan la extensión `.ts`.
  - **Quién lo importa:** la api (`require('@shop/shared')`) y la web (`import ... from '@shop/shared'`).

Más un `.gitlab-ci.yml` en la raíz. No hay `package-lock.json`, para no inflar las líneas. El fixture tiene 1485 líneas en 60 archivos:

| Tipo | Líneas |
|---|---|
| JavaScript | 528 |
| TypeScript | 745 |
| JSON | 148 |
| YAML | 26 |
| HTML | 12 |
| Markdown | 10 |
| Dockerfile y `.gitignore` | 16 |

El código de producción suma 1122 líneas; los tests, 122; las migraciones, 29.

## Cómo salen módulos y aristas

**Módulos.** Son las carpetas con al menos un `.js`/`.ts`/`.tsx` que no es test ni migración. Hay dos que salen solo de un archivo de configuración: `packages/api`, por `knexfile.js`, y `packages/web`, por `vite.config.ts`. La raíz y `packages/shared` no son módulos: solo tienen manifiestos (JSON, YAML, Markdown). Tampoco son módulos las carpetas de solo tests (`packages/api/test`, `packages/api/src/cart/__tests__`) ni `packages/api/migrations`.

**Resolución.** Las aristas salen de resolver cada `import`/`export ... from`/`import()`/`require()` con string literal:
- **Relativos:** se prueba `<spec>`, `<spec>` + extensión y `<spec>/index` + extensión.
- **Alias:** `@/*` resuelve a `packages/web/src/*`, desde `baseUrl: "."` en `packages/web/tsconfig.json`.
- **Workspace:** `@shop/shared` resuelve a `packages/shared/src`, la carpeta del `main`.
- **Externos:** lo demás es npm o builtin (`express`, `knex`, `react`, `react-router`, `node:crypto`, `@shop/design-tokens`, ...).

`import type` cuenta como arista porque la regla es sintáctica (`import ... from '<spec>'`). Cuatro aristas dependen de eso:
- `packages/web/src/api` → `packages/shared/src`;
- `packages/web/src/components` → `packages/web/src/hooks`;
- `packages/web/src/pages` → `packages/web/src/hooks`;
- `packages/web/src/pages/Admin` → `packages/shared/src`.

## Casos difíciles

1. **Ciclo:** `packages/api/src/orders` ↔ `packages/api/src/inventory`.
   - **Ida:** `orders/service.js` requiere `../inventory/stock` para validar disponibilidad y descontar stock al despachar.
   - **Vuelta:** `inventory/stock.js` requiere `../orders/status` para saber qué estados reservan stock.
   - **Solo entre carpetas:** a nivel archivo no hay ciclo.
2. **Módulo grande:** `packages/web/src/components` tiene 10 archivos de producción y 419 líneas, más un test co-ubicado.
3. **Imports relativos:** en todos los paquetes.
   - **Subiendo dos niveles:** `../../knexfile` en `packages/api/src/db/index.js` y `../../api/client` en `packages/web/src/pages/Admin/index.tsx`.
   - **Con extensión `.ts` explícita:** en `packages/shared/src/pricing.ts` y `packages/shared/src/index.ts`.
4. **Alias `@/`.** Lo usan `packages/web/src/App.tsx`, `packages/web/src/pages/CheckoutPage.tsx`, `packages/web/src/pages/Admin/index.tsx` y los componentes.
   - **Alias más índice de carpeta:** `@/components` resuelve a `packages/web/src/components/index.ts`.
   - **Alcance:** el alias es del tsconfig de web. `packages/shared/tsconfig.json` no tiene `paths`.
5. **Índice de carpeta:**
   - **En TS:** `packages/web/src/App.tsx` importa `./components`, que es `packages/web/src/components/index.ts`.
   - **En CommonJS:** `packages/api/src/app.js` (`./routes`), `packages/api/src/server.js` (`./db`) y `require('../errors')`, que resuelve a `packages/api/src/errors/index.js`.
6. **Workspace por nombre:** `@shop/shared` resuelve a `packages/shared/src`.
   - **Desde la api:** `packages/api/src/orders/totals.js`, `packages/api/src/orders/rules.js`, `packages/api/src/inventory/stock.js` y `packages/api/src/cart/cart.js`.
   - **Desde la web:** `packages/web/src/hooks/useCart.ts`, los componentes y las páginas.
7. **Import dinámico con literal (es arista):** `import('./pages/Admin')` en `packages/web/src/App.tsx` resuelve al índice `packages/web/src/pages/Admin/index.tsx`. Es la única arista `packages/web/src` → `packages/web/src/pages/Admin`.
8. **`require` con variable (no es arista):** `require(dialectPath)` en `packages/api/src/db/index.js:9`, con `'./dialects/' + client`.
   - **Destino real:** la carpeta `packages/api/src/db/dialects` existe y es módulo.
   - **Sin entrantes:** nadie la importa con un literal, así que queda sin aristas entrantes.
9. **Externos parecidos a locales (no son aristas):**
   - **`react-router`:** lo importan `packages/web/src/main.tsx`, `packages/web/src/App.tsx`, `packages/web/src/pages/CheckoutPage.tsx` y `packages/web/src/components/Layout.tsx`. Es de npm, aunque exista la carpeta local `packages/api/src/routes`.
   - **`@shop/design-tokens`:** lo importa `packages/web/src/components/StockBadge.tsx`. Comparte el scope `@shop/` con los workspaces, pero no es un paquete del repo: es una dependencia de `packages/web/package.json`.
10. **Import comentado (no es arista):** `// const { availableFor } = require('./inventory/stock');` en `packages/api/src/app.js:6`. No hay arista `packages/api/src` → `packages/api/src/inventory`.
11. **Nombre local que tapa otra carpeta:** en `packages/api/src/routes/index.js`, `./orders` y `./cart` son `routes/orders.js` y `routes/cart.js`. Son de la misma carpeta, así que no hay arista. No son las carpetas `packages/api/src/orders` ni `packages/api/src/cart`.
12. **Una migración que importa código de producción:** `packages/api/migrations/20260302091500_create_orders.js` requiere `../src/orders/status`. Las migraciones no originan aristas. Lo mismo pasa con los tests, que importan `../src/...`.
13. **Tests con forma rara:**
    - **Sin `.test` en el nombre:** `packages/api/src/cart/__tests__/cart-store.js` es test porque está en `__tests__/`, y jest lo toma con su `testMatch` por defecto.
    - **Co-ubicado:** `packages/web/src/components/CheckoutForm.test.tsx` vive en una carpeta de producción. La carpeta sigue siendo módulo por sus otros archivos.
14. **Archivos de configuración que son código:**
    - **Hacen módulo:** `packages/web/vite.config.ts` y `packages/api/knexfile.js`.
    - **Origen de una arista:** `packages/api/src/db/index.js` requiere `../../knexfile`, que da `packages/api/src/db` → `packages/api`.
    - **Strings que no son imports:** el `'/src'` del alias de Vite y el `'./migrations'` del knexfile.
15. **Entrypoints:**
    - **Por script:** `packages/api/scripts/seed.js`, con `"seed": "node scripts/seed.js"`.
    - **Script que coincide con el `main`:** `"start": "node src/server.js"` es el mismo `main` de `packages/api`.
    - **`main` en TypeScript:** `packages/shared/src/index.ts`.
    - **Desde el HTML:** `src="/src/main.tsx"` en `packages/web/index.html` es relativo a la carpeta del HTML.
    - **No son entrypoints:** `"migrate": "knex migrate:latest"` no es `node <archivo>`, y el `CMD` del `Dockerfile` no cuenta.
16. **Datos sensibles sintéticos:**
    - **Tarjeta y email de prueba:** `packages/web/src/components/CheckoutForm.test.tsx` usa la tarjeta publicada `4111 1111 1111 1111` y `buyer@example.com`.
    - **Email de contacto:** `packages/web/src/components/Layout.tsx` muestra `support@example.com`.
    - **Secretos por nombre:** `packages/api/src/config.js` lee `ADMIN_API_TOKEN` y `DATABASE_URL` del entorno. No hay ningún archivo sensible.

## Verdad conocida

```json
{
  "fixture": "node-shop",
  "languages": ["javascript", "typescript"],
  "frameworks": ["express", "jest", "knex", "react", "typescript", "vite", "vitest"],
  "entrypoints": [
    "packages/api/scripts/seed.js",
    "packages/api/src/server.js",
    "packages/shared/src/index.ts",
    "packages/web/src/main.tsx"
  ],
  "test_files": [
    "packages/api/src/cart/__tests__/cart-store.js",
    "packages/api/test/status.test.js",
    "packages/api/test/stock.test.js",
    "packages/api/test/totals.test.js",
    "packages/web/src/components/CheckoutForm.test.tsx"
  ],
  "ci": [".gitlab-ci.yml"],
  "migrations": [
    "packages/api/migrations/20260302090000_create_products.js",
    "packages/api/migrations/20260302091500_create_orders.js"
  ],
  "api_contracts": ["packages/api/openapi.json"],
  "infrastructure": ["packages/api/Dockerfile"],
  "sensitive_files": [],
  "modules": [
    "packages/api",
    "packages/api/scripts",
    "packages/api/src",
    "packages/api/src/cart",
    "packages/api/src/db",
    "packages/api/src/db/dialects",
    "packages/api/src/errors",
    "packages/api/src/inventory",
    "packages/api/src/orders",
    "packages/api/src/routes",
    "packages/shared/src",
    "packages/web",
    "packages/web/src",
    "packages/web/src/api",
    "packages/web/src/components",
    "packages/web/src/hooks",
    "packages/web/src/pages",
    "packages/web/src/pages/Admin"
  ],
  "edges": [
    ["packages/api/scripts", "packages/api/src"],
    ["packages/api/scripts", "packages/api/src/db"],
    ["packages/api/src", "packages/api/src/db"],
    ["packages/api/src", "packages/api/src/routes"],
    ["packages/api/src/cart", "packages/api/src/errors"],
    ["packages/api/src/cart", "packages/shared/src"],
    ["packages/api/src/db", "packages/api"],
    ["packages/api/src/inventory", "packages/api/src/orders"],
    ["packages/api/src/inventory", "packages/shared/src"],
    ["packages/api/src/orders", "packages/api/src/errors"],
    ["packages/api/src/orders", "packages/api/src/inventory"],
    ["packages/api/src/orders", "packages/shared/src"],
    ["packages/api/src/routes", "packages/api/src/cart"],
    ["packages/api/src/routes", "packages/api/src/errors"],
    ["packages/api/src/routes", "packages/api/src/inventory"],
    ["packages/api/src/routes", "packages/api/src/orders"],
    ["packages/web/src", "packages/web/src/components"],
    ["packages/web/src", "packages/web/src/hooks"],
    ["packages/web/src", "packages/web/src/pages"],
    ["packages/web/src", "packages/web/src/pages/Admin"],
    ["packages/web/src/api", "packages/shared/src"],
    ["packages/web/src/components", "packages/shared/src"],
    ["packages/web/src/components", "packages/web/src/hooks"],
    ["packages/web/src/hooks", "packages/shared/src"],
    ["packages/web/src/hooks", "packages/web/src/api"],
    ["packages/web/src/pages", "packages/shared/src"],
    ["packages/web/src/pages", "packages/web/src/api"],
    ["packages/web/src/pages", "packages/web/src/components"],
    ["packages/web/src/pages", "packages/web/src/hooks"],
    ["packages/web/src/pages/Admin", "packages/shared/src"],
    ["packages/web/src/pages/Admin", "packages/web/src/api"],
    ["packages/web/src/pages/Admin", "packages/web/src/components"]
  ],
  "capabilities": [
    {
      "name": "order-pricing",
      "key_files": [
        "packages/shared/src/pricing.ts",
        "packages/shared/src/limits.ts",
        "packages/api/src/orders/totals.js"
      ],
      "rules": [
        "Los códigos promocionales (WELCOME10, VIP25, STAFF40) se aceptan sin importar mayúsculas ni espacios; un código desconocido rechaza el pedido con 422.",
        "Ningún descuento pasa del 30% del subtotal: STAFF40 descuenta 30%, no 40%.",
        "El envío es gratis cuando el subtotal con descuento llega a 5000 centavos (USD 50); si no, cuesta 499 centavos.",
        "El impuesto se calcula sobre el subtotal con descuento, nunca sobre el envío, y se redondea a centavos enteros."
      ]
    },
    {
      "name": "stock-reservation",
      "key_files": [
        "packages/api/src/inventory/stock.js",
        "packages/api/src/orders/rules.js"
      ],
      "rules": [
        "Lo disponible es el stock físico (on_hand) menos lo que reservan los pedidos abiertos (pending y paid), nunca menos de cero; los cancelados no reservan.",
        "Cada línea de un pedido lleva entre 1 y 10 unidades y no puede superar lo disponible (409, 'Only N left').",
        "Un producto no puede repetirse en dos líneas del mismo pedido, y el precio unitario sale del catálogo, no del cliente.",
        "Con 5 unidades disponibles o menos el producto está en low-stock; con 0, en out-of-stock.",
        "Al pasar un pedido a shipped se descuentan sus unidades del stock físico."
      ]
    },
    {
      "name": "order-lifecycle",
      "key_files": [
        "packages/api/src/orders/status.js",
        "packages/api/src/orders/service.js",
        "packages/api/src/routes/orders.js"
      ],
      "rules": [
        "Las transiciones permitidas son pending a paid o cancelled, paid a shipped o cancelled, y shipped a delivered; delivered y cancelled son finales y cualquier otra responde 409.",
        "Cancelar un pedido que ya estaba pagado lo marca con refund_required.",
        "Un pedido nuevo nace pending y exige un email válido (400 si no lo es).",
        "Cambiar el estado exige el header x-admin-token igual a ADMIN_API_TOKEN (401 si falta o no coincide)."
      ]
    },
    {
      "name": "guest-cart",
      "key_files": [
        "packages/api/src/cart/cart.js",
        "packages/web/src/hooks/useCart.ts"
      ],
      "rules": [
        "Agregar un producto que ya está en el carrito suma la cantidad.",
        "La cantidad por línea se recorta a 10, y una cantidad 0 saca la línea.",
        "Un carrito admite como máximo 25 productos distintos (la API responde 422).",
        "Un carrito de invitado expira después de 7 días sin cambios."
      ]
    },
    {
      "name": "checkout-validation",
      "key_files": [
        "packages/web/src/components/checkoutValidation.ts",
        "packages/web/src/components/CheckoutForm.tsx"
      ],
      "rules": [
        "El número de tarjeta tiene que pasar el dígito verificador de Luhn y tener de 13 a 19 dígitos, ignorando espacios y guiones.",
        "La tarjeta vale hasta el último día de su mes de vencimiento (MM/YY).",
        "El email tiene que tener usuario, una arroba y un dominio con punto, y el ZIP, 5 dígitos (con +4 opcional).",
        "El formulario no se envía mientras algún campo tenga error."
      ]
    }
  ],
  "hard_cases": [
    "ciclo: packages/api/src/orders <-> packages/api/src/inventory (packages/api/src/orders/service.js requiere ../inventory/stock y packages/api/src/inventory/stock.js requiere ../orders/status)",
    "módulo grande: packages/web/src/components (10 archivos de producción, 419 líneas, más packages/web/src/components/CheckoutForm.test.tsx)",
    "imports relativos: ../../knexfile en packages/api/src/db/index.js, ../../api/client en packages/web/src/pages/Admin/index.tsx, y extensión .ts explícita en packages/shared/src/pricing.ts",
    "alias de tsconfig: @/* -> src/* en packages/web/tsconfig.json; @/components en packages/web/src/pages/CheckoutPage.tsx resuelve a packages/web/src/components/index.ts",
    "índice de carpeta: ./components en packages/web/src/App.tsx resuelve a packages/web/src/components/index.ts; ./routes en packages/api/src/app.js resuelve a packages/api/src/routes/index.js",
    "workspace por nombre: @shop/shared resuelve a packages/shared/src (carpeta del main packages/shared/src/index.ts) desde packages/api/src/orders/totals.js y packages/web/src/hooks/useCart.ts",
    "import dinámico con literal (es arista): import('./pages/Admin') en packages/web/src/App.tsx resuelve a packages/web/src/pages/Admin/index.tsx",
    "require con variable (no es arista): require(dialectPath) en packages/api/src/db/index.js:9; packages/api/src/db/dialects queda sin aristas entrantes",
    "externo parecido a local (no es arista): react-router en packages/web/src/App.tsx frente a la carpeta packages/api/src/routes, y @shop/design-tokens en packages/web/src/components/StockBadge.tsx, que comparte el scope de los workspaces",
    "import comentado (no es arista): packages/api/src/app.js:6 comenta require('./inventory/stock')",
    "nombre local que tapa otra carpeta: ./orders y ./cart en packages/api/src/routes/index.js son packages/api/src/routes/orders.js y packages/api/src/routes/cart.js",
    "import type es arista: packages/web/src/api/client.ts solo importa tipos de @shop/shared",
    "migración que importa código (no origina arista): packages/api/migrations/20260302091500_create_orders.js requiere ../src/orders/status",
    "test sin .test en el nombre: packages/api/src/cart/__tests__/cart-store.js",
    "config que es código y hace módulo: packages/web/vite.config.ts y packages/api/knexfile.js (arista packages/api/src/db -> packages/api)",
    "entrypoint solo por script: packages/api/scripts/seed.js; main en TypeScript: packages/shared/src/index.ts; script de index.html: packages/web/src/main.tsx",
    "datos sintéticos: tarjeta de prueba 4111 1111 1111 1111 y buyer@example.com en packages/web/src/components/CheckoutForm.test.tsx; secretos leídos por nombre en packages/api/src/config.js"
  ]
}
```
