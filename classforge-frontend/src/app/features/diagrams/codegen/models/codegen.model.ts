export interface GeneratedFiles {
  [filePath: string]: string;
}

export type CodegenEngine = 'deterministic' | 'gemini';
export type BackendFramework = 'spring_boot' | 'fastapi';

export interface CodegenPreviewResponse {
  files: GeneratedFiles;
  total_files: number;
  target_backend?: BackendFramework;
  engine_used?: string;
  summary?: string;
}

export interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileTreeNode[];
  icon?: string;
  isExpanded?: boolean;
}

export type FrontendFramework = 'flutter' | 'react-native' | 'react' | 'angular' | 'vue' | 'vanilla';
export type FrontendTheme = 'dark' | 'light';

export interface FrontendPromptRequest {
  target_framework: FrontendFramework;
  theme: FrontendTheme;
  /** Graph data snapshot from canvas */
  graph_data?: any;
  engine?: CodegenEngine;
  gemini_api_key?: string;
  gemini_model?: string;
}

export interface FrontendPromptResponse {
  prompt: string;
  character_count: number;
  estimated_tokens: number;
  target_framework: string;
  theme: string;
  engine_used?: string;
}
