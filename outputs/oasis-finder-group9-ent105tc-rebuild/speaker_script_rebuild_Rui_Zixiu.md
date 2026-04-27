# Oasis Finder Rebuilt Presentation Script

Presenters: Rui Huang and Zixiu Wang  
Target: about 8 minutes  
Split: Rui slides 1-5, Zixiu slides 6-11

## Rui Huang

### Slide 1 - Opening

中文提示：先把产品重新定义成“商家展示供应链以提高购买概率的方法”。

Good morning everyone. We are Group 9, and our product is Oasis Finder.

After teacher feedback, we reframed the project. Oasis Finder is not just a software feature. It is a commercial method: when a merchant shows a product's supply-chain structure, does the user become more likely to buy?

Our thesis is that credible supply-chain evidence reduces perceived risk and increases purchase confidence, especially for perishable or high-trust foods.

I am Rui Huang. I will cover the research question, the buying logic, and how we built the product. Then Zixiu Wang will show the product proof, GitHub evidence, and merchant value.

### Slide 2 - Questionnaire

中文提示：第二页替代旧 strategic groups。重点是“买不买”的问题。

The old second slide focused on strategic groups. We removed that because the real business question is more direct.

Our questionnaire asks: if a merchant shows supplier nodes, time, place, quality checks, temperature, and batch movement, are users more likely to buy?

The chart is now backed by CSV data. The directional result is strongest for products where users worry about freshness and safety. For example, cake and bakery products need ingredient and allergy trust. Seafood needs cold-chain and origin proof. Meat, dairy, and ready-to-eat meals need safety, expiry, inspection, and handling evidence.

So our research focus is now buyer behavior: transparency is not decoration. It is a decision cue.

### Slide 3 - Why It Pays

中文提示：解释为什么商家用这个做广告会赚钱。

This slide explains why merchants can benefit.

Traditional advertising often says: trust us. Oasis Finder changes the message to: inspect the evidence.

The mechanism has four steps. First, evidence is shown: supplier map, batch, timestamp, location, temperature, and certificate. Second, consumer risk drops because the product becomes less uncertain. Third, perceived value rises because the customer can justify the purchase. Fourth, merchant revenue can improve through better conversion, premium tolerance, and repeat intention.

This is why supply-chain transparency can work as advertising. It turns an invisible quality claim into a visible proof point.

### Slide 4 - What To Show

中文提示：这里回答老师说的“点击节点后到底显示什么变量”。

For the product method to be useful, merchants should show specific data fields.

At minimum, we recommend product identity, place, time, condition, quality proof, and evidence owner.

Product identity means SKU, GTIN, QR code, batch, or lot ID. Place means supplier, plant, warehouse, and location code. Time means harvest, production, receiving, shipping, and arrival. Condition means temperature, breach minutes, freshness, and shelf life. Quality proof means inspection result, package score, and residue or pathogen checks. Evidence owner means supplier, auditor, carrier, certificate URI, or evidence hash.

But we also make a clear disclaimer. Oasis Finder provides the interface, schema, and API slots. We do not guarantee merchant data authenticity. Supplier records, QR events, IoT logs, and third-party audits should validate the claims.

### Slide 5 - Build Story

中文提示：讲故事：我们怎么从作业做到产品。

This is our build story.

In Week 6, open coding helped us realize that QR traceability and analytics are stronger than superficial visibility. In the INF work, we built the data model: 17 tables connect facilities, lots, batches, shipments, risk, and demand.

Then we built a PySide6 control tower with dashboard, mesh, traceability, forecasting, and scenario pages. Finally, after teacher feedback, we improved the product layer: every supply-chain node can now expose stage variables and preset values.

So the project story is: question, evidence, system, proof.

That is the research logic and build story. Now I will pass the microphone to Zixiu, who will show the product evidence and why merchants benefit.

## Zixiu Wang

### Slide 6 - Node Click Proof

