# C4 templates

Each template uses the neutral values of `.exo/shared/executive-style.md`; replace them with the brand's when `.exo/brand.json` sets them. The init line and the class definitions are in the `diagram-design` skill (its tool styling reference); they are shortened here to the class lines. Names and paths are invented.

## System context (Mermaid)

```mermaid
%% exo-style: neutral
flowchart LR
    accTitle: The order platform serves customers and depends on two outside services
    accDescr: Customers and support agents use the order platform. It takes payments through a payment provider and sends orders to the warehouse system.

    %% [Code] services/web/src/routes.ts:10 (customer routes)
    customer(["Customer<br/>[Person]"])
    %% [Code] services/admin/app/roles.py:5 (support role)
    agent(["Support agent<br/>[Person]"])
    platform["Order platform<br/>[Software system]<br/>Takes and tracks orders"]
    %% [Code] services/orders/app/payments_client.py:20 (PAYMENTS_BASE_URL)
    payments["Payment provider<br/>[Software system]"]
    %% [Inferred: low] services/orders/app/events.py:12 (topic orders.created)
    warehouse["Warehouse system (inferred)<br/>[Software system]"]

    customer -->|"Places and tracks orders in"| platform
    agent -->|"Handles refunds in"| platform
    platform -->|"Takes payments through"| payments
    platform -.->|"Sends orders to"| warehouse

    classDef focus fill:#0a58a8,stroke:#0a58a8,color:#ffffff
    classDef person fill:#2f3b4c,stroke:#2f3b4c,color:#ffffff
    classDef external fill:#e9edf1,stroke:#7d8794,color:#1d2125
    classDef unconfirmed stroke-dasharray:5 5
    class platform focus
    class customer,agent person
    class payments,warehouse external
    class warehouse unconfirmed
```

## Containers (Mermaid)

```mermaid
%% exo-style: neutral
flowchart LR
    accTitle: Two APIs behind one gateway serve the shop front end
    accDescr: Customers use the shop front end, which calls the API gateway. The gateway routes to the Orders API and the Catalog API. The Orders API stores orders in its database, takes payments through the payment provider and publishes order events.

    customer(["Customer<br/>[Person]"])
    subgraph platform["Order platform"]
        %% [Code] services/web/package.json:5
        web["Shop front end<br/>[Container: TypeScript, React]"]
        %% [Code] deploy/gateway/routes.yaml:3
        gateway["API gateway<br/>[Container: reverse proxy]"]
        %% [Code] services/orders/pyproject.toml:8
        orders["Orders API<br/>[Container: Python, FastAPI]"]
        %% [Code] services/catalog/pom.xml:12
        catalog["Catalog API<br/>[Container: Java, Spring Boot]"]
        %% [Code] services/orders/app/db.py:9 (ORDERS_DB_URL)
        ordersdb[("Orders database<br/>[Container: PostgreSQL]")]
        %% [Code] services/orders/app/events.py:12
        events[["Order events<br/>[Queue]"]]
    end
    payments["Payment provider<br/>[Software system]"]

    customer -->|"Shops in [HTTPS]"| web
    web -->|"Calls [HTTPS/JSON]"| gateway
    gateway -->|"Routes order calls to [HTTP]"| orders
    gateway -->|"Routes catalog calls to [HTTP]"| catalog
    orders -->|"Reads and writes [SQL]"| ordersdb
    orders -->|"Takes payments through [HTTPS]"| payments
    orders -.->|"Publishes order events to [AMQP]"| events

    classDef inner fill:#e7f0fa,stroke:#0a58a8,color:#1d2125,stroke-width:1.5px
    classDef person fill:#2f3b4c,stroke:#2f3b4c,color:#ffffff
    classDef external fill:#e9edf1,stroke:#7d8794,color:#1d2125
    class web,gateway,orders,catalog,ordersdb,events inner
    class customer person
    class payments external
    style platform fill:#ffffff,stroke:#7d8794,stroke-dasharray:5 5,color:#5b6470
```

## Components of one container (Mermaid)

