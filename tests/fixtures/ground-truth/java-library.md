# java-library

Servicio de circulación de una biblioteca de barrio, en Spring Boot 3 con Maven, Java 21, JPA sobre PostgreSQL y migraciones Flyway. Lleva el catálogo de títulos y ejemplares, los socios con sus límites por tipo, los préstamos (vencimiento, renovaciones, devolución con multa) y los avisos de vencimiento. Usa Lombok para getters y constructores, y Guava en el módulo de socios.

Todo el código vive bajo `src/main/java/com/example/library/` (la única raíz Java). Cada paquete es un módulo:
- la raíz (`LibraryApplication`, el único entrypoint);
- `books` (el módulo grande);
- `members`;
- `loans`;
- `notifications`;
- `common`.

Los tests son JUnit 5 con Mockito y AssertJ, bajo `src/test/java/`. Compilan y pasan: se verificaron con `javac` y el lanzador de JUnit contra jars locales, sin Maven y sin descargas.

## Cómo se derivó la verdad

Se aplicaron a mano las reglas del contrato de F6 sobre cada `import` de los archivos de producción:
- las rutas son relativas a la raíz del fixture;
- un `import a.b.C;` va a la carpeta del paquete `a.b`;
- un `import a.b.*;`, a `a/b`;
- un `import static a.b.C.m;`, a la carpeta del paquete `a.b`;
- solo si esa carpeta existe bajo `src/main/java/`.

Los tests y las migraciones no son módulos ni originan aristas.

Aristas resultantes:
- `library` → `loans`: `LibraryApplication` importa `LoanPolicy` para `@EnableConfigurationProperties`.
- `books` → `common`: excepciones.
- `loans` → `books`: solo por el wildcard.
- `loans` → `common`.
- `loans` → `members`.
- `loans` → `notifications`.
- `members` → `loans`: cierra el ciclo.
- `notifications` → `common`: solo por el `import static`.

## Casos difíciles

- **Ciclo `loans` ↔ `members`:**
  - `loans/LoanService.java` importa `Member`, `MemberRepository` y `MemberType` para validar el préstamo.
  - `members/MemberService.java` importa `LoanRepository` para no dar de baja a un socio con préstamos activos.
- **Módulo grande:** `books/` tiene 10 archivos y 422 líneas (`wc -l`; 360 sin contar las vacías): entidad, enums, value object `Isbn`, repositorio, criterios de búsqueda, DTOs, servicio y controlador.
- **Wildcard:** `loans/LoanService.java` hace `import com.example.library.books.*;`. Es el único import de `books` desde `loans`, así que la arista `loans` → `books` depende de resolverlo a la carpeta `books/`.
- **`import static`:** `notifications/ReminderPolicy.java` hace `import static com.example.library.common.Dates.today;`. Es lo único que une `notifications` con `common`: la arista sale del paquete `com.example.library.common`, no de una carpeta `Dates/`.
- **Mismo paquete sin import:** `loans/LoanService.java` usa `Loan`, `LoanRepository`, `FineCalculator` y `LoanPolicy` sin importarlos, y `books/BookService.java` usa `Book`, `Isbn` y `BookSearch` igual. No hay arista.
- **Nombre calificado sin import:**
  - `books/BookService.java` declara el campo y el parámetro del constructor como `com.example.library.notifications.Notifier`, sin `import`. En runtime `books` usa `notifications`, pero por contrato no hay arista `books` → `notifications`.
  - `books/Book.java` nombra `{@link com.example.library.loans.LoanService}` en el javadoc. Tampoco hay arista `books` → `loans`.
- **Librería externa con nombre parecido:** `members/MemberService.java` importa Guava:
  - `import com.google.common.base.Strings;`
  - `import static com.google.common.base.Preconditions.checkArgument;`
  - `import static com.google.common.base.Preconditions.checkState;`

  El segmento `common` coincide con el paquete local `com.example.library.common`, pero el paquete `com.google.common.base` no existe en el fixture. `members` no importa nada del `common` local (lanza `IllegalArgumentException` e `IllegalStateException`, que mapea el `ApiErrorHandler`), así que no hay arista `members` → `common`.
- **Tests que importan otros paquetes:** `src/test/java/.../loans/LoanServiceTest.java` importa de `books`, `members`, `notifications` y `common`, y `notifications/ReminderPolicyTest.java` importa `common.Dates`. Ninguno origina aristas, y las carpetas de `src/test/` no son módulos.
- **Módulo raíz con submódulos:** `src/main/java/com/example/library` es un módulo propio (contiene `LibraryApplication.java`), distinto de sus subcarpetas, y tiene su propia arista hacia `loans`.
- **Datos sintéticos y sin secretos:**
  - los emails son `@example.com` y `@students.example.com`;
  - los ISBN son los de ejemplo de la norma (`978-0-306-40615-7`, `0-8044-2957-X`);
  - la contraseña de la base se lee del entorno (`password: ${DB_PASSWORD}` en `application.yml`);
  - no hay archivos sensibles.