中文提示：接住 Rui 的话，重点展示节点点击后的变量。

Thanks, Rui. I will start with the product proof.

This screenshot shows the revised Network Mesh. When the user clicks a node, the system does not only show a map. It shows concrete stage data.

For example, node FAC-L1-003 shows location, time, stage, quality, temperature, and risk. We can see the location is Fuzhou, the time is a quality checkpoint, the stage connects ingredient lot and cold-chain shipment, and the values include traceability percentage, temperature range, breach minutes, and risk score.

This is the key product improvement: users can inspect the chain behind the product instead of only reading a marketing sentence.

### Slide 7 - GitHub And Interface

中文提示：开源不等于替商家背书。

This slide clarifies the GitHub and data responsibility.

Our code is open-source on GitHub, so reviewers can inspect our method. The health gate passed, which means the local database, traceability flow, forecast flow, and scenario checks can run.

But open-source code does not automatically make merchant data true. Merchant data should come from supplier records, QR events, IoT logs, and audits.

We also leave an optional AI layer. AI can summarize evidence for users, but it should not certify the truth alone.

### Slide 8 - Technical Capability

中文提示：用数字证明不是静态PPT。

The product method is supported by a working digital twin.

The prototype includes 97 facilities, 200 active links, 418 traceable batches, and a 30-day forecasting horizon.

It also includes model outputs. The risk model has RMSE 5.83 and MAE 4.65, and the forecast MAPE is 4.81 percent.

These numbers show technical capability. The transparency layer can be connected to operational data, not just a static product poster.

### Slide 9 - Merchant Value

中文提示：回到商业收益，别讲太技术。

Now we return to the merchant value.

Oasis Finder can help merchants because it makes premium quality easier to believe before purchase.

The value model is indexed, not a guaranteed forecast. The idea is that a transparent product page can improve conversion, support premium trust, and reduce complaints or disputes.

For advertising, the message becomes very simple: scan the product journey, not just the package.

### Slide 10 - Pilot A/B Test

中文提示：这一页讲下一步怎么证明真的能提高商家收益。

This slide shows the next validation step: a merchant A/B test.

After the questionnaire signal, we should test real purchase behavior. The setup is simple: same product, same price, two product pages. One page is the baseline page. The other page uses Oasis Finder to show supply-chain evidence.

The product cells should include cake, seafood, meat, dairy, and ready-to-eat meals because freshness and safety concerns are high.

The outcome metrics should include QR scan rate, evidence-panel clicks, add-to-cart, purchase conversion, willingness-to-pay, and repeat intent.

The decision rule is also clear: adopt the method when purchase lift and trust lift both improve without increasing confusion.

### Slide 11 - Close

中文提示：最后一句慢一点。

To close, Oasis Finder is a transparent-commerce method. It combines open code, clear data fields, and inspectable product evidence.

The business value is that merchants can move from a trust slogan to evidence-based advertising. The technical value is that the evidence can be connected to a real data model and a clickable interface.

Our final line is: we do not ask users to trust a slogan. We let them inspect the chain behind the product.

Thank you. We are happy to take questions.

## Handover Line

Rui to Zixiu:

"That is the research logic and build story. Now I will pass the microphone to Zixiu, who will show the product evidence and why merchants benefit."

## Emergency Cues

Rui:

1. Product = method for merchants to show supply-chain evidence.
2. Research question = does transparency raise buying probability?
3. Strongest products = cake, seafood, meat, dairy, ready-to-eat.
4. Merchant value = evidence reduces risk and raises perceived value.
5. Build story = Week 6 -> INF data model -> control tower -> node click proof.

Zixiu:

1. Node click = location, time, stage, quality, temperature, risk.
2. GitHub = open code, not merchant truth guarantee.
3. Technical proof = 97 facilities, 200 links, 418 batches, 30 forecast days.
4. Merchant ROI = conversion, premium trust, fewer disputes.
5. Closing = inspect the chain, not just the slogan.
