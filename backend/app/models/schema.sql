-- AdPilot Postgres schema (Supabase-compatible).
-- Matches the ORM models in app/models/tables.py. For local dev the app uses
-- SQLite and creates these from ORM metadata; for deploy, run this file once.
--
-- Deviation from 02_ARCHITECTURE.md: keywords.conversion_value is added here so
-- ROAS (Conversion_Value / Cost) can be computed per 03_RULES.md section 1.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_name TEXT,
  phone_number TEXT,
  monthly_budget NUMERIC,
  preferred_language TEXT DEFAULT 'en',
  notify_opt_in BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  name TEXT,
  budget NUMERIC,
  spend NUMERIC DEFAULT 0,
  impressions INT DEFAULT 0,
  clicks INT DEFAULT 0,
  conversions NUMERIC DEFAULT 0,
  conversion_value NUMERIC DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_campaigns_account ON campaigns(account_id);

CREATE TABLE IF NOT EXISTS keywords (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  keyword TEXT,
  search_term TEXT,
  match_type TEXT,
  impressions INT DEFAULT 0,
  clicks INT DEFAULT 0,
  spend NUMERIC DEFAULT 0,
  conversions NUMERIC DEFAULT 0,
  conversion_value NUMERIC DEFAULT 0,
  ctr NUMERIC,
  cpc NUMERIC,
  cpa NUMERIC
);
CREATE INDEX IF NOT EXISTS idx_keywords_campaign ON keywords(campaign_id);

CREATE TABLE IF NOT EXISTS recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
  type TEXT,
  severity TEXT,
  explanation TEXT,
  confidence NUMERIC,
  estimated_impact NUMERIC,
  status TEXT DEFAULT 'PENDING'
);

CREATE TABLE IF NOT EXISTS optimization_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  current_cpa NUMERIC,
  projected_cpa NUMERIC,
  current_conversions INT,
  projected_conversions INT,
  total_waste_identified NUMERIC
);

CREATE TABLE IF NOT EXISTS whatsapp_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  direction TEXT,
  body TEXT,
  related_recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
