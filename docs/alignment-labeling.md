# Alignment labeling sheet

For each pair, decide one question: **is the NEW paragraph the same disclosure as the OLD one?**

- **Y**: yes. The same disclosure, reworded, updated (new numbers or dates), expanded, or shortened. A reader would call it a revision of the old paragraph, not a new topic.
- **N**: no. A different disclosure, even if it shares boilerplate phrasing ("could adversely affect our business…").
- **?**: you can't tell from these two texts.

Write the letter after **Label:**. Scores and the aligner's current decision are deliberately not shown, so they can't influence the label. They're in `tests/golden/alignment_sample.json`, keyed by item id.
Texts longer than 1,500 characters are cut, and the cut is marked.

## A01 · JPMORGAN CHASE & CO · 10K_7 · 2022-12-31 → 2023-12-31

**OLD:**

> •additions to goodwill associated with the acquisitions of Renovite Technologies, Inc. in the fourth quarter of 2022, Global Shares PLC and Figg, Inc. in the third quarter of 2022, and Frosch Travel Group, LLC and Volkswagen Payments S.A. in the second quarter of 2022.

**NEW:**

> •$1.1 billion to establish the allowance for the First Republic loans in the second quarter of 2023.

**Label:** N

**Note (optional):** 

## A02 · Apple Inc. · 10K_1A · 2024-09-28 → 2025-09-27

**OLD:**

> The Company’s business, reputation, results of operations, financial condition and stock price can be affected by a number of factors, whether currently known or unknown, including those described below. When any one or more of these risks materialize from time to time, the Company’s business, reputation, results of operations, financial condition and stock price can be materially and adversely affected.

**NEW:**

> If the Company is unable to compete successfully, its business, reputation, results of operations, financial condition and stock price can be materially adversely affected.

**Label:** Y

**Note (optional):** At least partially - It is basically saying the same thing, but one is more specific about "If the company is unable to compete sucessfully" which to me might mean there's a little more context. But both passages are basically saying in a given sitatuion, business could be affected.

## A03 · COCA COLA CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> Refer to Note 2 of Notes to Consolidated Financial Statements for additional information on the BodyArmor acquisition. Refer to Note 12 of Notes to Consolidated Financial Statements for additional information related to the tax litigation. Refer to Note 17 of Notes to Consolidated Financial Statements for additional information on the fairlife contingent consideration and the impairment charge. Refer to Note 19 of Notes to Consolidated Financial Statements for additional information on the

**NEW:**

> Net cash provided by operating activities for the years ended December 31, 2024 and 2023 was $6,805 million and $11,599 million, respectively, a decrease of $4,794 million, or 41%. This decrease was primarily driven by the $6.0 billion IRS Tax Litigation Deposit, an unfavorable impact due to foreign currency exchange rate fluctuations, higher other tax payments, increased charitable donations, and the reduced operating cash flows resulting from the refranchising of our bottling operations. The decrease was also impacted by additional annual incentive payments in the current year due to improved business performance in the prior year. These items were partially offset by strong cash operating results, the transfer of surplus international plan assets from pension trusts to general assets of the Company, payments in the prior year resulting from the buildup of inventory to manage potential supply chain disruptions, increased dividend payments from our equity method investees, and $167 million of the $275 million milestone payment for fairlife in the prior year. Refer to Note 2 of Notes to Consolidated Financial Statements for additional information on the refranchising of our bottling operations. Refer to Note 12 of Notes to Consolidated Financial Statements for additional information on the tax litigation. Refer to Note 14 of Notes to Consolidated Financial Statements for additional information on the pension transfer. Refer to Note 17 of Notes to Consolidated Financial Statem […cut]

**Label:** N

**Note (optional):** 

## A04 · GENERAL ELECTRIC CO · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> For 2017, restructuring and other charges were $4.1 billion of which approximately $2.4 billion was reported in cost of products/services and $1.6 billion was reported in selling, general and administrative expenses (SG&A). These activities were primarily at Corporate, Power and Oil & Gas. Cash expenditures for restructuring and other charges were approximately $2.0 billion for the twelve months ended December 31, 2017. Of the total $4.1 billion restructuring and other charges, $0.8 billion was recorded in the Oil & Gas segment, which amounted to $0.7 billion net of noncontrolling interest.

**NEW:**

> Cash expenditures for restructuring and other charges were approximately $1.2 billion, $1.5 billion and $1.5 billion for the years ended December 31, 2019, 2018 and 2017, respectively.

**Label:** Y

**Note (optional):** Seems similar in the type of disclosure. But NEW include a number of years, OLD referring to only 2017.

## A05 · PFIZER INC · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> •an increase in costs related to implementing our cost-reduction/productivity initiatives, partially offset by:

**NEW:**

> (e)Includes employee termination costs, asset impairments and other exit costs related to our cost-reduction and productivity initiatives not associated with acquisitions. See Note 3.

**Label:** ?

**Note (optional):** It seems very close. In essence it's NO but given limited context, the two are very similar

## A06 · COCA COLA CO · 10K_7 · 2019-12-31 → 2020-12-31

**OLD:**

> 7 Includes net tax expense of $8 million (or a 0.1 percent impact on our effective tax rate) related to the finalization of our accounting related to the Tax Reform Act.

**NEW:**

> 2 Includes net tax expense of $431 million (or a 4.4 percent impact on our effective tax rate) primarily related to changes in judgment on specific tax positions due to the Opinion and amounts required to be recorded for changes to other uncertain tax positions, including interest and penalties. Also includes a tax benefit of $107 million (or a 1.1 percent impact on our effective tax rate) related to changes in our assessment of certain valuation allowances and a net tax benefit of $135 million (or a 1.4 percent impact on our effective tax rate) related to domestic return to provision adjustments and other tax items.

**Label:** Y

**Note (optional):** Seems to be the same sort of disclosure here just rewaroded, expanded, new numbers

## A07 · Walmart Inc. · 10Q_P1_2 · 2025-04-30 → 2026-04-30

**OLD:**

> Effective February 20, 2025, the Company approved the fiscal 2026 annual dividend of $0.94 per share, a 13% increase over the fiscal 2025 annual dividend of $0.83 per share. For fiscal 2026, the annual dividend was or will be paid in four quarterly installments of $0.235 per share, according to the following record and payable dates:

**NEW:**

> Effective February 19, 2026, the Company approved the fiscal 2027 annual dividend of $0.99 per share, an increase over the fiscal 2026 annual dividend of $0.94 per share. For fiscal 2027, the annual dividend was or will be paid in four quarterly installments of $0.2475 per share, according to the following record and payable dates:

**Label:** Y

**Note (optional):** 

## A08 · FORD MOTOR CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> The remote work arrangements that we implemented in 2020 remain in place in most locations. Our remote work arrangements have been designed to allow for continued operation of non-production business-critical functions, including financial reporting systems and internal control. Our controls and procedures have incorporated remote work arrangements using appropriate digital tools.

**NEW:**

> COVID-19. The impact of COVID-19, including changes in consumer behavior, pandemic fears and market downturns, and restrictions on business and individual activities, has created significant volatility in the global economy. Consistent with the actions taken by governmental authorities, in late March 2020, we idled our manufacturing operations in regions around the world other than China, where manufacturing operations were suspended in January and February before beginning to resume operations in March. A successful phased restart of our manufacturing plants, supply network, and other dependent functions occurred in the second quarter of 2020. The remote work arrangements that we implemented in 2020 remain in place in most locations. Our remote work arrangements have been designed to allow for continued operation of non-production business-critical functions, including financial reporting systems and internal control. The full impact of COVID-19 on future results depends on future developments, such as the ultimate duration and scope of outbreaks (including any potential future waves due to variants or otherwise, and the success of vaccination programs) and their impact on our customers, dealers, and suppliers. Despite the successful restart of our manufacturing operations in 2020, we continue to experience intermittent COVID-19-related disruptions in our supply chain. Moreover, new restrictions could have an adverse effect on production, supply chains, distribution, and dem […cut]

