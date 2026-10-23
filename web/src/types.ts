export interface Meta {
  scenes: string[];
  perspectives?: string[];
  perspective_default?: string;
  platforms: string[];
  credentials: { ima_id: boolean; ima_key: boolean; llm_key: boolean };
  kb: { root: string; exists: boolean };
  history: { db: string; count: number };
  source_hint: string;
}

export interface Inputs {
  perspective?: string;
  product: string;
  audience: string;
  scene: string;
  platform: string;
  note: string;
}

export interface Editor {
  title: string;
  options: string;
  lead: string;
  cta: string;
  tags: string;
  paragraphs: string[];
  picks: string[];
  captions: string[];
  cover: string;
  cover_caption: string;
}

export interface PreviewImage {
  name: string;
  position: string;
  caption: string;
  source_label: string;
  url: string;
  missing: boolean;
}

export interface Article {
  title: string;
  title_options: string[];
  lead: string;
  paragraphs: string[];
  cta: string;
  tags: string[];
  facts: { point: string; source_title: string }[];
  images: PreviewImage[];
}

export interface Verification {
  facts: string[];
  images: string[];
  compliance: string[];
  pending: string[];
}

export interface Preview {
  article: Article;
  verification: Verification;
  export_text: string;
  fingerprint: string;
  intro: string;
}

export interface Candidate {
  name: string;
  theme: string;
  url: string;
  missing: boolean;
}

export interface VersionInfo {
  version_id: string;
  version_no: number;
  source_version_no: number | null;
  created_at: number;
  fingerprint: string;
}

export interface WorkMeta {
  use_tags: boolean;
  source: string;
  documents: { title: string }[];
  scenario_docs: { role: string; title: string }[];
  platform_title: string;
  paragraph_count: number;
  strategy: Record<string, string>;
}

export interface WorkData {
  ok: boolean;
  work_id: string;
  version_no: number;
  saved_version_no: number;
  fingerprint: string;
  saved_fingerprint: string;
  title: string;
  platform: string;
  inputs: Inputs;
  editor: Editor;
  preview: Preview;
  candidates: Candidate[];
  missing_images: string[];
  versions: VersionInfo[];
  meta: WorkMeta;
  saved_at: number;
  updated_at: number;
  message?: string;
  source?: string;
  warning?: string;
  created?: boolean;
}

export interface GenerateFailure {
  ok: false;
  stage: string;
  message: string;
  detail?: string;
  questions: string[];
  source?: string;
}

export interface WorkSummary {
  work_id: string;
  title: string;
  platform: string;
  created_at: number;
  updated_at: number;
  version_count: number;
  latest_no: number;
}
