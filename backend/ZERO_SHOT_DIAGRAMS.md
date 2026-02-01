# Zero-Shot Enrichment System - Visual Reference

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        MODULE 1 PIPELINE                           │
│                                                                    │
│  Document Upload → Extraction → Enrichment → Output               │
│                                       ↓                            │
│                            ┌──────────────────┐                   │
│                            │  Zero-Shot       │                   │
│                            │  Enricher        │                   │
│                            │  (NEW!)          │                   │
│                            └──────────────────┘                   │
└────────────────────────────────────────────────────────────────────┘
```

## Zero-Shot Enricher Internal Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT MACHINE DATA                          │
│  {                                                                  │
│    "nom_machine": "Machine d'injection plastique",                 │
│    "description": "Injection plastique (100T → 5000T)",           │
│    "specifications": {}  ← MOSTLY EMPTY                            │
│  }                                                                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Parse
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MACHINE DATA STRUCTURE                          │
│  • name: "Machine d'injection plastique"                          │
│  • raw_description: "Injection plastique (100T → 5000T)"          │
│  • specifications: {}                                              │
│  • suppliers: []                                                   │
│  • pricing: {}                                                     │
│  • gaps: [ALL FIELDS MISSING]                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Initialize
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      QUERY BUDGET TRACKER                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Machine: "Machine d'injection plastique"                   │  │
│  │  Budget: 2 queries max                                      │  │
│  │  Used: 0 queries                                            │  │
│  │  Remaining: 2 queries                                       │  │
│  │  History: []                                                │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ENRICHMENT LOOP START                            │
│  While (budget.can_query() && needs_more_data):                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────┐                    ┌──────────────────┐
│  ITERATION 1     │                    │  ITERATION 2     │
│  (if needed)     │                    │  (if needed)     │
└──────────────────┘                    └──────────────────┘
        │                                         │
        │                                         │
        ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STEP 1: GENERATE QUERIES (LLM)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ LLM Input:                                                   │  │
│  │ • Current gaps: ["manufacturer", "specs", "price"]          │  │
│  │ • Remaining budget: 2 queries                               │  │
│  │ • Machine description: "Injection plastique (100T → 5000T)" │  │
│  │                                                              │  │
│  │ LLM Output:                                                  │  │
│  │ {                                                            │  │
│  │   "queries": [                                               │  │
│  │     "Haitian Arburg injection machine 100-5000T Algeria",   │  │
│  │     "plastic injection equipment MENA suppliers price"      │  │
│  │   ],                                                         │  │
│  │   "reasoning": "First query: manufacturer brands + specs,   │  │
│  │                 Second query: regional suppliers + pricing" │  │
│  │ }                                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STEP 2: EXECUTE WEB SEARCHES                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Query 1: "Haitian Arburg injection machine 100-5000T..."    │  │
│  │ ├─ Consume 1 query from budget (1/2 used, 1 remaining)     │  │
│  │ └─ Search via: Serper → Aggregator → Results               │  │
│  │                                                              │  │
│  │ Results Found:                                               │  │
│  │ • haitian-machinery.com - MA series 100-5000T              │  │
│  │ • arburg.com - ALLROUNDER specifications                   │  │
│  │ • alibaba.com - Injection machines $80K-$650K              │  │
│  │ • ... (10 total results)                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 3: EXTRACT DATA FROM RESULTS (LLM)                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ LLM reads search results and extracts:                      │  │
│  │                                                              │  │
│  │ Manufacturers: ["Haitian", "Arburg", "Engel"]              │  │
│  │ Models: ["MA series", "ALLROUNDER"]                        │  │
│  │ Specs:                                                       │  │
│  │   - Capacity: 100-5000 tons                                │  │
│  │   - Power: 15-350 kW                                        │  │
│  │ Pricing: $80,000 - $650,000 USD                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Update machine data
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     UPDATED MACHINE DATA                            │
│  specifications: {                                                  │
│    "manufacturer": "Haitian",                                      │
│    "capacity": "100-5000 tons",                                   │
│    "power": "15-350 kW"                                            │
│  }                                                                  │
│  pricing: { amount: 250000, currency: "USD" }                     │
│  suppliers: []  ← STILL EMPTY                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STEP 4: GAP ANALYSIS (LLM)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ LLM analyzes:                                                │  │
│  │ • What we have: manufacturer, capacity, power, price        │  │
│  │ • What's missing: dimensions, weight, Algeria suppliers    │  │
│  │                                                              │  │
│  │ Decision:                                                    │  │
│  │ {                                                            │  │
│  │   "gaps": ["dimensions", "weight", "Algeria suppliers"],    │  │
│  │   "critical_gaps": ["Algeria suppliers"],                   │  │
│  │   "confidence_level": "medium",                             │  │
│  │   "needs_more_queries": true,  ← STILL NEED DATA           │  │
│  │   "reasoning": "Core specs found but no local suppliers"   │  │
│  │ }                                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ needs_more_queries = true
                             │ budget.remaining() = 1
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│            LOOP BACK TO STEP 1 (Query 2/2)                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Generate refined query targeting EXACT gaps:                │  │
│  │ "Haitian 500T injection machine dimensions Algeria"         │  │
│  │                                                              │  │
│  │ Budget: 0/2 remaining after this query                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                    [REPEAT STEPS 2-4]
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STEP 5: BUDGET EXHAUSTED OR SUFFICIENT DATA                 │
│  Budget used: 2/2                                                   │
│  OR                                                                 │
│  Confidence: High (all critical fields filled)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│             STEP 6: FILL REMAINING GAPS WITH ESTIMATES              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ LLM generates educated estimates for missing data:          │  │
│  │                                                              │  │
│  │ Weight: 12,000 kg                                            │  │
│  │   Rationale: "Based on 500T standard (25 kg/ton)"          │  │
│  │   Source: estimation                                         │  │
│  │   Confidence: medium                                         │  │
│  │                                                              │  │
│  │ Lead time: 90-120 days                                       │  │
│  │   Rationale: "Typical import from Asia to Algeria"         │  │
│  │   Source: estimation                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STEP 7: CONVERT PRICING TO DZD                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Original: $250,000 USD                                       │  │
│  │                                                              │  │
│  │ Calculation:                                                 │  │
│  │ 1. Base conversion: $250,000 × 160 = 40,000,000 DZD        │  │
│  │ 2. Add 15% tariff: 40,000,000 × 1.15 = 46,000,000 DZD     │  │
│  │                                                              │  │
│  │ Result:                                                      │  │
│  │ {                                                            │  │
│  │   "amount": 250000,                                          │  │
│  │   "currency": "USD",                                         │  │
│  │   "amount_dzd": 46000000,                                   │  │
│  │   "includes_tariff": true,                                  │  │
│  │   "tariff_rate": "15%",                                     │  │
│  │   "conversion_rate": 160                                     │  │
│  │ }                                                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FINAL ENRICHED OUTPUT                            │
│  {                                                                  │
│    "nom_machine": "Machine d'injection plastique",                 │
│    "type": "Injection molding machine - Horizontal hydraulic",    │
│    "specifications": {                                             │
│      "manufacturer": "Haitian",                                    │
│      "manufacturer_alternatives": ["Arburg", "Engel"],           │
│      "capacity": "500 tons clamping force",                       │
│      "power": "55 kW",                                             │
│      "dimensions": "6.5m x 3.2m x 2.8m",                          │
│      "weight": "12,000 kg",                                        │
│      "weight_source": "estimation",                               │
│      "weight_rationale": "Based on 500T standard (25kg/ton)"      │
│    },                                                              │
│    "suppliers": [                                                  │
│      {"name": "SOMEPI", "location": "Algeria"},                   │
│      {"name": "General Plastic", "location": "Algeria"}           │
│    ],                                                              │
│    "pricing": {                                                    │
│      "amount": 250000,                                             │
│      "currency": "USD",                                            │
│      "amount_dzd": 46000000,                                      │
│      "includes_tariff": true,                                     │
│      "tariff_rate": "15%"                                         │
│    },                                                              │
│    "confidence": "high",                                           │
│    "gaps": [],                                                     │
│    "enrichment_metadata": {                                        │
│      "queries_used": 2,                                            │
│      "queries_history": [                                          │
│        "Haitian Arburg injection machine 100-5000T Algeria",      │
│        "Haitian 500T injection machine dimensions Algeria"        │
│      ],                                                            │
│      "processing_time_s": 15.3,                                    │
│      "method": "zero_shot_intelligent",                           │
│      "final_confidence": "high"                                    │
│    }                                                               │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Query Budget Visualization

```
┌────────────────────────────────────────────────────────────┐
│                    QUERY BUDGET TRACKER                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Machine: "Machine d'injection plastique"                 │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Budget: ██████████ (2 queries max)                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Initial State:                                           │
│  [●●] Used: 0/2  |  Remaining: 2  |  Can query: YES      │
│                                                            │
│  After Query 1:                                           │
│  [●○] Used: 1/2  |  Remaining: 1  |  Can query: YES      │
│  History: ["Haitian Arburg injection..."]                │
│                                                            │
│  After Query 2:                                           │
│  [●●] Used: 2/2  |  Remaining: 0  |  Can query: NO       │
│  History: [                                               │
│    "Haitian Arburg injection...",                         │
│    "Haitian 500T dimensions..."                           │
│  ]                                                         │
│                                                            │
│  🛑 Budget exhausted - Move to estimation phase           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## LLM Decision Tree

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Have budget?  │
                  └───┬────────┬───┘
                      │        │
                   YES│        │NO
                      │        │
                      ▼        └──────────────┐
              ┌───────────────┐               │
              │ Generate      │               │
              │ Queries       │               │
              │ (LLM)         │               │
              └───────┬───────┘               │
                      │                       │
                      ▼                       │
              ┌───────────────┐               │
              │ Execute       │               │
              │ Web Search    │               │
              └───────┬───────┘               │
                      │                       │
                      ▼                       │
              ┌───────────────┐               │
              │ Extract Data  │               │
              │ (LLM)         │               │
              └───────┬───────┘               │
                      │                       │
                      ▼                       │
              ┌───────────────┐               │
              │ Analyze Gaps  │               │
              │ (LLM)         │               │
              └───┬───────┬───┘               │
                  │       │                   │
          Need    │       │ Sufficient       │
          more    │       │ data             │
                  │       │                   │
                  │       └──────┐            │
                  │              │            │
                  └──────┐       │            │
                         │       │            │
            ┌────────────┘       │            │
            │                    │            │
            └────────────────────┴────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │ Fill Remaining │
                        │ with Estimates │
                        │ (LLM)          │
                        └────────┬───────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │ Convert to DZD │
                        └────────┬───────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │   COMPLETE     │
                        └────────────────┘
