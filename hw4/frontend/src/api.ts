export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  short_description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock?: number
  sizes_in_stock?: string[]
}

export type SizeStock = { size: string; quantity: number }

export type ProductDetail = Product & {
  inventory: SizeStock[]
  total_stock: number
  sizes_in_stock: string[]
}

export type Category = { label: string; match: string; count: number }

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as T
}

export const api = {
  products: (params: { search?: string; garment_type?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.search) qs.set('search', params.search)
    if (params.garment_type) qs.set('garment_type', params.garment_type)
    const suffix = qs.toString() ? `?${qs}` : ''
    return get<{ count: number; products: Product[] }>(`/api/products${suffix}`)
  },
  product: (id: string) => get<ProductDetail>(`/api/products/${id}`),
  categories: () => get<{ categories: Category[] }>('/api/garment-types'),
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