**Label:** N

**Note (optional):** 

## A09 · EXXON MOBIL CORP · 10K_7 · 2019-12-31 → 2020-12-31

**OLD:**

> Statements in this discussion related to outlooks, projections, goals, targets, descriptions of strategic plans and objectives, and other statements of future events or conditions are forward-looking statements. Actual future results, including business and project plans, capacities, costs, and timing; capital spending; proceeds from asset sales; resource recoveries and production rates; asset carrying values; proved reserves; financing sources; the resolution of contingencies and uncertain tax positions; and the impact of new technologies, including to increase capital efficiency and production and to reduce greenhouse gas emissions, could differ materially due to a number of factors. These include global or regional changes in supply and demand for oil, gas, petrochemicals, feedstocks and other market conditions that impact prices and differentials; reservoir performance; the outcome of exploration projects and timely completion of development and construction projects; the impact of fiscal and commercial terms and the outcome of commercial negotiations or acquisitions; changes in law, taxes, or regulation including environmental regulations, and timely granting of governmental permits; war, trade agreements, shipping blockades or harassment, and other political, public health or security disturbances; opportunities for and regulatory approval of potential investments or divestments; the actions of competitors; the capture of efficiencies between business lines; unforeseen  […cut]

**NEW:**

> Outlooks, projections, goals, targets, descriptions of strategic plans and objectives, and other statements of future events or conditions in this release are forward-looking statements. Actual future results, including energy demand growth and mix; financial and operating performance; volume growth; project plans, timing, costs, and capacities; capital expenditures including environmental expenditures; cost reductions; emission intensity reductions; the impact of new technologies; capital expenditures and mix; investment returns; accounting and financial reporting effects resulting from market developments and ExxonMobil’s responsive actions, including potential impairment charges; the benefits of business integration; future debt levels and ability to reduce debt; the outcome of litigation and tax contingencies; and the impact of the COVID-19 pandemic on results, could differ materially due to a number of factors. These include global or regional changes in the supply and demand for oil, natural gas, petrochemicals, and feedstocks and other market conditions that impact prices and differentials; the impact of company actions to protect the health and safety of employees, vendors, customers, and communities; actions of competitors and commercial counterparties; the ability to access short- and long-term debt markets on a timely and affordable basis; the severity, length and ultimate impact of COVID-19 and government responses on people and economies; reservoir performance; t […cut]

**Label:** Y

**Note (optional):** 

## A10 · COCA COLA CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> •Global Ventures — favorable channel mix primarily due to the reopening of Costa retail stores, partially offset by unfavorable product mix; and

**NEW:**

> •Global Ventures — favorable pricing initiatives and favorable channel mix, primarily due to the timing of Costa retail store reopenings in the United Kingdom in the prior year, offset by the unfavorable impact of no longer receiving COVID-related incentives in the current year; and

**Label:** Y

**Note (optional):** 

## A11 · FORD MOTOR CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> Consistent with the actions taken by governmental authorities, in late March 2020, we idled our manufacturing operations in regions around the world other than China, where manufacturing operations were suspended in January and February before beginning to resume operations in March. A successful phased restart of our manufacturing plants, supply network, and other dependent functions occurred in the second quarter of 2020.

**NEW:**

> COVID-19. The impact of COVID-19, including changes in consumer behavior, pandemic fears and market downturns, and restrictions on business and individual activities, has created significant volatility in the global economy. Consistent with the actions taken by governmental authorities, in late March 2020, we idled our manufacturing operations in regions around the world other than China, where manufacturing operations were suspended in January and February before beginning to resume operations in March. A successful phased restart of our manufacturing plants, supply network, and other dependent functions occurred in the second quarter of 2020. The remote work arrangements that we implemented in 2020 remain in place in most locations. Our remote work arrangements have been designed to allow for continued operation of non-production business-critical functions, including financial reporting systems and internal control. The full impact of COVID-19 on future results depends on future developments, such as the ultimate duration and scope of outbreaks (including any potential future waves due to variants or otherwise, and the success of vaccination programs) and their impact on our customers, dealers, and suppliers. Despite the successful restart of our manufacturing operations in 2020, we continue to experience intermittent COVID-19-related disruptions in our supply chain. Moreover, new restrictions could have an adverse effect on production, supply chains, distribution, and dem […cut]

**Label:** Y

**Note (optional):** 

## A12 · Walmart Inc. · 10K_7 · 2023-01-31 → 2024-01-31

**OLD:**

> For fiscal 2023, operating expenses as a percentage of net sales increased 23 basis points when compared to the previous fiscal year. Operating expenses as a percentage of net sales were impacted by charges of $3.3 billion related to opioid-related legal settlements and charges of $0.8 billion related to the reorganization and restructuring of certain businesses in the Walmart International segment. These charges were partially offset by growth in net sales and lower incremental COVID-19 costs. For fiscal 2022, operating expenses as a percentage of net sales decreased 19 basis points when compared to the previous fiscal year. Operating expenses as a percentage of net sales benefited from growth in comparable sales and lower incremental COVID-19 related costs of $2.5 billion as compared to the previous year, partially offset by increased wage investments primarily in the Walmart U.S. segment.

**NEW:**

> For fiscal 2023, operating expenses as a percentage of net sales increased 23 basis points when compared to the previous fiscal year. Operating expenses as a percentage of net sales were negatively impacted by the charges related to opioid-related legal settlements and the reorganization and restructuring of certain businesses in the Walmart International segment discussed above. These charges were partially offset by growth in net sales and lower incremental COVID-19 costs.

**Label:** Y

**Note (optional):** 

## A13 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> (c)As of December 31, 2023, included a $729 million allowance for First Republic.

**NEW:**

> (c)As of December 31, 2024 and 2023, included an incremental $541 million and $655 million allowance for credit losses, respectively, on certain assets associated with First Republic to which the Standardized approach has been applied, as permitted by the transition provisions in the U.S. capital rules.

**Label:** Y

**Note (optional):** 

## A14 · JPMORGAN CHASE & CO · 10K_1A · 2024-12-31 → 2025-12-31

**OLD:**

> If an external party obtains access to customer account data on JPMorganChase’s systems, whether authorized or unauthorized, and that party misappropriates that data, this could result in negative outcomes for JPMorganChase and its clients and customers, including a heightened risk of fraudulent transactions using JPMorganChase’s systems, losses from fraudulent transactions and reputational harm arising from the perception that JPMorganChase’s systems may not be secure.

**NEW:**

> In addition, if a third-party, whether authorized or unauthorized, obtains and misappropriates data from JPMorganChase’s systems, JPMorganChase and its clients and customers could experience negative outcomes, including a heightened risk of fraudulent transactions using JPMorganChase’s systems, losses from fraudulent transactions and reputational harm from perceived system insecurity.

**Label:** Y

**Note (optional):** 

## A15 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> –a net addition of $1.3 billion in consumer, predominantly driven by CCB, reflecting $1.4 billion in Card Services driven by loan growth, including an increase in revolving balances, partially offset by a net reduction of $200 million in Home Lending, and

**NEW:**

> •$2.1 billion net addition in consumer, primarily in Card Services, predominantly driven by loan growth, reflecting higher revolving balances, including the seasoning of vintages originated in recent years, partially offset by a net reduction in Home Lending in the first quarter of 2024, and

**Label:** Y

**Note (optional):** 

## A16 · BERKSHIRE HATHAWAY INC · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> Estimated ultimate liabilities for asbestos, environmental and other latent injury claims were increased approximately $145 million in 2018, which produced a corresponding reduction in pre-tax earnings. Net liabilities for such claims, excluding amounts assumed under retroactive reinsurance contracts, were approximately $1.7 billion at December 31, 2018. We may use industry-wide loss experience data and informed judgment when internal loss data is of limited reliability in making estimates for such losses. Loss estimations for these exposures are difficult to determine due to the changing legal environment, and increases may be required in the future if new exposures or claimants are identified, new claims are reported or new theories of liability emerge. In addition to the previously described methodologies, we consider “survival ratios,” which is the average net claim payments in recent years in relation to net unpaid losses, as a rough guide to reserve adequacy. Our survival ratio was approximately 16 years as of December 31, 2018.

