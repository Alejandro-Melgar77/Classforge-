export interface GeneratedFiles {
  [filePath: string]: string;
}

export interface CodegenPreviewResponse {
  files: GeneratedFiles;
  total_files: number;
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
}

export interface FrontendPromptResponse {
  prompt: string;
  character_count: number;
  estimated_tokens: number;
  target_framework: string;
  theme: string;
}

