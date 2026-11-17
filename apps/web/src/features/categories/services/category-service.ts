import { apiClient } from "@/lib/api-client"
import type { CategoryItem, CategoryCreateInput, CategoryUpdateInput } from "../types"

export const categoryService = {
  /**
   * Lấy danh sách tất cả danh mục tài liệu
   */
  async getCategories(): Promise<CategoryItem[]> {
    return apiClient.get<CategoryItem[]>("/categories/")
  },

  /**
   * Lấy thông tin chi tiết một danh mục theo ID
   */
  async getCategory(id: number | string): Promise<CategoryItem> {
    return apiClient.get<CategoryItem>(`/categories/${id}`)
  },

  /**
   * Tạo mới danh mục
   */
  async createCategory(data: CategoryCreateInput): Promise<CategoryItem> {
    return apiClient.post<CategoryItem>("/categories/", data)
  },

  /**
   * Cập nhật thông tin danh mục
   */
  async updateCategory(
    id: number | string,
    data: CategoryUpdateInput
  ): Promise<CategoryItem> {
    return apiClient.patch<CategoryItem>(`/categories/${id}`, data)
  },

  /**
   * Xóa danh mục
   */
  async deleteCategory(id: number | string): Promise<void> {
    return apiClient.delete<void>(`/categories/${id}`)
  },
}