**NEW:**

> Estimated ultimate liabilities for asbestos, environmental and other latent injury claims were increased approximately $150 million in 2019, which produced a corresponding reduction in pre-tax earnings. Net liabilities for such claims, excluding amounts assumed under retroactive reinsurance contracts, were approximately $1.7 billion at December 31, 2019. Loss estimations for these exposures are difficult to determine due to the changing legal environment and increases may be required in the future if new exposures or claimants are identified, new claims are reported or new theories of liability emerge.

**Label:** Y

**Note (optional):** 

## A17 · GENERAL ELECTRIC CO · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> For 2018, restructuring and other charges were $3.6 billion of which approximately $1.4 billion was reported in cost of products/services and $2.1 billion was reported in selling, general and administrative expenses (SG&A). These activities were primarily at Power, Corporate and Oil & Gas. Cash expenditures for restructuring and other charges were approximately $2.0 billion for the twelve months ended December 31, 2018. Of the total $3.6 billion restructuring and other charges, $0.7 billion was recorded in the Oil & Gas segment, which amounted to $0.5 billion net of noncontrolling interest.

**NEW:**

> Cash expenditures for restructuring and other charges were approximately $1.2 billion, $1.5 billion and $1.5 billion for the years ended December 31, 2019, 2018 and 2017, respectively.

**Label:** Y

**Note (optional):** 

## A18 · GENERAL ELECTRIC CO · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> •
>
> The Healthcare Systems global market continued to expand, predominately in emerging markets, including China, driven by Ultrasound as well as Imaging across most modalities. In addition, Healthcare Systems launched 26 new products in 2017, and Life Sciences continued to expand its business through product launches, organic investments and acquisitions.

**NEW:**

> Revenues increased $0.7 billion (3%) organically* due to higher volume in Life Sciences, driven by BioPharma and Pharmaceutical Diagnostics, as well as higher volume in Healthcare Systems.

**Label:** Y

**Note (optional):** 

## A19 · GENERAL ELECTRIC CO · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> Cash used for investing activities of discontinued operations was $1.1 billion in 2024, a decrease of $2.6 billion compared to 2023, primarily driven by higher cash received of $4.6 billion from net settlements between our discontinued operations and businesses in continuing operations, due to cash received of $3.0 billion in 2024 related to the separation of our former GE Vernova business and cash paid of $1.1 billion in 2023 related to the separation of our former GE HealthCare business. In addition, there was a decrease in cash used due to the prior year separation of GE HealthCare cash and cash equivalents of $1.8 billion. These decreases in cash used were partially offset by a reduction of cash and cash equivalents of $4.2 billion due to the separation of GE Vernova in 2024.

**NEW:**

> Cash used for financing activities of discontinued operations decreased $0.1 billion for the year ended December 31, 2025 compared to 2024, primarily driven by net debt repayments in 2024 by our former GE Vernova business.

**Label:** Y

**Note (optional):** 

## A20 · BERKSHIRE HATHAWAY INC · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> Service group revenues declined $1.15 billion (8.5%) in 2020 compared to 2019 and pre-tax earnings decreased $81 million (4.8%). Pre-tax earnings of the group as a percentage of revenues were 13.0% in 2020, an increase of 0.5 percentage points compared to 2019.

**NEW:**

> Revenues of the industrial products group in 2021 increased $2.5 billion (9.8%) from 2020. Pre-tax earnings increased $714 million (19.0%) compared to 2020 and pre-tax earnings as a percentage of revenues in 2021 was 15.9%, an increase of 1.3 percentage points compared to 2020.

**Label:** ?

**Note (optional):** Old referenced service group in particular, NEW references industrial products.

## A21 · EXXON MOBIL CORP · 10K_7 · 2022-12-31 → 2023-12-31

**OLD:**

> 2021 versus 2020
>
> 2021 production of 3.7 million oil-equivalent barrels per day decreased 49 thousand barrels per day from 2020, as higher demand and growth were more than offset by lower entitlements due to higher prices, decline, and divestments.

**NEW:**

> 2022 versus 2021
>
> 2022 production of 3.7 million oil-equivalent barrels per day increased 25 thousand barrels per day from 2021. Excluding the impacts from entitlements, Russia expropriation, divestments, and eased government-mandated curtailments, net production grew by 103 thousand oil-equivalent barrels per day driven by Permian and Guyana.

**Label:**  Y

**Note (optional):** 

## A22 · COCA COLA CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> Also in 2019, the Company refranchised certain of its bottling operations in India. The impact of these refranchising activities has been included as a structural change in our analysis of net operating revenues on a consolidated basis as well as for the Bottling Investments and Asia Pacific operating segments.

**NEW:**

> In 2020, the Company discontinued our Odwalla juice business. The impact of discontinuing our Odwalla juice business has been included in acquisitions and divestitures in our analysis of net operating revenues on a consolidated basis as well as for the North America operating segment.

**Label:** Y

**Note (optional):** Overall similar type of disclosure

## A23 · GENERAL ELECTRIC CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> GE INDUSTRIAL LIQUIDITY. GE Industrial's primary sources of liquidity consist of cash and cash equivalents, free cash flows from our operating businesses, monetization of receivables, and short-term borrowing facilities, including revolving credit facilities. Cash generation can be subject to variability based on many factors, including seasonality, receipt of down payments on large equipment orders, timing of billings on long-term contracts, market conditions and our ability to execute dispositions. Additionally, as previously reported, we launched a program in the third quarter of 2020 to fully monetize our Baker Hughes position over approximately three years. Consistent with the program’s design, we received initial proceeds of approximately $0.4 billion in the fourth quarter of 2020 and $0.7 billion in January 2021. See Note 26 for further information.

**NEW:**

> CONSOLIDATED LIQUIDITY. Our primary sources of liquidity consist of cash and cash equivalents, free cash flows* from our operating businesses, cash generated from asset sales and dispositions, and short-term borrowing facilities, including revolving credit facilities. Cash generation can be subject to variability based on many factors, including seasonality, receipt of down payments on large equipment orders, timing of billings on long-term contracts, market conditions and our ability to execute dispositions. Total cash, cash equivalents and restricted cash was $15.8 billion at December 31, 2021, of which $6.4 billion was held in the U.S. and $9.4 billion was held outside the U.S.

**Label:** Y

**Note (optional):** 

## A24 · BERKSHIRE HATHAWAY INC · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> BH Primary’s loss ratios were 64.9% in 2018, 63.1% in 2017, and 61.8% in 2016. Losses and loss adjustment expenses included losses from significant catastrophe events of $190 million in 2018 from Hurricanes Florence and Michael and the wildfires in California and $225 million in 2017 from Hurricanes Harvey, Irma and Maria. Losses and loss adjustment expenses also included net gains from the reductions of estimated ultimate liabilities for prior years’ loss events of $715 million in 2018, $766 million in 2017 and $503 million in 2016. The liability reductions in each year primarily related to healthcare malpractice and workers’ compensation business. BH Primary writes significant levels of commercial and professional liability and workers’ compensation insurance and the related claim costs may be subject to higher severity and longer claim-tails, which could give rise to significant increases in claims liabilities in the future attributable to higher than expected claim settlements, adverse litigation outcomes or judicial rulings and other factors not currently anticipated.

**NEW:**

> BH Primary insurers write significant levels of commercial and professional liability and workers’ compensation insurance and the related claim costs may be subject to high severity and long claim-tails. Accordingly, we could experience significant increases in claims liabilities in the future attributable to higher than expected claim settlements, adverse litigation outcomes or judicial rulings and other factors not currently anticipated.

**Label:** N

**Note (optional):** 

## A25 · BERKSHIRE HATHAWAY INC · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> Consumer products revenues increased $359 million (3.0%) in 2020 versus 2019, while pre-tax earnings increased $146 million (11.7%). Pre-tax earnings as a percentage of revenues in 2020 increased 0.9 percentage points to 11.5%.

