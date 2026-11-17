# UML in PlantUML

Keep the style in one shared file that every diagram includes by relative path (the `diagram-design` skill has the `skinparam` lines in its tool styling reference), for example `!include ../style.iuml`. Never `!include` a URL. Each diagram starts with the marker `' exo-style: neutral`, or `brand <hash>`. Names and paths are invented.

To mark the element in focus, add a stereotype and style it once in the shared file:

```text
skinparam class {
  BackgroundColor<<focus>> #0A58A8
  BorderColor<<focus>> #0A58A8
  FontColor<<focus>> #FFFFFF
  StereotypeFontColor<<focus>> #FFFFFF
}
hide <<focus>> stereotype
```

The same pattern works for `participant`, `state`, `usecase` and `rectangle`. For a single element, an inline color also works: `class Order #0A58A8;text:FFFFFF`.

## Class

```text
@startuml
' exo-style: neutral
!include ../style.iuml
title An order owns its lines and is paid through one gateway interface

' [Code] services/orders/app/models.py:12
class Order <<focus>> {
  +id: OrderId
  +status: Status
  +place()
  +cancel()
}
' [Code] services/orders/app/models.py:40
class OrderLine {
  +sku: Sku
  +quantity: int
}
' [Code] services/orders/app/payments/port.py:5
interface PaymentGateway {
  +charge(amount: Money): Receipt
}
' [Code] services/orders/app/payments/card.py:9
class CardGateway

Order "1" *-- "1..*" OrderLine : contains
Order ..> PaymentGateway : charged through
CardGateway ..|> PaymentGateway
hide empty members
@enduml
```

## Sequence

```text
@startuml
' exo-style: neutral
!include ../style.iuml
title A timed-out payment is retried once, then the order is released

actor Customer as C
participant "Orders API" as O <<focus>>
participant "Payment client" as P
participant "Payment provider" as X

' [Code] services/orders/app/routes.py:22
C -> O : Place order (cart)
O -> P : charge(amount, idempotency key)
P -> X : Create charge
alt answer within 5 s
  X --> P : Charged
  P --> O : Receipt
  O --> C : Order confirmed
else timeout
  P -> X : Create charge (same key)
  opt still no answer
    P --> O : Timeout
    O --> C : Order released, please try again
  end
end
note over P, X : The idempotency key makes the retry safe
@enduml
```

- Arrows: `->` synchronous call, `-->` reply, `->>` asynchronous message.
- `autonumber` when the audience refers to steps; `== Phase ==` separators for long scenarios.

## Activity

```text
@startuml
' exo-style: neutral
!include ../style.iuml
title Shipping waits for both the label and the packing

|Warehouse floor|
start
:Pick the order;
fork
  |Shipping office|
  :Print the label;
fork again
  |Warehouse floor|
  :Pack the parcel;
end fork
|Shipping office|
:Hand over to the carrier;
stop
@enduml
```

- Decisions: `if (Stock available?) then (yes)` … `else (no)` … `endif`. Loops: `repeat` … `repeat while (more items?)`.
- Lanes: `|Name|` before the actions of that lane.

## State machine

```text
@startuml
' exo-style: neutral
!include ../style.iuml
title An order can be cancelled until the warehouse starts picking it

state "Pending payment" as Pending
state Paid <<focus>>
[*] --> Pending
Pending --> Paid : payment accepted
Pending --> Cancelled : customer cancels
Paid --> Cancelled : customer cancels [picking not started]
Paid --> Picking : warehouse starts picking
Picking --> Shipped : parcel handed over / notify customer
Shipped --> [*]
Cancelled --> [*]
@enduml
```

Composite states: `state Open { ... }`. Fork and join: `state fork1 <<fork>>`, `state join1 <<join>>`.

## Use case

```text
@startuml
' exo-style: neutral
!include ../style.iuml
title Customers order and track; support agents refund
left to right direction

actor Customer
actor "Support agent" as Agent
actor "Payment provider" as Provider <<system>>

rectangle "Online shop" {
  usecase "Place order" as Place
  usecase "Track order" as Track
  usecase "Refund payment" as Refund
}

Customer -- Place
Customer -- Track
Agent -- Refund
Place -- Provider
Refund -- Provider
@enduml
```

`include` and `extend`: `Place .> (Check stock) : <<include>>`, `(Apply voucher) .> Place : <<extend>>`. Use them only when they explain something.

## Render

When PlantUML is installed: `plantuml -tsvg docs/diagrams/*.puml`. Otherwise give that command and keep the source; most documentation builds that support PlantUML render it on their own.
