export interface SearchResult {
  name: string;
  synonym: string;
  objectType: string;
  objectTypeRu: string;
  score: number;
}

export interface MetadataDetails {
  object_name: string;
  object_type: string;
  object_type_ru: string;
  synonym: string;
  friendly_name: string;
  description: string;
  attributes: string[];
  tabular_sections: string[];
  register_records: string[];
  hierarchical: boolean;
  config_name: string;
}

export interface ObjectTypeStats {
  type: string;
  typeRu: string;
  count: number;
}

export interface EmbeddingResponse {
  embeddings: number[][];
  dimensions: number;
  model: string;
  count: number;
}

export interface SparseEmbeddingResponse {
  embeddings: { indices: number[]; values: number[] }[];
  model: string;
  count: number;
}