**NEW:**

> Revenues of the industrial products group in 2021 increased $2.5 billion (9.8%) from 2020. Pre-tax earnings increased $714 million (19.0%) compared to 2020 and pre-tax earnings as a percentage of revenues in 2021 was 15.9%, an increase of 1.3 percentage points compared to 2020.

**Label:** N

**Note (optional):** Similar but referencing different: "Consumer products" vs. "Industrial products"

## A26 · PFIZER INC · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> In 2023, we principally sold Paxlovid globally to government agencies. On October 13, 2023, we announced an amended agreement with the U.S. government, which facilitated the transition of Paxlovid to traditional commercial markets in the U.S. in November 2023, with minimal uptake of NDA-labeled commercial product before January 1, 2024 (see Note 17C). Internationally, for Paxlovid, most markets have now transitioned to commercial markets, and we are expecting most revenue for Paxlovid to be generated through commercial channels. In 2025, we expect utilization for Paxlovid to follow infection rates and stable market share, and revenues may fluctuate based on the timing, duration and severity of COVID-19 cases.

**NEW:**

> In 2023, we principally sold Paxlovid globally to government agencies. On October 13, 2023, we announced an amended agreement with the U.S. government, which facilitated the transition of Paxlovid to traditional commercial markets in the U.S. Internationally, most revenue was generated through commercial channels in 2025. We expect a higher proportion of revenues to be delivered in the second-half of the year and revenues to fluctuate based on the timing, duration and severity of COVID-19 cases. The expected impact of lower demand has been incorporated in our 2026 financial guidance.

**Label:** Y

**Note (optional):** Almost identical

## A27 · PFIZER INC · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> We periodically encounter supply delays, disruptions or shortages, including due to voluntary product recalls such as our recent Chantix recall. For information on our recent Chantix recall and risks related to product manufacturing, see the Item 1A. Risk Factors––Product Manufacturing, Sales and Marketing Risks section in this Form 10-K.

**NEW:**

> Regarding our supply chain generally, in 2022 and to date, we have not seen a significant disruption, and all of our manufacturing sites globally have continued to operate at or near normal levels; however, we are seeing an increase in overall demand in the industry for certain components and raw materials, which could potentially result in constraining available supply leading to a possible future impact on our business. We are continuing to monitor and implement mitigation strategies in an effort to reduce any potential risk or impact including active supplier management, qualification of additional suppliers and advanced purchasing to the extent possible. For information on risks related to product manufacturing, see the Item 1A. Risk Factors––Product Manufacturing, Sales and Marketing Risks section in this Form 10-K.

**Label:** N

**Note (optional):** Similar, but don't think its the same type disclosure.

## A28 · FORD MOTOR CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> Liquidity. One of our key priorities is to maintain a strong balance sheet, while at the same time having resources available to invest in and grow our business. At December 31, 2020, we had Company cash of $30.8 billion, an increase of $8.5 billion compared with December 31, 2019, primarily due to our unsecured debt issuance in the second quarter of 2020, with about 90% of Company cash held by consolidated entities domiciled in the United States. To be prepared for an economic downturn, we target an ongoing Company cash balance at or above $20 billion plus significant additional liquidity above our Company cash target. We expect to have periods when we will be above or below this amount due to: (i) future cash flow expectations, such as for investments in future opportunities, capital investments, debt maturities, pension contributions, or restructuring requirements, (ii) short-term timing differences, and (iii) changes in the global economic environment.

**NEW:**

> To be prepared for an economic downturn, we target an ongoing Company cash balance at or above $20 billion plus significant additional liquidity above our Company cash target. We expect to have periods when we will be above or below this amount due to: (i) future cash flow expectations, such as for investments in future opportunities, capital investments, debt maturities, pension contributions, or restructuring requirements, (ii) short-term timing differences, and (iii) changes in the global economic environment.

**Label:** Y

**Note (optional):** 

## A29 · GENERAL ELECTRIC CO · 10K_7 · 2019-12-31 → 2020-12-31

**OLD:**

> Backlog as of December 31, 2019 increased $49.7 billion (22%) primarily due to an increase in long-term service agreements.

**NEW:**

> Backlog as of December 31, 2020 increased $2.5 billion (9%) from December 31, 2019, primarily from Offshore Wind due to our first Haliade-X order from Dogger Bank Wind Farm, new Cypress platform orders mainly in Onshore Wind Europe and an increase in Hydro. These increases were partially offset by sales exceeding new orders at Grid, primarily as a result of increased commercial selectivity in certain product lines.

**Label:** Y

**Note (optional):** 

## A30 · JPMORGAN CHASE & CO · 10K_1A · 2024-12-31 → 2025-12-31

**OLD:**

> •disruptions in operational systems or in the ability of systems to communicate with each other could be caused by failures in synchronization or encryption software, or degraded performance of microprocessors, and

**NEW:**

> •failures in synchronization or encryption software, or degraded performance of microprocessors, which could cause disruptions in operational systems or in the ability of systems to communicate with each other, and

**Label:** Y

**Note (optional):** 

## A31 · GENERAL ELECTRIC CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> (a) Orders included $1,136 million, $3,643 million and $3,210 million related to BioPharma for the years ended December 31, 2020, 2019 and 2018, respectively.

**NEW:**

> (a) Includes interest and other financial charges of $63 million, $50 million and $101 million and benefit for income taxes of $162 million, $154 million and $166 million related to EFS within Corporate for the years ended December 31, 2021, 2020, and 2019, respectively.

**Label:** N

**Note (optional):** 

## A32 · COCA COLA CO · 10K_7 · 2022-12-31 → 2023-12-31

**OLD:**

> Unit case volume in North America increased 2 percent, which included 1 percent growth in Trademark Coca-Cola, 3 percent growth in both sparkling flavors and juice, value-added dairy and plant-based beverages, and even performance in water, sports, coffee and tea.

**NEW:**

> In Asia Pacific, unit case volume increased 3%, which included 4% growth in both sparkling flavors and Trademark Coca-Cola, 10% growth in juice, value-added dairy and plant-based beverages, and 1% growth in water, sports, coffee and tea. The operating segment reported growth in unit case volume of 11% in the India and Southwest Asia operating unit, 2% in the Greater China and Mongolia operating unit, and 1% in both the ASEAN and South Pacific and the Japan and South Korea operating units.

**Label:** Y

**Note (optional):** 

## A33 · JPMORGAN CHASE & CO · 10Q_P1_2 · 2025-03-31 → 2026-03-31

**OLD:**

> •The Firm’s nonperforming assets totaled $9.1 billion at March 31, 2025, up 10%, driven by higher wholesale nonaccrual loans, largely in Real Estate, concentrated in Multifamily and Lodging, reflecting downgrades, partially offset by lower consumer nonaccrual loans, which included loan sales. Refer to Wholesale Credit Portfolio and Consumer Credit Portfolio on pages 52-60 and pages 49-51, respectively, for additional information.

**NEW:**

> •The Firm’s nonperforming assets totaled $10.0 billion at March 31, 2026, up 10%, driven by:

**Label:** Y

**Note (optional):** NEW cuts off early - Also been some others from prior that simply are Labeled Y but cut off early either in OLD or NEW.

## A34 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> Net interest income increased driven by higher rates, the impact of First Republic, and higher revolving balances in Card Services, partially offset by lower Markets net interest income and lower average deposit balances.

**NEW:**

> Net interest income increased driven by the impact of balance sheet actions, primarily reinvestments in the investment securities portfolio, higher revolving balances in Card Services, the timing impact of First Republic, higher wholesale deposit balances and higher Markets net interest income. These factors were largely offset by deposit margin compression across the lines of business and lower average deposit balances in CCB.

**Label:** Y

**Note (optional):** 