```mermaid
%% exo-style: neutral
flowchart TB
    accTitle: The Orders API keeps payment and event logic out of its routes
    accDescr: The routes call the order service, which uses the order repository, the payment client and the event publisher.

    gateway["API gateway<br/>[Container]"]
    subgraph orders["Orders API [Container: Python, FastAPI]"]
        %% [Code] services/orders/app/routes.py:1
        routes["Order routes<br/>[Component]"]
        %% [Code] services/orders/app/service.py:1
        service["Order service<br/>[Component]"]
        %% [Code] services/orders/app/repository.py:1
        repo["Order repository<br/>[Component]"]
        %% [Code] services/orders/app/payments_client.py:1
        payclient["Payment client<br/>[Component]"]
        %% [Code] services/orders/app/events.py:1
        publisher["Event publisher<br/>[Component]"]
    end
    db[("Orders database<br/>[Container: PostgreSQL]")]
    payments["Payment provider<br/>[Software system]"]

    gateway -->|"Calls"| routes
    routes -->|"Delegates to"| service
    service -->|"Stores orders with"| repo
    service -->|"Charges through"| payclient
    service -->|"Announces orders with"| publisher
    repo -->|"Reads and writes [SQL]"| db
    payclient -->|"Calls [HTTPS]"| payments

    classDef inner fill:#e7f0fa,stroke:#0a58a8,color:#1d2125,stroke-width:1.5px
    classDef external fill:#e9edf1,stroke:#7d8794,color:#1d2125
    class routes,service,repo,payclient,publisher inner
    class gateway,db,payments external
    style orders fill:#ffffff,stroke:#0a58a8,stroke-dasharray:5 5,color:#5b6470
```

## Deployment (Mermaid)

Nest the deployment nodes as subgraphs, outermost first. Use generic environment and region names in any piece that may leave the team.

```mermaid
%% exo-style: neutral
flowchart TB
    accTitle: Production runs the order platform in one cluster behind a load balancer
    accDescr: Traffic enters through a load balancer into a Kubernetes cluster that runs the gateway and the APIs; the orders database is a managed service in a private network.

    users(["Customers<br/>[Person]"])
    subgraph prod["Production [Environment]"]
        %% [Code] infra/network.tf:14
        lb["Load balancer"]
        subgraph cluster["Cluster [Kubernetes]"]
            %% [Code] deploy/k8s/gateway.yaml:1
            gw["API gateway x2"]
            %% [Code] deploy/k8s/orders.yaml:1
            ord["Orders API x3"]
        end
        subgraph private["Private network"]
            %% [Code] infra/database.tf:3
            pg[("Orders database<br/>[Managed PostgreSQL]")]
        end
    end

    users -->|"HTTPS"| lb
    lb -->|"Forwards to"| gw
    gw -->|"Routes to"| ord
    ord -->|"SQL over TLS"| pg

    classDef inner fill:#e7f0fa,stroke:#0a58a8,color:#1d2125,stroke-width:1.5px
    classDef person fill:#2f3b4c,stroke:#2f3b4c,color:#ffffff
    class lb,gw,ord,pg inner
    class users person
    style prod fill:#ffffff,stroke:#7d8794,stroke-dasharray:5 5,color:#5b6470
    style cluster fill:#f5f7f9,stroke:#7d8794,stroke-dasharray:5 5,color:#5b6470
    style private fill:#f5f7f9,stroke:#7d8794,stroke-dasharray:5 5,color:#5b6470
```

## The same levels in PlantUML

With the C4 library of PlantUML's standard library and the style lines of the `diagram-design` skill:

```text
@startuml
' exo-style: neutral
!include <C4/C4_Container>
title The Orders API takes orders, stores them and announces them

Person(customer, "Customer")
System_Boundary(platform, "Order platform") {
  ' [Code] services/web/package.json:5
  Container(web, "Shop front end", "TypeScript, React")
  ' [Code] services/orders/pyproject.toml:8
  Container(orders, "Orders API", "Python, FastAPI", "Takes and tracks orders")
  ' [Code] services/orders/app/db.py:9 (ORDERS_DB_URL)
  ContainerDb(ordersdb, "Orders database", "PostgreSQL")
  ' [Code] services/orders/app/events.py:12
  ContainerQueue(events, "Order events", "AMQP")
}
System_Ext(payments, "Payment provider")

Rel(customer, web, "Shops in", "HTTPS")
Rel(web, orders, "Sends orders to", "HTTPS/JSON")
Rel(orders, ordersdb, "Reads and writes", "SQL")
Rel(orders, payments, "Takes payments through", "HTTPS")
Rel(orders, events, "Publishes order events to", "AMQP")
SHOW_LEGEND()
@enduml
```

Use `C4_Context`, `C4_Component` or `C4_Deployment` for the other levels (`Deployment_Node` nests like the subgraphs above). Never include the library by URL.
