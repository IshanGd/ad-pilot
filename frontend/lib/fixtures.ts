import type { AnalyzeResponse } from "./types";

/*
 * Static result for sample_data/sample_google_ads_report.csv, matching the
 * backend rule engine (backend/tests/test_rules.py). Used to build screens
 * before wiring the API, and by /audit?demo=1 for an offline demo.
 */
export const DEMO_ACCOUNT_ID = "demo";

export const DEMO_AUDIT: AnalyzeResponse = {
  account_id: DEMO_ACCOUNT_ID,
  analyzed_keywords: 12,
  total_waste_identified: 2200,
  recommendation_count: 8,
  by_severity: { HIGH: 2, MEDIUM: 3, LOW: 3 },
  by_type: {
    PAUSE_KEYWORD: 2,
    INCREASE_BUDGET: 2,
    ADD_NEGATIVE: 1,
    REVIEW_LOW_CTR: 3,
  },
  recommendations: [
    {
      id: "d1",
      campaign_id: "c-generic",
      campaign_name: "Generic Shoes",
      keyword_id: "k6",
      label: "cheap shoes online",
      type: "PAUSE_KEYWORD",
      severity: "HIGH",
      confidence: 0.9,
      estimated_impact: 1240,
      explanation:
        "This search term cost ₹1,240 over 83 clicks and brought in no sales. Pausing it stops that spend.",
      status: "PENDING",
    },
    {
      id: "d2",
      campaign_id: "c-generic",
      campaign_name: "Generic Shoes",
      keyword_id: "k7",
      label: "shoe repair",
      type: "PAUSE_KEYWORD",
      severity: "HIGH",
      confidence: 0.9,
      estimated_impact: 700,
      explanation:
        "This search term cost ₹700 over 45 clicks and brought in no sales. Pausing it stops that spend.",
      status: "PENDING",
    },
    {
      id: "d3",
      campaign_id: "c-brand",
      campaign_name: "Brand Search",
      keyword_id: "k1",
      label: "adpilot shoes",
      type: "INCREASE_BUDGET",
      severity: "MEDIUM",
      confidence: 0.8,
      estimated_impact: 5288,
      explanation:
        "This keyword brings sales at ₹38 each, well below your account average of ₹170. It is performing — giving it more budget should bring more sales at a similar cost.",
      status: "PENDING",
    },
    {
      id: "d4",
      campaign_id: "c-brand",
      campaign_name: "Brand Search",
      keyword_id: "k2",
      label: "adpilot store",
      type: "INCREASE_BUDGET",
      severity: "MEDIUM",
      confidence: 0.8,
      estimated_impact: 1536,
      explanation:
        "This keyword brings sales at ₹42 each, well below your account average of ₹170. It is performing — giving it more budget should bring more sales at a similar cost.",
      status: "PENDING",
    },
    {
      id: "d5",
      campaign_id: "c-generic",
      campaign_name: "Generic Shoes",
      keyword_id: "k12",
      label: "free shoes",
      type: "ADD_NEGATIVE",
      severity: "MEDIUM",
      confidence: 0.75,
      estimated_impact: 260,
      explanation:
        "“free shoes giveaway” got 35 clicks and no sales — these searches are not your buyers. Add it as a negative keyword so you stop paying for them.",
      status: "PENDING",
    },
    {
      id: "d6",
      campaign_id: "c-generic",
      campaign_name: "Generic Shoes",
      keyword_id: "k8",
      label: "kids shoes",
      type: "REVIEW_LOW_CTR",
      severity: "LOW",
      confidence: 0.6,
      estimated_impact: null,
      explanation:
        "Very few people who see this keyword click it (8 clicks from 1,500 views). Worth reviewing the ad wording or the keyword itself.",
      status: "PENDING",
    },
    {
      id: "d7",
      campaign_id: "c-generic",
      campaign_name: "Generic Shoes",
      keyword_id: "k9",
      label: "leather boots",
      type: "REVIEW_LOW_CTR",
      severity: "LOW",
      confidence: 0.6,
      estimated_impact: null,
      explanation:
        "Very few people who see this keyword click it (15 clicks from 2,200 views). Worth reviewing the ad wording or the keyword itself.",
      status: "PENDING",
    },
    {
      id: "d8",
      campaign_id: "c-clearance",
      campaign_name: "Clearance Sale",
      keyword_id: "k11",
      label: "sneaker sale",
      type: "REVIEW_LOW_CTR",
      severity: "LOW",
      confidence: 0.6,
      estimated_impact: null,
      explanation:
        "Very few people who see this keyword click it (40 clicks from 6,000 views). Worth reviewing the ad wording or the keyword itself.",
      status: "PENDING",
    },
  ],
};