## A35 · EXXON MOBIL CORP · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> The Corporation’s strategy seeks to maximize the advantages of our scale, business integration, leading technology, execution excellence, and our people to build globally competitive businesses that lead industry in earnings and cash flow growth across a range of future scenarios. We strive to play a leading role, regardless of how an energy transition unfolds. Across our portfolio of opportunities, we retain investment flexibility to maximize shareholder value. With advancements in technology and clear, consistent, stable, and effective government policies, we aim to achieve net-zero Scope 1 and 2 greenhouse gas emissions in our operated assets by 2050. Our net-zero ambition is backed by a comprehensive approach centered on detailed emission-reduction roadmaps for our major operated assets that were completed in 2022. The roadmaps build on the Company’s 2030 emission-intensity reduction plans and, notably, include reaching net-zero Scope 1 and 2 emissions in our heritage Permian Basin (1) unconventional operated assets by 2030, and by 2035 for Pioneer assets. We continue to update the roadmaps, including to account for portfolio changes, to reflect technology and policy, and to account for the many potential pathways, and the pace of an energy transition.

**NEW:**

> The Corporation’s strategy seeks to maximize the advantages of our scale, business integration, leading technology, execution excellence, and our people to build globally competitive businesses that lead industry in earnings and cash flow growth across a range of future scenarios. We strive to play a leading role, regardless of how an energy transition unfolds. Across our portfolio of opportunities, we retain investment flexibility to maximize shareholder value. In 2022, we announced our ambition to achieve net-zero Scope 1 and 2 greenhouse gas emissions in our operated assets by 2050, with advancements in technology and clear, consistent, stable, and effective government policies. Society's progress continues to lag in these areas. Without supportive policies and the innovations they drive, net zero 2050 will remain out of reach — for society and ExxonMobil. Our net-zero ambition is backed by a comprehensive approach centered on detailed emission-reduction roadmaps for our major operated assets that were completed in 2022. The roadmaps build on the Company’s 2030 emission-intensity reduction plans. We continue to update the roadmaps, including to account for portfolio changes, to reflect technology and policy, and to account for the many potential pathways and pace of an energy transition. Our plans include reaching net-zero Scope 1 and 2 emissions in our integrated Permian Basin operated assets by 2035, including Pioneer assets acquired in 2024. By 2030, we plan to reduce e […cut]

**Label:** Y

**Note (optional):** 

## A36 · EXXON MOBIL CORP · 10Q_P1_2 · 2025-03-31 → 2026-03-31

**OLD:**

> Expenses – Higher expenses mainly related to new product development costs, decreased earnings by $70 million.

**NEW:**

> Base Volume – Decreased earnings by $260 million, mainly driven by Middle East supply disruptions.

**Label:** N

**Note (optional):** 

## A37 · BERKSHIRE HATHAWAY INC · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> Real estate brokerage after-tax earnings increased in 2019 compared to 2018. The increase was primarily due to higher earnings at mortgage businesses due to increased refinance activity and earnings attributable to recent business acquisitions, partially offset by lower earnings at brokerage businesses, primarily from a decrease in closed units and lower margins.

**NEW:**

> Real estate brokerage after-tax earnings increased $12 million in 2021 compared to 2020. The increase was due to a comparative increase in closed brokerage transaction volumes in 2021, partially offset by lower funded mortgage volume due to a decrease in refinance activity.

**Label:** Y

**Note (optional):** 

## A38 · EXXON MOBIL CORP · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> Margins – Stronger margins increased earnings by $4,480 million driven by resilient demand and industry supply constraints.

**NEW:**

> Margins – Margins decreased earnings by $220 million driven by higher feed costs and energy prices.

**Label:** Y

**Note (optional):** 

## A39 · GENERAL ELECTRIC CO · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> BORROWINGS. Consolidated total borrowings were $19.3 billion and $20.5 billion at December 31, 2024 and December 31, 2023, respectively, a decrease of $1.2 billion, mainly due to maturities. In April 2024, the Company replaced its previous $10.0 billion syndicated credit facility with a five-year unsecured revolving credit facility in an aggregate committed amount of $3.0 billion. The total interest payments on consolidated borrowings are estimated to be $0.8 billion, $0.8 billion, $0.7 billion, $0.7 billion and $0.7 billion for 2025, 2026, 2027, 2028 and 2029, respectively.

**NEW:**

> BORROWINGS. Consolidated total borrowings were $20.5 billion and $19.3 billion at December 31, 2025 and December 31, 2024, respectively, an increase of $1.2 billion, primarily due to new debt issued of $2.0 billion, and currency exchange of $0.9 billion, partially offset by maturities of $1.8 billion. The Company also holds a five-year unsecured revolving credit facility maturing in 2029 in an aggregate committed amount of $3.0 billion and had zero outstanding at December 31, 2025.

**Label:** Y

**Note (optional):** 

## A40 · JPMORGAN CHASE & CO · 10K_7 · 2019-12-31 → 2020-12-31

**OLD:**

> • a $251 million addition in the wholesale allowance for credit losses driven by select client downgrades.

**NEW:**

> The prior year included a $244 million net reduction in the allowance for credit losses.

**Label:** Y

**Note (optional):** 

## A41 · JPMORGAN CHASE & CO · 10K_1A · 2020-12-31 → 2021-12-31

**OLD:**

> Any significant failure or disruption of JPMorgan Chase’s operations or operational systems, or any catastrophic event, could:

**NEW:**

> Any significant failure or disruption of JPMorgan Chase’s operations or operational systems, or the occurrence of one or more extraordinary events that are beyond its control, could:

**Label:** Y

**Note (optional):** 

## A42 · WEYCO GROUP INC · 10K_7 · 2019-12-31 → 2020-12-31

**OLD:**

> The majority of the Company’s interest income is generated by investments in marketable securities. Interest income was $823,000 and $981,000 in 2019 and 2018, respectively. The decrease in 2019 was primarily due to less interest earned on the lower cash and investment balances this year. Interest expense was $244,000 and $45,000 in 2019 and 2018, respectively. The increase in expense was largely due to the higher average debt balance this year, as a result of additional inventory purchases in the second half of the year ahead of the anticipated tariff on footwear. Other expense totaled $535,000 in 2019 versus $638,000 in 2018. The Company’s effective tax rate was 22.9% in 2019 and 22.5% in 2018.

**NEW:**

> The majority of the Company’s interest income is generated by investments in marketable securities. Interest income was $527,000 and $823,000 in 2020 and 2019, respectively. The decrease in 2020 was primarily due to less interest earned on the lower investment balances this year as a result of maturities of marketable securities and lower interest rates. Interest expense declined to $79,000 in 2020 from $244,000 in 2019, due to the lower average debt balance this year. Other income totaled $96,000 in 2020 versus other expense of $535,000 in 2019. The decrease in expense was primarily due to a decrease in the non-service cost components of pension expense, resulting from lower interest expense and higher expected return on plan assets.

**Label:** Y

**Note (optional):** 

## A43 · JPMORGAN CHASE & CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> In March 2020, the Firm began providing assistance to clients in response to the COVID-19 pandemic, predominantly in the form of payment deferrals and covenant modifications.

**NEW:**

> The Firm provided various forms of assistance to customers and clients impacted by the COVID-19 pandemic, including payment deferrals and covenant modifications. Assistance provided in response to the COVID-19 pandemic could delay the recognition of delinquencies, nonaccrual status, and net charge-offs for those customers and clients who would have otherwise moved into past due or nonaccrual status. Refer to Notes 12 and 13 for further information on the Firm’s accounting policies for loan modifications and the allowance for credit losses.

**Label:** Y

**Note (optional):** 

## A44 · JPMORGAN CHASE & CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> •lower revenue in CIB Fixed Income Markets, primarily in Rates, Currencies & Emerging Markets, Credit and Commodities, compared to a strong prior year, and an increase in Securitized Products, and

**NEW:**

> •higher net revenue in Fixed Income Markets, driven by a strong performance in the macro businesses amid volatile market conditions, particularly Currencies & Emerging Markets and Rates, partially offset by lower revenue in Securitized Products and Credit, and