```

## Data Flow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Document   │───▶│  Extraction  │───▶│    Vague     │
│   (PDF)      │    │   (Stage 1)  │    │  Machines    │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
                                      ┌────────────────┐
                                      │  Zero-Shot     │
                                      │  Enricher      │
                                      └────────┬───────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌───────────────┐        ┌────────────────┐        ┌────────────────┐
            │   Web Search  │        │  LLM Analysis  │        │  Estimations   │
            │   Results     │        │  & Decisions   │        │  (when needed) │
            └───────┬───────┘        └────────┬───────┘        └────────┬───────┘
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               │
                                               ▼
                                      ┌────────────────┐
                                      │   Enriched     │
                                      │   Machines     │
                                      └────────┬───────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌───────────────┐        ┌────────────────┐        ┌────────────────┐
            │  Manufacturer │        │  Suppliers     │        │  Pricing (DZD) │
            │  Specs        │        │  (Algeria)     │        │  + Tariff      │
            └───────────────┘        └────────────────┘        └────────────────┘
```

## Confidence Scoring

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIDENCE LEVELS                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HIGH (85-100%)                                             │
│  ████████████████████████████████████░░░░░░░                │
│  • Multiple web sources confirm data                       │
│  • Manufacturer identified                                 │
│  • Specs from official sources                             │
│  • Minimal estimation (<20% of fields)                     │
│                                                             │
│  MEDIUM (60-84%)                                            │
│  ████████████████████░░░░░░░░░░░░░░░░░░                     │
│  • Single web source or                                    │
│  • Mix of web + estimates (20-50%)                         │
│  • Generic manufacturer known                              │
│                                                             │
│  LOW (<60%)                                                 │
│  ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░                     │
│  • Mostly estimates (>50%)                                 │
│  • No specific manufacturer                                │
│  • Limited web data                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Cost & Performance

```
┌──────────────────────────────────────────────────────────────┐
│               PER-MACHINE PROCESSING METRICS                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Time Breakdown:                                             │
│  ├─ Query Generation (LLM):     2-3s                        │
│  ├─ Web Search Execution:       3-5s per query              │
│  ├─ Data Extraction (LLM):      2-3s                        │
│  ├─ Gap Analysis (LLM):         2-3s                        │
│  ├─ Estimation (LLM):           2-3s                        │
│  └─ DZD Conversion:             <0.1s                       │
│                                                              │
│  Total Time:        10-20 seconds                           │
│  LLM Calls:         3-4 calls                               │
│  Web Searches:      1-2 queries                             │
│                                                              │
│  Cost (approximate):                                         │
│  • LLM calls:       ~$0.01-0.02                            │
│  • Web searches:    ~$0.005-0.01                           │
│  • Total:           ~$0.015-0.03 per machine               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

*Visual reference for understanding the Zero-Shot Intelligent Enrichment System*
