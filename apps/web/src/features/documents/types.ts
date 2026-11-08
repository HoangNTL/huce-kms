export type DocumentStatus = "UPLOADED" | "PROCESSING" | "INDEXED" | "FAILED"

export interface DocumentMetadata {
  id: string
  title: string
  fileName: string
  fileSize: number
  fileType: string
  category: string
  status: DocumentStatus
  chunkCount: number
  createdAt: string
  updatedAt?: string
}

export interface DocumentChunk {
  id: string
  documentId: string
  chunkIndex: number
  content: string
  tokenCount: number
}