**Label:** Y

**Note (optional):** 

## A45 · Apple Inc. · 10K_7 · 2019-09-28 → 2020-09-26

**OLD:**

> Products gross margin increased during 2018 compared to 2017 due primarily to a favorable shift in mix of iPhones and the strength in foreign currencies relative to the U.S. dollar, partially offset by higher product cost structures. Year-over-year Products gross margin percentage decreased during 2018 due primarily to higher product cost structures, partially offset by the strength in foreign currencies relative to the U.S. dollar.

**NEW:**

> Products gross margin increased during 2020 compared to 2019 due primarily to higher Products volume and material cost savings, partially offset by the weakness in foreign currencies relative to the U.S. dollar and a different Products mix. Products gross margin percentage decreased during 2020 compared to 2019 due primarily to the weakness in foreign currencies relative to the U.S. dollar and a different Products mix, partially offset by material cost savings and higher leverage.

**Label:** Y

**Note (optional):** 

## A46 · JPMORGAN CHASE & CO · 10Q_P1_2 · 2025-06-30 → 2026-06-30

**OLD:**

> •higher asset management fees in BWM, reflecting higher average market levels and to a lesser extent, net inflows, partially offset by

**NEW:**

> •in BWM, higher asset management fees, reflecting higher average market levels and net inflows, as well as higher deposit-related fees as a result of higher transaction volume and new accounts, partially offset by

**Label:** Y

**Note (optional):** 

## A47 · JPMORGAN CHASE & CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> (c)Movement in portfolio levels (inclusive of rule changes) refers to: changes in book size, composition, credit quality, and market movements for credit risk RWA; changes in position and market movements for market risk RWA; updates to cumulative losses for operational risk RWA; and deductions to credit risk RWA for excess eligible credit reserves not eligible for inclusion in Tier 2 capital.

**NEW:**

> (c)Movement in portfolio levels (inclusive of rule changes) refers to: for Credit risk RWA, changes in book size, composition and credit quality, market movements, and deductions for excess eligible credit reserves not eligible for inclusion in Tier 2 capital; for Market risk RWA, changes in position, market movements, and changes in the Firm’s regulatory multiplier from Regulatory VaR backtesting exceptions; and for Operational risk RWA, updates to cumulative losses and macroeconomic model inputs.

**Label:** Y

**Note (optional):** 

## A48 · JPMORGAN CHASE & CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> On December 18, 2020, the Federal Reserve announced that all large banks, including the Firm, could resume share repurchases commencing in the first quarter of 2021. Subsequently, the Firm announced that its Board of Directors authorized a new common share repurchase program for up to $30 billion. As directed by the Federal Reserve, total net repurchases and common stock dividends in the first and second quarters of 2021 were restricted and could not exceed the average of the Firm’s net income for the four preceding calendar quarters.

**NEW:**

> (a)As directed by the Federal Reserve, total net repurchases and common stock dividends in the first and second quarter of 2021 were restricted and could not exceed the average of the Firm’s net income for the four preceding calendar quarters. Effective July 1, 2021, the Firm became subject to the normal capital distribution restrictions provided under the regulatory capital framework.

**Label:** N

**Note (optional):** 

## A49 · Apple Inc. · 10K_1A · 2018-09-29 → 2019-09-28

**OLD:**

> Compliance with these laws, regulations and similar requirements may be onerous and expensive, and they may be inconsistent from jurisdiction to jurisdiction, further increasing the cost of compliance and doing business. Any such costs, which may rise in the future as a result of changes in these laws and regulations or in their interpretation, could individually or in the aggregate make the Company’s products and services less attractive to the Company’s customers, delay the introduction of new products in one or more regions, or cause the Company to change or limit its business practices. The Company has implemented policies and procedures designed to ensure compliance with applicable laws and regulations, but there can be no assurance that the Company’s employees, contractors, or agents will not violate such laws and regulations or the Company’s policies and procedures.

**NEW:**

> Compliance with these laws and regulations may be onerous and expensive, increasing the cost of conducting the Company’s global operations. Changes to laws and regulations can adversely affect the Company’s business by increasing the Company’s costs, limiting the Company’s ability to offer a product or service to customers, requiring changes to the Company’s business practices or otherwise making the Company’s products and services less attractive to customers. The Company has implemented policies and procedures designed to ensure compliance with applicable laws and regulations, but there can be no assurance that the Company’s employees, contractors or agents will not violate such laws and regulations or the Company’s policies and procedures. If the Company is found to have violated laws and regulations, it could materially adversely affect the Company’s reputation, financial condition and operating results.

**Label:** Y

**Note (optional):** 

## A50 · BERKSHIRE HATHAWAY INC · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> Revenues from consumer products were $7.1 billion in 2017, representing an increase of 8.8% compared to 2016, reflecting volume increases of 6.3% as well as higher average revenue per car/unit. The volume increases were primarily attributable to improving economic conditions, normalizing of retail inventories, new services and higher market share, which benefited domestic intermodal, international intermodal and automotive volumes.

**NEW:**

> Revenues from industrial products were $6.0 billion in 2018, an increase of 16.2% from 2017. The increase was attributable to volume increases of 9.8% as well as higher average revenue per car/unit. Volumes in 2018 increased for petroleum products, building products, construction products, and plastics.

**Label:** N

**Note (optional):** 

## A51 · BERKSHIRE HATHAWAY INC · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> (1)
>
> Primarily related to fuel, capacity, transmission and maintenance contracts and capital expenditure commitments of BHE and BNSF and aircraft purchase commitments of NetJets.

**NEW:**

> Other obligations pertaining to the acquisition of goods or services in the future, such as certain purchase obligations, are not currently reflected in the Consolidated Financial Statements and will be recognized in future periods as the goods are delivered or services are provided. As of December 31, 2021, the largest categories of our long-term contractual obligations primarily related to fuel, capacity, transmission and maintenance contracts and capital expenditure commitments of BHE and BNSF and aircraft purchase commitments of NetJets. We estimate future payments associated with these contracts over the next five years of approximately $19 billion, including $8 billion in 2022. We also have an agreement to acquire an additional 41.4% of Pilot in 2023 and agreements to acquire certain non-controlling interests of consolidated subsidiaries. Reference is made to Note 26 to the Consolidated Financial Statements for additional information regarding these commitments.

**Label:** N

**Note (optional):** 

## A52 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> Refer to page 95 for additional information on GSIB surcharge and page 98 for additional information on SLR.

**NEW:**

> Refer to AWM segment results on pages 84–87 for additional information on CIFM; Notes 1, 6, 14 and 25 for additional information on the adoption of updates to the Accounting for Investments in Tax Credit Structures guidance; Notes 2 and 6 for additional information on Visa shares; and Notes 6 and 34 for additional information on the First Republic acquisition.

**Label:** N

**Note (optional):** 

## A53 · COCA COLA CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> 1Represents the percent change in net operating revenues attributable to the increase (decrease) in concentrate sales volume for our geographic operating segments and our Global Ventures operating segment (expressed in equivalent unit cases) after considering the impact of acquisitions and divestitures. For our Bottling Investments operating segment, this represents the percent change in net operating revenues attributable to the increase (decrease) in unit case volume after considering the impact of structural changes. Our Bottling Investments operating segment data reflects unit case volume growth for consolidated bottlers only. Refer to the heading "Beverage Volume" above.

**NEW:**

> 1Bottling Investments operating segment data reflects unit case volume growth for consolidated bottlers only.

**Label:** ?

**Note (optional):** OLD has a couple disclosures in which NEW statement is relating to in a similar way

## A54 · GENERAL ELECTRIC CO · 10K_7 · 2020-12-31 → 2021-12-31

**OLD:**

