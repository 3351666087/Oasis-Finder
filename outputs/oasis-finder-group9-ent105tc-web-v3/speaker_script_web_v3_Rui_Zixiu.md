# Oasis Finder Group 9 Speaker Script

Target length: about 8 minutes
Speakers: Rui Huang first half, Zixiu Wang second half

## Slide 1 - Rui Huang

Good morning everyone. We are Group 9, and our product is called Oasis Finder.

The main question today is very simple: will shoppers be more likely to buy a fresh-food product if the merchant clearly shows the supply chain behind that product?

So Oasis Finder is not just a dashboard. It is a merchant-facing transparency method. The user first sees the product, then the product can be split into components, and then the user can inspect evidence such as supplier route, batch, time, place, temperature, and quality.

Our GitHub repository is open-source, so the code and workflow can be reviewed. But the important business idea is this: instead of asking users to just trust a slogan, we let them inspect the chain behind the product.

## Slide 2 - Rui Huang

After the teacher feedback, we changed the focus of the presentation.

Before, we talked too much like a general supply-chain intelligence platform. Now the research question is more direct: if a merchant displays supply-chain evidence on a product page, does it increase the probability that users want to buy?

Our questionnaire direction shows that users are especially interested in transparency for high-trust food categories. Cake or bakery products are a good example, because ingredients and freshness are hard to judge only from appearance. Chilled meat, dairy, fresh produce, and ready meals also need trust, because users care about safety, storage, and freshness.

So the chart is not saying transparency is magic. It says transparency is a useful buying cue when risk and uncertainty are high.

## Slide 3 - Rui Huang

This slide explains the user experience in simple language.

We redesigned the frontend to be closer to a retail app, like Hema or Sam's Club. The shopper does not start from a technical network table. They start from product cards: product name, category, price, and proof score.

Then the product can be split into modules. For example, a cake can be split into cake base and cream. In our demo product, chilled chicken can be split into protein input, packaging film, carton, QR label, and cold-chain pack.

Finally, the user can inspect the route. They can stay on the whole-product supply chain, or click a component and see that component's own supply chain.

The promise is: customers do not need to understand databases. They only need to see where the product came from, when it moved, and why it is safe enough to buy.

## Slide 4 - Rui Huang

Technically, we made a major rebuild.

The system is now completely browser-based. We removed PySide6 and rebuilt the product as a frontend and backend system.

The merchant backend is a React admin route. It allows merchants to edit product data and upload or paste evidence images.

The FastAPI service provides REST endpoints, media upload, and a WebSocket live-update channel.

The MySQL digital twin stores products, batches, supplier lots, shipments, risk, and inspections.

The customer frontend is also React. It displays product cards, module dissection, supply-chain route, and evidence variables.

The key point is that the backend and frontend can run together. When the backend changes, the frontend can receive a live update.

## Slide 5 - Rui Huang

Here is the customer frontend screenshot.

Step one: the user starts with product cards. This makes the interface much more friendly, because it looks like a shopping page, not like an enterprise dashboard.

Step two: the page gives a plain guide. It tells users to choose a product, split it into modules, and then inspect evidence.

Step three: after choosing a SKU, the system loads the matching route, modules, and evidence.

This is the part that turns Oasis Finder into a marketing method. The merchant can use the product page itself as the advertisement, because the product page contains proof.

Now I will hand over to Zixiu. Zixiu will explain the component-level proof, the merchant backend, and why this creates business value.

## Slide 6 - Zixiu Wang

Thank you, Rui.

This slide shows what happens after the user clicks one component.

In the screenshot, the selected component is Broiler Protein Input. The route switches from the whole-product supply chain to the supply chain of this one module.

The important part is the variable panel. The user can see the module name, supplier city, lot number, received date, inspection score, and traceability percentage.

So the system is not only drawing a pretty route. It is showing real fields that a merchant should prepare.

There is also an animation when switching between whole product and module view. This helps the user understand which layer of evidence they are looking at.

## Slide 7 - Zixiu Wang

This is the merchant backend.

The backend is designed for merchants, so the workflow is very direct.

First, select the SKU from the product list.

Second, edit product data, including product name, category, price, shelf life, and storage temperature.

Third, upload or paste evidence images. We reserved four image slots: product photo, origin or farm image, quality certificate, and cold-chain proof.

At the moment, the interface uses icon-style placeholders, because real merchants need to insert their own images later. But the interface and API slots are already prepared.

After the merchant saves data or media, the customer frontend can refresh through the live update channel.

## Slide 8 - Zixiu Wang

This slide is about data responsibility.

Our code is open-source, and we provide the interface, schema, API, and media slots. But we do not guarantee the truthfulness of a merchant's data.

In a real pilot, merchants should provide product identity, critical tracking events, location, condition, quality proof, and evidence owner.

For example, the system should know the SKU, QR code, batch ID, lot ID, production time, shipping time, temperature range, inspection result, and certificate source.

We recommend validating these fields with QR events, IoT logs, supplier records, ERP or WMS systems, and third-party audits.

This is why Oasis Finder is useful but also responsible. It gives the display method, but the company still needs to prove its claims.

## Slide 9 - Zixiu Wang

Now we connect the product to CP Group.

CP Group is a strong pilot partner because it has agro-food, retail, distribution, e-commerce, and traceability contexts. That means a single product page can connect upstream production, processing, cold-chain movement, and retail display.

But Oasis Finder is not limited to CP Group. Any merchant can use the same schema if it can provide product, batch, supplier, shipment, inspection, and media proof.

The merchant value is also clear. Transparency can increase trust, support evidence-based advertising, improve conversion, and reduce complaints caused by uncertainty.

The next commercial validation would be an A/B test: one baseline product page, and one Oasis Finder evidence page.

## Slide 10 - Zixiu Wang

To close, this is what we can prove today.

First, the architecture has been rebuilt. PySide6 is removed, and the system now uses FastAPI, React/Vite, and MySQL.

Second, the frontend works as a customer product page with product shelf, module dissection, route transition, and variable proof panel.

Third, the backend works as a merchant editor with data fields, image slots, and live-update logic.

Fourth, we validated it locally. Python compile passed, health check passed, frontend build passed, and API smoke test passed.

Our final line is: we do not ask users to trust a slogan. We let them inspect the chain behind the product.

Thank you. We are ready for questions.
