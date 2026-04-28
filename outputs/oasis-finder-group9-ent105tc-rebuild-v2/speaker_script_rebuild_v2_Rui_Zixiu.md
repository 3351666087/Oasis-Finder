# Oasis Finder Group 9 Speaker Script

Presenters: Rui Huang and Zixiu Wang
Target length: about 8 minutes
Split: Rui slides 1-6, Zixiu slides 7-12

## Rui Huang

### Slide 1 - Opening

Good morning everyone. We are Group 9, and our product is Oasis Finder.

The most important point is: Oasis Finder is not only a dashboard. It is a commercial method for merchants. When a merchant shows a product's supply-chain route and evidence, users may feel the product is safer and more trustworthy, so they may be more willing to buy.

Our thesis is simple: we do not ask users to trust a slogan. We let them inspect the chain behind the product.

I am Rui Huang. I will explain the research question, why merchants may earn more from this method, what data should be shown, and how we built the product. Then Zixiu will explain the merchant image interface, GitHub evidence, technical capability, and validation plan.

### Slide 2 - Questionnaire Focus

This slide is about our revised research focus.

The question is not only whether people like supply-chain information. The real business question is: if a merchant shows supplier nodes, time, place, quality checks, temperature, and batch movement, will users become more likely to buy?

Our questionnaire direction shows that transparency matters more for products where people worry about freshness or safety. For example, cake needs ingredient and allergy trust. Seafood needs origin and cold-chain proof. Meat, dairy, and ready-to-eat meals need expiry, inspection, and handling evidence.

So our focus is buyer behavior. Supply-chain transparency is not decoration. It is a purchase decision cue.

### Slide 3 - Why It Pays

This slide explains why merchants can benefit.

Traditional advertising often says: trust us. Oasis Finder changes the message to: inspect the evidence.

The mechanism has four steps. First, evidence is shown, such as supplier map, batch, timestamp, location, temperature, and certificate. Second, consumer risk drops because the product becomes less uncertain. Third, perceived value rises because the customer can justify the purchase. Fourth, merchant revenue can improve through better conversion, premium trust, and repeat intention.

In simple words, this makes advertising more credible. The merchant is not only saying the product is safe. The merchant is showing why it is safe.

### Slide 4 - What Merchants Should Show

For this method to work, merchants should show specific data fields.

At minimum, we recommend six types of evidence.

First, product identity: SKU, QR code, batch ID, or lot ID. Second, place: supplier, plant, warehouse, and store. Third, time: harvest, production, receiving, shipping, and arrival. Fourth, condition: temperature, breach minutes, freshness, and shelf life. Fifth, quality proof: inspection result, package score, residue or pathogen checks. Sixth, evidence owner: supplier, auditor, carrier, certificate link, or evidence hash.

We also make the responsibility clear. Oasis Finder provides the interface and data slots, but we do not guarantee merchant data authenticity. Supplier records, QR events, IoT logs, and third-party audits should validate the claims.

### Slide 5 - Build Story

This is our build story.

At the beginning, our idea was broad: supply-chain transparency. Then the coursework and feedback pushed us to make it more practical. We realized the key question is not just showing a beautiful supply-chain map. The key question is whether the evidence can make users more likely to buy.

So we built the data foundation. Our system connects facilities, supplier lots, product batches, shipments, risk, demand, and quality inspections. Then we built the desktop interface with dashboard, mesh, traceability, forecasting, and scenario pages.

Now we improved the product layer. The user can start from a product, click it, and see that product's route and evidence.

### Slide 6 - Product Shelf Homepage

This slide shows the new homepage.

Instead of starting with a complicated network table, the user first sees a retail-style product shelf. It shows product name, category, price, proof score, and a simple consumer claim.

The page is designed to be more friendly. Step one: put the product first, because shoppers first want to know what they are buying. Step two: connect the batch, because the system must know which batch and QR code the product belongs to. Step three: add proof images, like product photo, origin photo, quality certificate, and cold-chain log. Step four: explain the route, so users can see time, place, temperature, quality, and evidence ownership.

This is also why the page is more useful for marketing. It starts from the buying moment, not from an internal operations table.

Now I will pass the microphone to Zixiu. Zixiu will explain the image interfaces we leave for merchants, and how the technical system supports the product.

## Zixiu Wang