> It is our policy to minimize exposure to interest rate changes with regards to our borrowings and their impact to interest and other financial charges. We fund our financial investments using a combination of debt and hedging instruments so that the interest rates of our borrowings match the expected interest rate profile on our assets. It is our policy to minimize currency exposures and to conduct operations either within functional currencies or using the protection of hedge strategies. To test the effectiveness of our hedging actions, for interest rate risk we assumed that, on January 1, 2021, interest rates increased by 100 basis points and the increase remained in place for the next 12 months and for currency risk of assets and liabilities denominated in other than their functional currencies, we evaluated the effect of a 10% shift in exchange rates against the U.S. dollar. The analyses indicated that our 2020 consolidated net earnings would decline by less than $0.1 billion for interest rate risk and approximately $0.1 billion for foreign exchange risk.

**NEW:**

> Exchange rate and interest rate risks are managed with a variety of techniques, including selective use of derivatives. We apply policies to manage each of these risks, including prohibitions on speculative activities. It is our policy to minimize currency exposures and to conduct operations either within functional currencies or using the protection of hedge strategies. To test the effectiveness of our hedging actions, for interest rate risk we assumed that, on January 1, 2022, interest rates decreased by 100 basis points and the decrease remained in place for the next 12 months and for currency risk of assets and liabilities denominated in other than their functional currencies, we evaluated the effect of a 10% shift in exchange rates against the U.S. dollar (USD). The analyses indicated that our 2021 consolidated net earnings would decline by $0.1 billion for interest rate risk and less than $0.1 billion for foreign exchange risk.

**Label:** Y

**Note (optional):** 

## A55 · GENERAL ELECTRIC CO · 10K_7 · 2022-12-31 → 2023-12-31

**OLD:**

> As of December 31, 2022, RPO increased $11.2 billion (5%) from December 31, 2021, primarily at Aerospace, from engines contracted under long-term service agreements that have now been put into service and an increase in Commercial and Military orders; at Renewable Energy, from new orders at Grid and Hydro exceeding sales; and at Power, driven by Gas Power services and equipment; partially offset by a decrease at HealthCare, from the impact of contract renewal timing in services.

**NEW:**

> As of December 31, 2023, RPO increased $28.8 billion (12%) from December 31, 2022, primarily at Aerospace, from increases in both equipment and services; at Renewable Energy, from new orders at Grid and Onshore Wind; and at Power, driven by increases in Gas Power services and equipment and Power Conversion equipment.

**Label:** Y

**Note (optional):** 

## A56 · JPMORGAN CHASE & CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> As of December 31, 2021, retained loans increased $45.4 billion driven by CIB and AWM, partially offset by decreases in CCB. Lending-related commitments increased $36.6 billion, predominantly driven by net portfolio activity in CB and CIB, including an increase in held for sale commitments intended to be syndicated.

**NEW:**

> As of December 31, 2022, retained loans increased by $43.3 billion driven by CIB and CB, including higher revolver utilization, partially offset by a decline in AWM. Lending-related commitments decreased $14.5 billion, driven by net portfolio activity in CIB, including a decrease in held-for-sale positions in the bridge financing portfolio, largely offset by net portfolio activity in AWM and CB.

**Label:** Y

**Note (optional):** 

## A57 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> Other assets decreased reflecting the impact of the change in the type of collateral placed with CCPs from cash to securities.

**NEW:**

> The following discussion excludes the impact of the transfer of certain First Republic deposits in the fourth quarter of 2023 from CCB to the other LOBs as the transfers had no net impact on Firmwide deposits.

**Label:** N

**Note (optional):** 

## A58 · COCA COLA CO · 10Q_P1_2 · 2025-03-28 → 2026-04-03

**OLD:**

> During the three months ended March 28, 2025, operating income was $3,659 million, compared to $2,141 million during the three months ended March 29, 2024, an increase of $1,518 million, or 71%. The increase was driven by an increase in concentrate sales volume of 1%, favorable pricing initiatives and lower other operating charges, partially offset by the impact of refranchising our bottling operations in the Philippines, Bangladesh and certain territories in India; higher commodity costs; and an unfavorable foreign currency exchange rate impact of 18%.

**NEW:**

> Unit case volume for Bottling Investments increased 1%, primarily driven by growth in Africa, partially offset by the impact of refranchising certain territories of our bottling operations in India.

**Label:** N

**Note (optional):** 

## A59 · JPMORGAN CHASE & CO · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> (b)As of December 31, 2024 and 2023, included a net benefit associated with cash flow hedges and debit valuation adjustments ("DVA") related to structured notes recorded in AOCI of $5.2 billion and $4.3 billion and the benefit from the CECL capital transition provisions of $720 million and $1.4 billion, respectively.

**NEW:**

> (b)As of December 31, 2025 and 2024, included a net reduction for certain deferred tax assets related to tax attribute carryforwards of $1.8 billion and $125 million, respectively, and a net benefit associated with cash flow hedges and debit valuation adjustments ("DVA") related to structured notes recorded in AOCI of $2.6 billion and $5.2 billion, respectively. As of January 1, 2025, the benefit from the CECL capital transition provision had been fully phased out. The year ended December 31, 2024 included benefit from the CECL capital transitions of $720 million.

**Label:** Y

**Note (optional):** Seems similar

## A60 · GENERAL ELECTRIC CO · 10K_7 · 2022-12-31 → 2023-12-31

**OLD:**

> The recovery trends vary by region from the travel restrictions imposed by governments and the prevalence of COVID-19 virus variants around the globe. We remain confident in the recovery, and current trends are in line with our recovery forecast. Consistent with updated industry projections, we estimate both narrowbody and widebody air traffic to recover to 2019 levels in late 2023. We are in frequent dialogue with our airline, airframe, and maintenance, repair and overhaul customers about the outlook for commercial air travel, new aircraft production, fleet retirements, and after-market services, including shop visit and spare parts demand.

**NEW:**

> Significant Trends & Developments. Our results in 2023 reflect robust demand for commercial air travel and continued strength in services, which represents over 70% of Aerospace’s revenue this year. A key underlying driver of our commercial engine and services business is global commercial departures, which grew high-teens during 2023 compared to 2022. The air traffic growth trends vary by region given economic conditions, airline competition and government regulations. Consistent with industry projections, we estimate departures growth to decelerate to mid-single digits in 2024. We are in frequent dialogue with our airline, airframe, and maintenance, repair and overhaul customers about the outlook for commercial air travel, new aircraft production, fleet retirements, and after-market services, including shop visit and spare parts demand.

**Label:** Y

**Note (optional):** 

## A61 · PFIZER INC · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> Accounting for contract assets and contract liabilities from contracts with customers requires contract assets and contract liabilities acquired in a business combination to be recognized and measured by the acquirer on the acquisition date in accordance with ASC 606. This new guidance will generally result in the acquirer recognizing contract assets and contract liabilities at the same amounts that were recorded by the acquiree. Previously, these amounts were recognized by the acquirer at fair value as of the acquisition date.
>
> January 1, 2023. Early adoption is permitted.
>
> We do not expect this new guidance to have a material impact on our consolidated financial statements.

**NEW:**

> In June 2022, the FASB issued final guidance to clarify that a contractual restriction on the sale of an equity security is not considered part of the unit of account of the equity security and, therefore, is not considered when measuring fair value. Recognizing a contractual sale restriction as a separate unit of account is not permitted.
>
> January 1, 2024, with early adoption permitted.
>
> We are assessing the impact, but currently do not expect this new guidance to have a material impact on our consolidated financial statements.

**Label:** N

**Note (optional):** 

## A62 · PFIZER INC · 10K_7 · 2024-12-31 → 2025-12-31

**OLD:**

> One way we believe we will be more efficient, effective and able to execute on these strategic priorities is through technology, including AI.

**NEW:**

> One way we believe we will be more efficient, effective and able to execute on these strategic priorities is through digital enablement. This includes expanding automation, data‑driven decision making, and enterprise AI solutions that strengthen productivity and accelerate innovation.

**Label:** Y

**Note (optional):** 

## A63 · JPMORGAN CHASE & CO · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> (c)
>
> Includes market-making inventory, AFS securities, and counterparty exposure on derivative and securities financings net of eligible collateral and hedging.

