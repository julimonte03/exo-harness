# UML in Mermaid

Start each diagram with the init line of the executive style (the `diagram-design` skill has it in its tool styling reference) and the marker `%% exo-style: neutral`, or `brand <hash>`. They are left out below to keep the examples short. Names and paths are invented.

## Class: `classDiagram`

```mermaid
classDiagram
    accTitle: An order owns its lines and is paid through one gateway interface
    accDescr: Order contains one or more order lines and may have one payment. Payments go through the PaymentGateway interface, which the card gateway implements.

    %% [Code] services/orders/app/models.py:12
    class Order {
        +OrderId id
        +Status status
        +place()
        +cancel()
    }
    %% [Code] services/orders/app/models.py:40
    class OrderLine {
        +Sku sku
        +int quantity
    }
    %% [Code] services/orders/app/models.py:58
    class Payment {
        +Money amount
        +PaymentStatus status
    }
    %% [Code] services/orders/app/payments/port.py:5
    class PaymentGateway {
        <<interface>>
        +charge(Money amount) Receipt
    }
    %% [Code] services/orders/app/payments/card.py:9
    class CardGateway

    Order "1" *-- "1..*" OrderLine : contains
    Order "1" --> "0..1" Payment : paid by
    Payment ..> PaymentGateway : charged through
    CardGateway ..|> PaymentGateway

    style Order fill:#0a58a8,stroke:#0a58a8,color:#ffffff
```

- Relations: `<|--` inheritance, `*--` composition, `o--` aggregation, `-->` association, `..>` dependency, `..|>` realization. Multiplicity in quotes on each end, the label after a colon.
- The base theme colors every class with `primary_tint`; `style` sets the one in focus. Newer Mermaid versions also accept `classDef` in class diagrams; use it only when the project's renderer does.

## Sequence: `sequenceDiagram`

```mermaid
sequenceDiagram
    accTitle: A timed-out payment is retried once, then the order is released
    accDescr: The customer places an order; the Orders API charges through the payment client. If the provider does not answer in 5 seconds, the client retries once with the same idempotency key, and releases the order if there is still no answer.

    actor C as Customer
    participant O as Orders API
    participant P as Payment client
    participant X as Payment provider

    %% [Code] services/orders/app/routes.py:22
    C->>O: Place order (cart)
    %% [Code] services/orders/app/service.py:61
    O->>P: charge(amount, idempotency key)
    %% [Code] services/orders/app/payments_client.py:30
    P->>X: Create charge
    alt answer within 5 s
        X-->>P: Charged
        P-->>O: Receipt
        O-->>C: Order confirmed
    else timeout
        %% [Code] services/orders/app/payments_client.py:41
        P->>X: Create charge (same key)
        opt still no answer
            P-->>O: Timeout
            %% [Code] services/orders/app/service.py:88
            O-->>C: Order released, please try again
        end
    end
    Note over P,X: The idempotency key makes the retry safe
```

- Arrows: `->>` synchronous call, `-->>` reply, `-)` asynchronous message, `-x` a message that fails.
- `actor` draws a person; `participant` a box. `autonumber` adds step numbers when the audience will refer to them.
- Theme variables for sequences (actor fill, signal color, notes) are in the tool styling reference of the `diagram-design` skill.

## State machine: `stateDiagram-v2`

```mermaid
stateDiagram-v2
    accTitle: An order can be cancelled until the warehouse starts picking it
    accDescr: An order starts pending payment, becomes paid when the payment is accepted, and shipped when the warehouse ships it. It can be cancelled while pending or paid, but not after picking starts.

    %% [Code] services/orders/app/models.py:20 (Status)
    state "Pending payment" as Pending
    state "Picking" as Picking
    [*] --> Pending
    %% [Code] services/orders/app/service.py:70
    Pending --> Paid: payment accepted
    %% [Code] services/orders/app/service.py:102
    Pending --> Cancelled: customer cancels
    Paid --> Cancelled: customer cancels [picking not started]
    %% [Code] services/warehouse/app/consumer.py:33
    Paid --> Picking: warehouse starts picking
    Picking --> Shipped: parcel handed over / notify customer
    Shipped --> [*]
    Cancelled --> [*]

    classDef focus fill:#0a58a8,stroke:#0a58a8,color:#ffffff
    classDef highlight stroke:#a34f00,stroke-width:3px
    class Paid focus
    class Picking highlight
```

- `state "Long name" as Id` for names with spaces. Composite states: `state Open { ... }`. Fork and join: `state fork1 <<fork>>` and `state join1 <<join>>`.

## Activity: a `flowchart`

Mermaid has no activity diagram; a flowchart with lanes covers the light subset. Parallel work is a pair of narrow nodes, "In parallel" and "Both done".

```mermaid
flowchart TB
    accTitle: Shipping waits for both the label and the packing
    accDescr: After the order is picked, the label is printed and the parcel is packed in parallel; when both are done, the parcel is handed to the carrier.

    start(["Order picked"])
    split["In parallel"]
    subgraph office["Shipping office"]
        label["Print the label"]
    end
    subgraph floor["Warehouse floor"]
        pack["Pack the parcel"]
    end
    joined["Both done"]
    hand["Hand over to the carrier"]
    done(["Parcel shipped"])

    start --> split
    split --> label
    split --> pack
    label --> joined
    pack --> joined
    joined --> hand --> done

    classDef bar fill:#1d2125,stroke:#1d2125,color:#ffffff
    class split,joined bar
```

The legend says: "UML activity drawn as a flowchart: black bars are fork and join." When the project has PlantUML, its activity diagrams have real fork and join bars.

## Use case: an approximation with a `flowchart`

```mermaid
flowchart LR
    accTitle: Customers order and track; support agents refund
    accDescr: Customers place and track orders in the online shop. Support agents refund payments. Placing an order and refunding both use the payment provider.

    customer(["Customer<br/>[Actor]"])
    agent(["Support agent<br/>[Actor]"])
    subgraph shop["Online shop"]
        place(["Place order"])
        track(["Track order"])
        refund(["Refund payment"])
    end
    provider["Payment provider<br/>[Actor: system]"]

    customer --- place
    customer --- track
    agent --- refund
    place --- provider
    refund --- provider

    classDef person fill:#2f3b4c,stroke:#2f3b4c,color:#ffffff
    classDef usecase fill:#e7f0fa,stroke:#0a58a8,color:#1d2125
    classDef external fill:#e9edf1,stroke:#7d8794,color:#1d2125
    class customer,agent person
    class place,track,refund usecase
    class provider external
    style shop fill:#ffffff,stroke:#7d8794,color:#5b6470
```

The legend says: "Use cases approximated in a flowchart: stadiums inside the box are use cases; people and systems outside are actors."
