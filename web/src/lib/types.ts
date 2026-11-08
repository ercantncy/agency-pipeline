// Types mirror docs/WEB_SPEC.md. Ratios / MoM are fractions (0.1 = +10%).
export type Channel = 'google_ads' | 'meta_ads';
export type MonthlyChannel = Channel | 'total_paid';
export type Severity = 'critical' | 'warn';

export interface Manifest {
  generated_at: string;
  agency: { name: string; logo_text: string; primary_color: string };
  months: string[];
  default_month: string;
  clients: ManifestClient[];
}
export interface ManifestClient {
  client_id: string;
  client_name: string;
  currency: string;
  scenario: string;
  alert_counts_by_month: Record<string, { critical: number; warn: number }>;
}

export interface ClientInfo {
  client_id: string; client_name: string; currency: string; scenario: string;
  agency_name: string; agency_logo_text: string; agency_primary_color: string;
  google_ads_customer_id?: string | null; meta_account_id?: string | null;
  ga4_property_id?: string | null; gsc_site_url?: string | null;
}
export interface MonthlyRow {
  month: string; channel: MonthlyChannel;
  spend: number; clicks: number; conversions: number; conversion_value: number;
  cpa: number | null; roas: number | null; ctr: number | null;
  spend_mom_pct: number | null; conversions_mom_pct: number | null;
  cpa_mom_pct: number | null; roas_mom_pct: number | null;
}
export interface PaidDaily {
  date: string; channel: Channel; spend: number; impressions: number;
  clicks: number; conversions: number; conversion_value: number;
}
export interface CampaignMonthly {
  month: string; channel: Channel; campaign_id: string; campaign_name: string;
  spend: number; impressions: number; clicks: number; conversions: number; conversion_value: number;
}
export interface WebDaily {
  date: string; channel_group: string; sessions: number; engaged_sessions: number;
  users: number; key_events: number; revenue: number;
}
export interface SeoDaily { date: string; clicks: number; impressions: number; ctr: number; avg_position: number }
export interface SeoQuery { month: string; query: string; clicks: number; impressions: number; ctr: number; avg_position: number }
export interface ReconRow {
  date: string; channel: Channel; platform_clicks: number; ga4_sessions: number;
  session_click_ratio: number | null; platform_conversions: number; ga4_key_events: number; status: string;
}
export interface Alert {
  client_id: string; severity: Severity; check: string; message: string;
  start_date: string; end_date: string;
}
export interface ClientData {
  client: ClientInfo;
  monthly: MonthlyRow[];
  paid_daily: PaidDaily[];
  campaigns_monthly: CampaignMonthly[];
  web_daily: WebDaily[];
  seo_daily: SeoDaily[];
  seo_queries_monthly: SeoQuery[];
  reconciliation_daily: ReconRow[];
  thresholds: Record<Channel, { warn: number; critical: number }>;
  months: Record<string, { alerts: Alert[]; commentary: { text: string; source: string } }>;
}