**NEW:**

> (c)
>
> Includes market-making inventory, AFS securities, and counterparty exposure on derivative and securities financings net of eligible collateral and hedging. Includes exposure from single reference entity (“single-name”), index and other multiple reference entity transactions for which one or more of the underlying reference entities is in a country listed in the above table.

**Label:** Y

**Note (optional):** 

## A64 · JPMORGAN CHASE & CO · 10K_7 · 2023-12-31 → 2024-12-31

**OLD:**

> •higher noninterest revenue, predominantly driven by the amortization of the purchase discount on certain acquired lending-related commitments associated with First Republic, partially offset by net investment valuation losses.

**NEW:**

> –a decline in the amortization of the fair value discount on certain acquired lending-related commitments associated with First Republic that have expired, and

**Label:** Y

**Note (optional):** 

## A65 · GENERAL ELECTRIC CO · 10K_1A · 2019-12-31 → 2020-12-31

**OLD:**

> With respect to acquisitions, joint ventures and business integrations, we may not achieve expected returns and other benefits as a result of changes in strategy or separation/integration challenges related to personnel, IT systems or other factors. In addition, in connection with acquisitions over time, we have recorded significant goodwill and other intangible assets on our balance sheet, and if we are not able to realize the value of these assets, we may be required to incur charges relating to the impairment of these assets. We also participate in a number of joint ventures with other companies or government enterprises in various markets around the world, including joint ventures where we have a lesser degree of control over the business operations, which may expose us to additional operational, financial, legal or compliance risks.

**NEW:**

> Business portfolio - Our success depends on achieving our strategic and financial objectives, including through dispositions, acquisitions, integrations and joint ventures. Over the past several years we have been pursuing a variety of dispositions, including the ongoing monetization of our remaining equity ownership position in Baker Hughes. The proceeds from those dispositions have been an important source of cash flow for the Company as part of our strategic and financial planning. When we seek to sell certain businesses, equity interests or assets, we may encounter difficulties in finding buyers or in market conditions that could delay or prevent the accomplishment of our objectives, and declines in the values of equity interests (such as our remaining interest in Baker Hughes) or other assets that we sell can diminish the cash proceeds that we realize. We may dispose of businesses or assets at a price or on terms that are less favorable than we had anticipated, or with purchase price adjustments or the exclusion of assets or liabilities that must be divested, managed or run off separately. We can also be subject to limitations in the form of regulatory or governmental approvals that may prevent certain prospective counterparties from completing transactions with us or delay us from executing transactions on our preferred timeline, or arising from our debt or other contractual obligations that limit our ability to complete certain transactions. Moreover, dispositions have […cut]

**Label:** Y

**Note (optional):** 

## A66 · JPMORGAN CHASE & CO · 10K_7 · 2021-12-31 → 2022-12-31

**OLD:**

> The increase in unsecured other borrowed funds at December 31, 2021 from December 31, 2020, and for the average year ended December 31, 2021 compared to the prior year period, was primarily due to net issuances of structured notes.

**NEW:**

> Auto and other: The auto and other loan portfolio, including loans at fair value consists of prime-quality scored auto and business banking loans, as well as overdrafts. The portfolio decreased when compared with December 31, 2021 due to paydowns of scored Auto loans and PPP loan forgiveness in Business Banking predominantly offset by originations of scored Auto loans. Net charge-offs for the year ended December 31, 2022 increased compared to the prior year due to higher scored Auto and overdraft charge-offs, as the prior year benefited from government stimulus and payment assistance programs. The scored Auto net charge-off rates were 0.24% and 0.04% for the years ended December 31, 2022 and 2021, respectively.

**Label:** N

**Note (optional):** 

## A67 · FORD MOTOR CO · 10Q_P1_2 · 2025-03-31 → 2026-03-31

**OLD:**

> Our Provision for/(Benefit from) income taxes for the first quarter of 2025 was $148 million, resulting in an effective tax rate of 23.8%.

**NEW:**

> Our Provision for/(Benefit from) income taxes for the first quarter of 2026 was a provision of $361 million, resulting in an effective tax rate of 12.4%, partially driven by a benefit resulting from a tax law change in the United Kingdom during the period.

**Label:** Y

**Note (optional):** 

## A68 · WEYCO GROUP INC · 10Q_P1_2 · 2025-06-30 → 2026-06-30

**OLD:**

> Cash dividends paid for the first six months of 2025 totaled $5.0 million and included two dividend payments that were both declared and paid in the first half of 2025. Cash dividends paid for the first six months of 2024 totaled $7.2 million and included three dividend payments: one that was declared in the fourth quarter of 2023 and paid in the first half of 2024 and two that were both declared and paid in the first half of 2024.

**NEW:**

> Cash dividends paid in the first half of 2026 totaled $26.6 million and included three dividend payments: our regular fourth-quarter and special dividend that was declared in 2025 and paid in 2026, and two dividend payments that were both declared and paid in the first half of 2026. Cash dividends paid in the first half of 2025 totaled $5.0 million and included two dividend payments that were both declared and paid in the first half of 2025.

**Label:** Y

**Note (optional):** 

## A69 · GENERAL ELECTRIC CO · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> •
>
> A decrease in net investment securities of $4.6 billion: $2.5 billion in 2018 compared with $7.1 billion in 2017.

**NEW:**

> GE Capital cash from investing activities was $11.8 billion in 2018 compared with $8.2 billion in 2017. The increase of $3.5 billion was primarily due to: higher collections of financing receivables of $7.1 billion and proceeds from the sales of EFS' debt origination business and EFS equity investments of $6.1 billion in 2018; partially offset by a decrease in net investment securities of $4.6 billion: $2.5 billion in 2018 compared with $7.1 billion in 2017; an increase in net additions to property, plant and equipment of $1.6 billion; net proceeds from sales of discontinued operations of an insignificant amount in 2018 compared with $1.5 billion in 2017; an increase in net intercompany loans from GE Capital to GE of $6.5 billion in 2018 compared with $5.9 billion in 2017 and a general reduction in funding related to discontinued operations.

**Label:** Y

**Note (optional):** Similar - OLD is very short though and may need additional context

## A70 · EXXON MOBIL CORP · 10K_7 · 2018-12-31 → 2019-12-31

**OLD:**

> The Corporation has a robust process to monitor for indicators of potential impairment across its asset groups throughout the year. This process is aligned with the requirements of ASC 360 and relies in part on the Corporation’s planning and budgeting cycle. In 2018, the Corporation identified a number of situations where events or changes in circumstances indicated that the carrying value of certain long-lived assets, mainly in North America, may not be recoverable. Accordingly, impairment assessments were performed which indicated that certain asset groups assessed have future undiscounted cash flow estimates that do not recover their carrying values. The Corporation’s 2018 results include after-tax charges of $0.5 billion to reduce the carrying value of those assets to fair value.

**NEW:**

> The Corporation has a robust process to monitor for indicators of potential impairment across its asset groups throughout the year. This process is aligned with the requirements of ASC 360 and relies in part on the Corporation’s planning and budgeting cycle. If events or changes in circumstances indicate that the carrying value of an asset may not be recoverable, the Corporation estimates the future undiscounted cash flows of the affected properties to judge the recoverability of carrying amounts. In performing this assessment, assets are grouped at the lowest level for which there are identifiable cash flows that are largely independent of the cash flows of other groups of assets. Cash flows used in recoverability assessments are based on the Corporation’s assumptions which are developed in the annual planning and budgeting process, and are consistent with the criteria management uses to evaluate investment opportunities. These evaluations make use of the Corporation’s assumptions of future capital allocations, crude oil and natural gas commodity prices including price differentials, refining and chemical margins, volumes, development and operating costs, and foreign currency exchange rates. Volumes are based on projected field and facility production profiles, throughput, or sales. Management’s estimate of upstream production volumes used for projected cash flows makes use of proved reserve quantities and may include risk-adjusted unproved reserve quantities. Cash flow esti […cut]

**Label:** Y

**Note (optional):** 
