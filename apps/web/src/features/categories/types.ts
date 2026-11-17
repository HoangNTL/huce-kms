export interface CategoryItem {
  id: number | string
  name: string
  slug?: string
  code?: string
  description?: string | null
  created_at?: string
  updated_at?: string
}

export interface CategoryCreateInput {
  name: string
  description?: string
  slug?: string
}

export interface CategoryUpdateInput {
  name?: string
  description?: string
  slug?: string
}
