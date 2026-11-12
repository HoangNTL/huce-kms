import { apiClient } from "@/lib/api-client"
import type { DocumentMetadata, DocumentDetail, CategoryItem } from "../types"
import type { PaginatedResponse, PaginationParams } from "@/types/api"

export const documentService = {
  async getDocuments(params?: PaginationParams): Promise<PaginatedResponse<DocumentMetadata>> {
    const page = Number(params?.page || 1)
    const pageSize = Number(params?.pageSize || 10)
    const skip = (page - 1) * pageSize
    const queryParams: Record<string, string | number | undefined> = {
      skip,
      limit: pageSize,
      q: params?.search ? String(params.search) : undefined,
      category_id: params?.category_id ? Number(params.category_id) : undefined,
      status: params?.status && params.status !== "ALL" ? String(params.status).toLowerCase() : undefined,
    }

    interface BackendPaginatedResponse {
      items: Array<Record<string, unknown>>
      pagination?: {
        total: number
        total_pages: number
      }
    }

    const res = await apiClient.get<BackendPaginatedResponse>("/documents", { params: queryParams })

    // Normalize PaginatedData from backend
    const items: DocumentMetadata[] = (res?.items || []).map((doc) => {
      const categoryObj = doc.category as { name?: string } | undefined
      return {
        id: doc.id as string | number,
        title: String(doc.title || ""),
        file_name: String(doc.file_name || ""),
        file_path: doc.file_path ? String(doc.file_path) : undefined,
        file_size: Number(doc.file_size || 0),
        file_type: String(doc.file_type || ""),
        file_hash: doc.file_hash ? String(doc.file_hash) : undefined,
        chunk_count: Number(doc.chunk_count ?? 0),
        total_pages: Number(doc.total_pages ?? 0),
        category: categoryObj?.name ? categoryObj.name : typeof doc.category === "string" ? doc.category : "Chung",
        category_id: doc.category_id ? Number(doc.category_id) : undefined,
        status: String(doc.status || "UPLOADED").toUpperCase() as DocumentMetadata["status"],
        error_message: doc.error_message ? String(doc.error_message) : null,
        created_at: String(doc.created_at || ""),
        updated_at: doc.updated_at ? String(doc.updated_at) : undefined,
      }
    })

    const total = res?.pagination?.total ?? items.length
    const totalPages = res?.pagination?.total_pages ?? Math.max(1, Math.ceil(total / pageSize))

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    }
  },

  async getDocument(id: string | number): Promise<DocumentDetail> {
    interface BackendDocumentDetail extends Record<string, unknown> {
      category?: { name?: string } | string
      chunks?: Array<Record<string, unknown>>
    }

    const doc = await apiClient.get<BackendDocumentDetail>(`/documents/${id}`)
    const categoryObj = doc.category as { name?: string } | undefined

    return {
      id: doc.id as string | number,
      title: String(doc.title || ""),
      file_name: String(doc.file_name || ""),
      file_path: doc.file_path ? String(doc.file_path) : undefined,
      file_size: Number(doc.file_size || 0),
      file_type: String(doc.file_type || ""),
      file_hash: doc.file_hash ? String(doc.file_hash) : undefined,
      chunk_count: Number(doc.chunk_count ?? 0),
      total_pages: Number(doc.total_pages ?? 0),
      category: categoryObj?.name ? categoryObj.name : typeof doc.category === "string" ? doc.category : "Chung",
      category_id: doc.category_id ? Number(doc.category_id) : undefined,
      status: String(doc.status || "UPLOADED").toUpperCase() as DocumentMetadata["status"],
      error_message: doc.error_message ? String(doc.error_message) : null,
      created_at: String(doc.created_at || ""),
      updated_at: doc.updated_at ? String(doc.updated_at) : undefined,
      chunks: (doc.chunks || []).map((c) => ({
        id: String(c.id || ""),
        document_id: (c.document_id ?? id) as string | number,
        chunk_index: Number(c.chunk_index ?? 0),
        token_count: Number(c.token_count ?? 0),
        page_number: Number(c.page_number ?? 1),
        content: String(c.content || ""),
        created_at: c.created_at ? String(c.created_at) : undefined,
      })),
    }
  },

  async uploadDocument(
    file: File,
    title?: string,
    categoryId?: number | string
  ): Promise<DocumentMetadata> {
    const formData = new FormData()
    formData.append("file", file)
    if (title) formData.append("title", title)
    if (categoryId) formData.append("category_id", String(categoryId))

    return apiClient.post<DocumentMetadata>("/documents/upload", formData)
  },

  async deleteDocument(id: string | number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/documents/${id}`)
  },

  async getCategories(): Promise<CategoryItem[]> {
    return apiClient.get<CategoryItem[]>("/categories")
  },
}
