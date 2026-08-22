export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'CONFLICT';

export type ProductStatus = 'verified' | 'needs_review' | 'conflicting' | 'processing' | 'failed';

export interface DynamicAttribute {
  id?: string;
  key: string;
  value: string | null;
  normalizedValue?: string | null;
  unit?: string;
  confidence?: number;
  confidenceLevel: ConfidenceLevel;
  status: string;
  fieldStatus: 'DIRECTLY_SUPPORTED' | 'INFERRED' | 'MISSING' | 'CONFLICTING' | string;
  sourceSnippet?: string;
  sourceLocation?: string;
  explanation?: string;
  competingValue?: string | null;
  attributeType?: string;
}

export interface ValidationIssue {
  id: string;
  product_id?: string;
  productId?: string;
  product_name?: string;
  productName?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: string;
  field: string;
  message: string;
  current_value?: string | null;
  currentValue?: string | null;
  suggested_value?: string | null;
  suggestedValue?: string | null;
  source_a?: string | null;
  sourceA?: string | null;
  source_b?: string | null;
  sourceB?: string | null;
  resolved: boolean;
  created_at?: string;
  createdAt?: string;
}

export interface SourceDoc {
  id: string;
  name: string;
  type: string;
  fileSize?: string;
  url?: string;
  pages?: number;
  extractedAt?: string;
  ocrAccuracy?: number;
}

export interface EvidenceItem {
  id: string;
  source_id?: string;
  document_name?: string;
  url?: string;
  page?: number;
  section?: string;
  content: string;
  score: number;
  source_type?: string;
  created_at?: string;
}

export interface ProductItem {
  id: string;
  sku: string;
  mpn?: string;
  name: string;
  brand: string;
  manufacturer?: string;
  category: string;
  subcategory?: string;
  industry?: string;
  description: string;
  completenessScore: number;
  confidenceScore: number;
  confidenceLevel: ConfidenceLevel;
  status: ProductStatus;
  review_status?: string;
  missingFieldsCount: number;
  conflictFieldsCount: number;
  fieldsTotal?: number;
  fieldsPopulated?: number;
  sourceDocument?: SourceDoc | null;
  imageUrl?: string;
  technicalSpecs?: DynamicAttribute[];
  dimensions?: any[];
  materials?: any[];
  certifications?: any[];
  features?: any[];
  applications?: any[];
  dynamicAttributes?: DynamicAttribute[];
  validationIssues?: ValidationIssue[];
  intelligence?: any;
  commerceData?: Record<string, string>;
  createdAt?: string;
  updatedAt?: string;
}

export interface ProcessingJobItem {
  id: string;
  product_id: string;
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  step: string;
  pipeline_stage?: string;
  progress: number;
  processing_time_ms?: number;
  error_message?: string | null;
  result?: any;
  created_at?: string;
  updated_at?: string;
}

export interface AnalyticsSummary {
  products: {
    total: number;
    verified: number;
    needs_review: number;
    conflicting: number;
    processing: number;
    failed: number;
    with_missing_data: number;
    with_conflicts: number;
  };
  confidence_distribution: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
    CONFLICT: number;
  };
  validation: {
    unresolved_issues: number;
    needs_attention: number;
  };
  jobs: {
    total: number;
    completed: number;
    failed: number;
    success_rate: number;
  };
}

export interface RecentActivityItem {
  type: string;
  title: string;
  description: string;
  product_id?: string;
  product_name?: string;
  timestamp: string;
  status: 'success' | 'error' | 'warning' | 'info';
}

export interface RecentlyProcessedItem {
  product_id: string;
  name: string;
  sku: string;
  status: string;
  confidence_level: ConfidenceLevel;
  missing_fields: number;
  conflict_fields: number;
  processed_at: string;
  processing_time_ms?: number;
}
