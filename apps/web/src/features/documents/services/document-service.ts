import { apiClient } from "@/lib/api-client"
import type { DocumentMetadata, DocumentChunk } from "../types"
import type { PaginatedResponse, PaginationParams } from "@/types/api"

export const documentService = {
  async getDocuments(params?: PaginationParams): Promise<PaginatedResponse<DocumentMetadata>> {
    return apiClient.get<PaginatedResponse<DocumentMetadata>>("/api/v1/documents", { params })
  },

  async getDocument(id: string): Promise<DocumentMetadata> {
    return apiClient.get<DocumentMetadata>(`/api/v1/documents/${id}`)
  },

  async getDocumentChunks(id: string): Promise<DocumentChunk[]> {
    return apiClient.get<DocumentChunk[]>(`/api/v1/documents/${id}/chunks`)
  },

  async uploadDocument(file: File, category: string): Promise<DocumentMetadata> {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("category", category)

    return apiClient.post<DocumentMetadata>("/api/v1/documents/upload", formData)
  },

  async updateMetadata(
    id: string,
    data: Partial<Pick<DocumentMetadata, "title" | "category">>
  ): Promise<DocumentMetadata> {
    return apiClient.put<DocumentMetadata>(`/api/v1/documents/${id}`, data)
  },

  async deleteDocument(id: string): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/api/v1/documents/${id}`)
  },
}