## Notas sobre el contrato

- **`frameworks`:** salen de los `<artifactId>` del `pom.xml`:
  - `spring-boot`: `spring-boot-starter-parent` y los starters;
  - `spring-web`: `spring-boot-starter-web`;
  - `spring-data-jpa`: `spring-boot-starter-data-jpa`;
  - `flyway`: `flyway-core`;
  - `junit`: `junit-jupiter`, declarado explícito además de `spring-boot-starter-test`.

  `maven` sale de que el manifiesto es un `pom.xml`. Guava, Lombok y el driver de PostgreSQL no están en el vocabulario.
- **`languages`:** solo `java`, el único lenguaje de código. Además hay `sql` (migraciones), `yaml` (config, contrato y CI) y `markdown`.
- **`src/main/resources/`:** no es módulo porque no tiene código de producción. Las migraciones son SQL y el resto, YAML.

```json
{
  "fixture": "java-library",
  "languages": ["java"],
  "frameworks": ["spring-boot", "spring-web", "spring-data-jpa", "junit", "flyway", "maven"],
  "entrypoints": ["src/main/java/com/example/library/LibraryApplication.java"],
  "test_files": [
    "src/test/java/com/example/library/books/IsbnTest.java",
    "src/test/java/com/example/library/loans/FineCalculatorTest.java",
    "src/test/java/com/example/library/loans/LoanServiceTest.java",
    "src/test/java/com/example/library/members/MemberServiceTest.java",
    "src/test/java/com/example/library/notifications/ReminderPolicyTest.java"
  ],
  "ci": ["azure-pipelines.yml"],
  "migrations": [
    "src/main/resources/db/migration/V1__init.sql",
    "src/main/resources/db/migration/V2__loan_fines_and_due_index.sql"
  ],
  "api_contracts": ["src/main/resources/static/openapi.yaml"],
  "infrastructure": ["Dockerfile"],
  "sensitive_files": [],
  "modules": [
    "src/main/java/com/example/library",
    "src/main/java/com/example/library/books",
    "src/main/java/com/example/library/common",
    "src/main/java/com/example/library/loans",
    "src/main/java/com/example/library/members",
    "src/main/java/com/example/library/notifications"
  ],
  "edges": [
    ["src/main/java/com/example/library", "src/main/java/com/example/library/loans"],
    ["src/main/java/com/example/library/books", "src/main/java/com/example/library/common"],
    ["src/main/java/com/example/library/loans", "src/main/java/com/example/library/books"],
    ["src/main/java/com/example/library/loans", "src/main/java/com/example/library/common"],
    ["src/main/java/com/example/library/loans", "src/main/java/com/example/library/members"],
    ["src/main/java/com/example/library/loans", "src/main/java/com/example/library/notifications"],
    ["src/main/java/com/example/library/members", "src/main/java/com/example/library/loans"],
    ["src/main/java/com/example/library/notifications", "src/main/java/com/example/library/common"]
  ],
  "capabilities": [
    {
      "name": "book-catalog",
      "key_files": [
        "src/main/java/com/example/library/books/Isbn.java",
        "src/main/java/com/example/library/books/BookService.java",
        "src/main/java/com/example/library/books/Book.java",
        "src/main/java/com/example/library/books/BookSearch.java"
      ],
      "rules": [
        "Un ISBN se acepta como ISBN-10 (con X como dígito verificador) o como ISBN-13 con prefijo 978 o 979, solo si el dígito verificador es válido, y se guarda normalizado a 13 dígitos: el ISBN-10 se convierte con el prefijo 978.",
        "El ISBN es único en el catálogo: registrar uno repetido se rechaza con duplicate_isbn.",
        "Un título tiene entre 1 y 20 ejemplares; agregar ejemplares que pasen de 20, o a un título retirado, se rechaza.",
        "Un título con ejemplares prestados no se puede retirar, y los títulos retirados no aparecen en la búsqueda.",
        "Si la búsqueda trae texto, tiene que tener al menos 2 caracteres; la página se limita a 50 resultados (20 por defecto)."
      ]
    },
    {
      "name": "membership",
      "key_files": [
        "src/main/java/com/example/library/members/MemberService.java",
        "src/main/java/com/example/library/members/Member.java",
        "src/main/java/com/example/library/members/MemberType.java"
      ],
      "rules": [
        "El email se normaliza (sin espacios, en minúsculas) antes de comprobar que no haya otro socio con el mismo.",
        "Un socio estudiante tiene que registrarse con un email del dominio students.example.com.",
        "Un socio con préstamos activos no se puede dar de baja.",
        "Solo un socio activo puede pedir préstamos; uno dado de baja no vuelve a pedir."
      ]
    },
    {
      "name": "loan-lifecycle",
      "key_files": [
        "src/main/java/com/example/library/loans/LoanService.java",
        "src/main/java/com/example/library/loans/Loan.java"
      ],
      "rules": [
        "Cada tipo de socio tiene un máximo de préstamos activos: estudiante 3, público 5 y personal 10.",
        "El vencimiento es la fecha del préstamo más los días del tipo de socio: 14 para estudiante, 21 para público y 28 para personal.",
        "Las obras de referencia no se prestan, ni un título retirado o sin ejemplares en el estante.",
        "Un préstamo se renueva como máximo 2 veces, y cada renovación extiende el vencimiento un período completo desde el vencimiento actual.",
        "Un préstamo vencido no se renueva, y uno ya devuelto no se renueva ni se devuelve otra vez."
      ]
    },
    {
      "name": "overdue-fines",
      "key_files": [
        "src/main/java/com/example/library/loans/FineCalculator.java",
        "src/main/java/com/example/library/loans/LoanPolicy.java"
      ],
      "rules": [
        "Una devolución dentro del día de gracia no genera multa.",
        "Pasada la gracia, se cobran 25 centavos por cada día de atraso, contados desde el vencimiento.",
        "La multa tiene un tope de 1000 centavos por préstamo.",
        "La multa se calcula al devolver y queda registrada en el préstamo."
      ]
    },
    {
      "name": "due-reminders",
      "key_files": [
        "src/main/java/com/example/library/notifications/ReminderPolicy.java",
        "src/main/java/com/example/library/notifications/Notifier.java"
      ],
      "rules": [
        "Se manda un aviso de vence pronto exactamente 2 días antes del vencimiento.",
        "Un préstamo vencido recibe aviso de atraso a los 1, 7 y 14 días de atraso, y ningún otro día.",
        "El barrido diario corre por cron y solo revisa préstamos abiertos que vencen entre hace 14 días y dentro de 2."
      ]
    }
  ],
  "hard_cases": [
    {
      "case": "cycle",
      "paths": [
        "src/main/java/com/example/library/loans/LoanService.java",
        "src/main/java/com/example/library/members/MemberService.java"
      ],
      "detail": "loans importa Member, MemberRepository y MemberType; members importa LoanRepository: aristas loans -> members y members -> loans."
    },
    {
      "case": "large-module",
      "paths": ["src/main/java/com/example/library/books"],
      "detail": "10 archivos y 422 líneas (360 sin contar las vacías)."
    },
    {
      "case": "wildcard-import",
      "paths": ["src/main/java/com/example/library/loans/LoanService.java"],
      "detail": "import com.example.library.books.*; es la única fuente de la arista loans -> books."
    },
    {
      "case": "static-import",
      "paths": ["src/main/java/com/example/library/notifications/ReminderPolicy.java"],
      "detail": "import static com.example.library.common.Dates.today; es la única fuente de la arista notifications -> common."
    },
    {
      "case": "same-package-no-import",
      "paths": [
        "src/main/java/com/example/library/loans/LoanService.java",
        "src/main/java/com/example/library/books/BookService.java"
      ],
      "detail": "Clases del mismo paquete (Loan, LoanRepository, FineCalculator, LoanPolicy; Book, Isbn, BookSearch) usadas sin import: no hay arista."
    },
    {
      "case": "qualified-name-no-import",
      "paths": [
        "src/main/java/com/example/library/books/BookService.java",
        "src/main/java/com/example/library/books/Book.java"
      ],
      "detail": "com.example.library.notifications.Notifier como tipo de campo y de parámetro, y {@link com.example.library.loans.LoanService} en un javadoc, sin import: no hay aristas books -> notifications ni books -> loans."
    },
    {
      "case": "external-lookalike-package",
      "paths": ["src/main/java/com/example/library/members/MemberService.java"],
      "detail": "Guava (com.google.common.base.Strings y los import static de Preconditions) se parece al paquete local com.example.library.common, pero no existe en el fixture: no hay arista members -> common."
    },
    {
      "case": "tests-import-other-packages",
      "paths": [
        "src/test/java/com/example/library/loans/LoanServiceTest.java",
        "src/test/java/com/example/library/notifications/ReminderPolicyTest.java"
      ],
      "detail": "Los tests importan de books, members, notifications y common, pero no son módulos ni originan aristas."
    },
    {
      "case": "root-module-with-submodules",
      "paths": ["src/main/java/com/example/library/LibraryApplication.java"],
      "detail": "La carpeta raíz del paquete es un módulo propio, distinto de sus subcarpetas, con la arista library -> loans por LoanPolicy."
    },
    {
      "case": "synthetic-data-no-secrets",
      "paths": [
        "src/main/resources/application.yml",
        "src/test/java/com/example/library/members/MemberServiceTest.java"
      ],
      "detail": "Emails @example.com y @students.example.com, ISBN de ejemplo de la norma, y la contraseña de la base leída del entorno (${DB_PASSWORD})."
    }
  ]
}
```