### Slide 7 - Vendor Media Interface

Thanks, Rui.

This slide explains the merchant image interface in very simple terms.

Real stores need images. A customer does not want to only read database fields. So we leave four image slots for merchants.

The first slot is product photo. The merchant can upload a packshot or shelf photo. This helps shoppers recognize the exact item. The second slot is origin image. The merchant can upload a farm, supplier, or source image. This makes the source visible, not abstract.

The third slot is QC certificate. The merchant can upload an inspection certificate or lab result. This makes safety claims reviewable. The fourth slot is cold-chain log. The merchant can upload a temperature chart or delivery log. This helps users understand freshness.

Before real merchant assets are uploaded, we use icon-style placeholders. This means the interface is ready, and the merchant can replace the placeholders later.

### Slide 8 - GitHub And Data Responsibility

This slide clarifies GitHub and responsibility.

Our code is open-source on GitHub, so reviewers can inspect our method. The repository shows the system structure, data schema, UI, and evidence assets.

But open-source code does not automatically make merchant data true. If CP Group or any other large company uses our interface, they still need to provide real evidence from supplier records, QR events, IoT logs, and audits.

So the boundary is clear. Oasis Finder provides the tool and the data slots. The merchant is responsible for the truth of the data they put into those slots.

### Slide 9 - Technical Capability

This slide shows that the product is not just a static poster.

Behind the friendly product shelf, we have a working digital twin. The prototype contains 97 facilities, 200 active supply links, 418 finished-goods batches, and a 30-day forecasting horizon.

It also includes model outputs. The risk model has RMSE 5.83 and MAE 4.65, and the forecast MAPE is 4.81 percent.

So the consumer-facing interface can be connected to operational data. This is important because a merchant needs the evidence to update from real batch, shipment, and quality records.

### Slide 10 - Merchant Value

Now we return to the business value.

Oasis Finder can help merchants because it makes premium quality easier to believe before purchase. The value model on this slide is indexed. It is not a guaranteed financial forecast, but it shows the logic.

The first value is conversion. Users face less uncertainty at the exact buying moment. The second value is premium trust. Traceability can support perceived value and willingness to pay. The third value is retention. Clearer evidence may reduce disputes and support repeat intention.

The advertising message becomes very simple: scan the product journey, not just the package.

### Slide 11 - Pilot A/B Test

This slide shows the next validation step.

After the questionnaire signal, we should test real purchase behavior. The setup is simple: same product, same price, two product pages. One page is the normal baseline page. The other page uses Oasis Finder to show supply-chain evidence.

The product cells should include cake, seafood, meat, dairy, and ready-to-eat meals, because freshness and safety concerns are high.

The outcome metrics should include QR scan rate, evidence-panel clicks, add-to-cart, purchase conversion, willingness-to-pay, and repeat intention.

The decision rule is clear: we adopt the method when purchase lift and trust lift both improve without making the page confusing.

### Slide 12 - Closing

To close, Oasis Finder is a transparent-commerce method.

It combines open code, clear data fields, merchant image slots, and inspectable product evidence. It is especially suitable for a CP Group-style partner because CP Group has food, supply-chain, and retail channels. But it is not limited to CP Group. Any merchant can use the same structure if they can provide SKU, batch, lot, shipment, quality, image, and audit evidence.

Our final line is: we do not ask users to trust a slogan. We let them inspect the chain behind the product.

Thank you. We are happy to take questions.

## Handover Line

Rui to Zixiu:

"Now I will pass the microphone to Zixiu. Zixiu will explain the image interfaces we leave for merchants, and how the technical system supports the product."

## Emergency Cues

Rui:

1. Product = a method for merchants to show supply-chain evidence.
2. Research question = does evidence increase buying probability?
3. Strong products = cake, seafood, meat, dairy, ready-to-eat.
4. Merchant value = lower risk, higher trust, better conversion.
5. New homepage = product shelf first, then route and evidence.

Zixiu:

1. Four image slots = product photo, origin image, QC certificate, cold-chain log.
2. Placeholder icons = interface is ready before real merchant assets arrive.
3. GitHub = open code, not merchant data guarantee.
4. Technical proof = 97 facilities, 200 links, 418 batches, 30 forecast days.
5. Closing = inspect the chain, not just the slogan.
